"""Feedback functions for TruLens evaluation."""

import logging
from typing import Any, List

from trulens_eval import Feedback, Select
from trulens.feedback.templates.rag import Groundedness
from trulens_eval.feedback.provider.openai import OpenAI as OpenAIProvider
from trulens_eval.feedback.provider.google import Google as GoogleProvider

from app.settings import settings

logger = logging.getLogger(__name__)

def get_feedback_functions() -> List[Feedback]:
    """
    Initialize and return TruLens feedback functions.
    
    Supported:
    - Answer Relevance
    - Context Relevance
    - Groundedness (RAG validation)
    """
    try:
        # 1. Initialize Provider
        provider_name = settings.llm_provider.lower()
        if provider_name == "openai":
            if not settings.openai_api_key:
                logger.warning("OpenAI API key missing for TruLens feedback, skipping feedback functions.")
                return []
            provider = OpenAIProvider(model_engine=settings.openai_model)
        elif provider_name == "google":
            if not settings.google_api_key:
                logger.warning("Google API key missing for TruLens feedback, skipping feedback functions.")
                return []
            provider = GoogleProvider(model_id=settings.google_model)
        else:
            # Default to OpenAI if possible, or skip
            logger.warning(f"Provider {provider_name} not directly supported for TruLens feedback in this script yet. Using OpenAI fallback if key exists.")
            if settings.openai_api_key:
                provider = OpenAIProvider(model_engine=settings.openai_model)
            else:
                return []

        # 2. Answer Relevance
        # Measures how relevant the final answer is to the user's query.
        f_answer_relevance = Feedback(
            provider.relevance, 
            name="Answer Relevance"
        ).on_input_output()

        # 3. Context Relevance
        # Measures how relevant the retrieved context is to the user's query.
        # Note: We need to point to the correct state path for retrieved candidates
        f_context_relevance = Feedback(
            provider.context_relevance, 
            name="Context Relevance"
        ).on_input().on(
            Select.Record.app.retrieved_candidates
        ).aggregate(max)

        # 4. Groundedness
        # Measures how much of the answer is derived from the retrieved context.
        grounded = Groundedness(groundedness_provider=provider)
        f_groundedness = (
            Feedback(grounded.groundedness_measure_with_cot_reasons, name="Groundedness")
            .on(Select.Record.app.retrieved_candidates)
            .on_output()
        )

        return [f_answer_relevance, f_context_relevance, f_groundedness]

    except Exception as e:
        logger.error(f"Failed to initialize TruLens feedback functions: {str(e)}", exc_info=True)
        return []

def get_safety_feedback_functions() -> List[Feedback]:
    """Optional safety and toxicity feedback functions."""
    try:
        provider_name = settings.llm_provider.lower()
        if provider_name == "openai" and settings.openai_api_key:
            provider = OpenAIProvider(model_engine=settings.openai_model)
            
            f_toxic = Feedback(provider.toxic, name="Toxicity").on_output()
            f_pii = Feedback(provider.pii_detection, name="PII Detection").on_input()
            
            return [f_toxic, f_pii]
    except Exception:
        pass
    return []
