"""Feedback functions for TruLens evaluation."""

import contextlib
import io
import json
import logging
import sys
import types
import os
import warnings
from typing import Any, List, Optional

os.environ.setdefault("TRULENS_OTEL_TRACING", "1")

# Silence noisy trulens warnings and deprecations
warnings.filterwarnings("ignore", category=DeprecationWarning, module="trulens")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="trulens_eval")
logging.getLogger("trulens.core.utils.imports").setLevel(logging.ERROR)
logging.getLogger("trulens_eval.utils.imports").setLevel(logging.ERROR)


def _install_langchain_schema_shim() -> None:
    """
    ``trulens-providers-openai==2.2.2`` hard-imports
    ``from langchain.schema import Generation, LLMResult`` in
    ``trulens/providers/openai/endpoint.py``. langchain 1.x removed the
    ``langchain.schema`` module (those symbols now live in
    ``langchain_core.outputs``), so the import raises
    ``ModuleNotFoundError: No module named 'langchain.schema'`` and the feedback
    provider fails to initialise (``feedbacks=[]`` -> no RAG-triad scores).

    Newer trulens providers (>=2.8.x) added a try/except fallback to
    ``langchain_core.outputs`` but also pin ``openai<2.0.0``, which conflicts
    with our ``openai>=2.26`` / ``langchain-openai`` stack — so we cannot
    upgrade. Instead we backport that exact fallback by registering a
    lightweight ``langchain.schema`` module that delegates attribute lookups to
    ``langchain_core.outputs``. Must run before any trulens provider import.
    No-op if ``langchain.schema`` already resolves (older langchain).
    """
    import importlib

    if "langchain.schema" in sys.modules:
        return
    try:
        importlib.import_module("langchain.schema")
        return  # native module exists; nothing to shim
    except Exception:
        pass

    try:
        import langchain_core.outputs as _lc_outputs
    except Exception:
        return  # can't shim; let the original import error surface

    shim = types.ModuleType("langchain.schema")

    def __getattr__(name: str):  # PEP 562 module-level __getattr__
        try:
            return getattr(_lc_outputs, name)
        except AttributeError as exc:
            raise AttributeError(name) from exc

    shim.__getattr__ = __getattr__  # type: ignore[attr-defined]
    sys.modules["langchain.schema"] = shim


_install_langchain_schema_shim()


@contextlib.contextmanager
def _suppress_trulens_import_noise():
    """
    TruLens' optional-import machinery emits raw ``print()`` calls (not log
    records) when optional integrations such as ``llama_index`` are absent —
    e.g. "TRULENS DEBUG: Dummy original exception: No module named 'llama_index'".
    These cannot be silenced via logging config, so we swallow stdout/stderr
    only while the trulens import runs. Real errors still raise normally.
    """
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        yield


with _suppress_trulens_import_noise():
    from trulens.core import Feedback

from app.settings import settings

logger = logging.getLogger(__name__)

# TruLens feedback (LLM-judge) model for the Groq provider. The app's serving
# model (settings.groq_model, e.g. llama-3.1-8b-instant) does NOT support the
# `response_format=json_schema` structured outputs that the feedback judge
# requires, so judge calls fail with HTTP 400. Use a Groq model that supports
# structured outputs for evaluation only — the serving model is unchanged.
# See https://console.groq.com/docs/structured-outputs#supported-models
TRULENS_GROQ_JUDGE_MODEL = "openai/gpt-oss-20b"


def _make_provider():
    """Initialize and return the LLM provider for feedback evaluation."""
    provider_name = (settings.feedback_llm_provider or settings.llm_provider).lower()
    if provider_name == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key missing for TruLens feedback.")
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
        from trulens.providers.openai import OpenAI as OpenAIProvider
        return OpenAIProvider(model_engine=settings.feedback_openai_model)
    elif provider_name in ("local", "ollama"):
        from trulens.providers.openai import OpenAI as OpenAIProvider
        return OpenAIProvider(
            model_engine=settings.feedback_local_model,
            api_key=settings.feedback_local_api_key or "ollama",
            base_url=settings.feedback_local_base_url,
            timeout=600.0,
            max_retries=0,
        )
    elif provider_name == "google":
        if not settings.google_api_key:
            raise RuntimeError("Google API key missing for TruLens feedback.")
        from trulens.providers.google import Google as GoogleProvider
        return GoogleProvider(model_id=settings.google_model)
    elif provider_name == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("Groq API key missing for TruLens feedback.")
        from trulens.providers.openai import OpenAI as OpenAIProvider
        # Groq exposes an OpenAI-compatible endpoint. Use a structured-output
        # capable judge model (not settings.groq_model) so feedback eval works.
        return OpenAIProvider(
            model_engine=TRULENS_GROQ_JUDGE_MODEL,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    else:
        logger.warning(
            f"Provider '{provider_name}' not directly supported. "
            "Attempting OpenAI fallback."
        )
        if settings.openai_api_key:
            from trulens.providers.openai import OpenAI as OpenAIProvider
            return OpenAIProvider(model_engine=settings.openai_model)
        raise RuntimeError("No usable LLM provider for TruLens feedback.")


def get_feedback_functions() -> List[Feedback]:
    """
    Return TruLens feedback functions for RAG evaluation.

    Metrics
    -------
    - **Answer Relevance** — Is the final matched-candidate list relevant to
      the job description?
    - **Context Relevance** — Are the RAG-retrieved candidates relevant to
      the job description?
    - **Groundedness** — Is the answer grounded in the retrieved candidates?
    """
    try:
        # Provider imports (trulens.providers.*) lazily probe optional
        # integrations like llama_index and emit raw debug prints; suppress them.
        with _suppress_trulens_import_noise():
            provider = _make_provider()
    except Exception as e:
        logger.warning(f"Could not create feedback provider: {e}")
        return []

    try:
        from trulens.core.feedback.selector import Selector
        import re

        # ------------------------------------------------------------------
        # Selector processors
        # ------------------------------------------------------------------

        def _extract_jd_text(attributes: dict) -> Optional[str]:
            """Extract the raw JD text from the record_root span."""
            # 1. Prefer the dedicated record_root.input attribute
            text = attributes.get("ai.observability.record_root.input")
            if text and len(text.strip()) > 10:
                return text.strip()

            # 2. Fallback: requisition_text kwarg on execute()
            text = attributes.get("ai.observability.call.kwargs.requisition_text")
            if text and len(text.strip()) > 10:
                return text.strip()

            # 3. Fallback: parse jd_text from state
            for attr_name in [
                "ai.observability.call.kwargs.state",
                "ai.observability.call.return",
            ]:
                state_str = attributes.get(attr_name, "")
                if not state_str:
                    continue
                match = re.search(
                    r'"jd_text"\s*:\s*"(.*?)"',
                    state_str,
                    re.DOTALL,
                )
                if match:
                    return match.group(1).replace("\\n", "\n")

            return None

        def _extract_candidates_output(attributes: dict) -> Optional[str]:
            """
            Build a semantically rich matched-candidates summary from the
            record_root output.

            The judge LLMs (Answer Relevance, Groundedness) need real prose —
            the fit level and explanation text — not opaque IDs and scores, or
            relevance always scores ~0. We parse the final_results JSON and
            surface each candidate's fit level plus its explanation summary.
            """
            output_str = attributes.get("ai.observability.record_root.output", "")
            if not output_str:
                # Also try call.return for the execute() span
                output_str = attributes.get("ai.observability.call.return", "")
            if not output_str:
                return None

            # Preferred path: parse the JSON array of results.
            try:
                results = json.loads(output_str)
                if isinstance(results, list) and results:
                    lines = []
                    for c in results:
                        if not isinstance(c, dict):
                            continue
                        cid = c.get("team_member_id", "?")
                        fit = c.get("fit_level", "")
                        score = c.get("profile_score", "")
                        explanation = c.get("explanation", "")
                        if isinstance(explanation, list):
                            explanation = " ".join(str(e) for e in explanation)
                        lines.append(
                            f"Candidate {cid} (fit: {fit}, score: {score}): "
                            f"{str(explanation).strip()}"
                        )
                    if lines:
                        return "Matched Candidates:\n" + "\n\n".join(lines)
            except Exception:
                pass

            # Fallback: first 2000 chars of whatever is there.
            return str(output_str)[:2000]

        def _extract_rag_context(attributes: dict) -> Optional[List[str]]:
            """Extract retrieved candidate IDs from the rag_retrieval_node span."""
            func_name = attributes.get("ai.observability.call.function", "")
            if "rag_retrieval" not in func_name:
                return None

            ret_val = attributes.get("ai.observability.call.return", "")
            if not ret_val:
                return None

            try:
                cands = re.findall(
                    r'"team_member_id"\s*:\s*"([^"]+)"',
                    ret_val,
                )
                if cands:
                    return [f"Retrieved candidate ID: {cid}" for cid in cands]
            except Exception:
                pass
            return None

        # ------------------------------------------------------------------
        # Selectors — all anchored to the record_root span so that they share
        # the same (record_id, span_group) key in _collect_inputs_from_events.
        # The RAG context is embedded inside the record_root output JSON.
        # ------------------------------------------------------------------

        def _extract_rag_context_from_root(attributes: dict) -> Optional[List[str]]:
            """
            Build the RAG context list from the record_root output, which
            already contains the final_results list.

            This avoids selecting a different span (rag_retrieval_node) which
            would put the context selector in a different span_group to the
            question/answer selectors and cause the validation step to drop
            all inputs.

            Each context chunk carries semantic content (fit level + the
            candidate's explanation) rather than a bare ID, so Context
            Relevance and Groundedness can score meaningfully.
            """
            # The record_root.output has the full final_results JSON
            output_str = (
                attributes.get("ai.observability.record_root.output", "")
                or attributes.get("ai.observability.call.return", "")
            )
            if not output_str:
                return None

            try:
                results = json.loads(output_str)
                if isinstance(results, list) and results:
                    chunks = []
                    for c in results:
                        if not isinstance(c, dict):
                            continue
                        cid = c.get("team_member_id", "?")
                        fit = c.get("fit_level", "")
                        explanation = c.get("explanation", "")
                        if isinstance(explanation, list):
                            explanation = " ".join(str(e) for e in explanation)
                        chunks.append(
                            f"Candidate {cid} (fit: {fit}): "
                            f"{str(explanation).strip()}"
                        )
                    if chunks:
                        return chunks
            except Exception:
                pass

            # Fallback: regex out just the IDs if JSON parsing failed.
            try:
                cands = re.findall(r'"team_member_id"\s*:\s*"([^"]+)"', output_str)
                if cands:
                    return [f"Matched candidate ID: {cid}" for cid in cands]
            except Exception:
                pass
            return None

        # All three selectors point at the record_root span, so they are all
        # in the same span_group and the validation pass keeps them.
        selector_question = Selector(
            span_type="record_root",
            span_attributes_processor=_extract_jd_text,
            ignore_none_values=True,
        )
        selector_answer = Selector(
            span_type="record_root",
            span_attributes_processor=_extract_candidates_output,
            ignore_none_values=True,
        )
        selector_context = Selector(
            span_type="record_root",
            span_attributes_processor=_extract_rag_context_from_root,
            ignore_none_values=True,
            collect_list=True,
        )

        # ------------------------------------------------------------------
        # Feedback functions
        # ------------------------------------------------------------------

        # Use the CoT variant: the plain `relevance` schema fails Groq's strict
        # structured-output validation on gpt-oss-20b, while the CoT variant
        # passes (and adds a reason). See _make_provider for judge model.
        f_answer_relevance = Feedback(
            provider.relevance_with_cot_reasons,
            name="Answer Relevance",
        ).on({"prompt": selector_question, "response": selector_answer})

        f_context_relevance = Feedback(
            provider.context_relevance,
            name="Context Relevance",
        ).on({"question": selector_question, "context": selector_context})

        f_groundedness = Feedback(
            provider.groundedness_measure_with_cot_reasons,
            name="Groundedness",
        ).on({"source": selector_context, "statement": selector_answer})

        return [f_answer_relevance, f_context_relevance, f_groundedness]

    except Exception as e:
        logger.error(
            f"Failed to initialize TruLens feedback functions: {e}",
            exc_info=True,
        )
        return []


def get_safety_feedback_functions() -> List[Feedback]:
    """Optional safety and toxicity feedback functions (OpenAI only)."""
    try:
        provider_name = settings.llm_provider.lower()
        if provider_name == "openai" and settings.openai_api_key:
            from trulens.providers.openai import OpenAI as OpenAIProvider
            provider = OpenAIProvider(model_engine=settings.openai_model)

            f_toxic = Feedback(provider.toxic, name="Toxicity").on_output()
            f_pii = Feedback(provider.pii_detection, name="PII Detection").on_input()

            return [f_toxic, f_pii]
    except Exception:
        pass
    return []
