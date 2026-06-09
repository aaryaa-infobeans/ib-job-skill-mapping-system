"""TruLens service for observability and instrumentation."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

# Import the feedback module first so its trulens-import-noise suppressor and
# logging config are installed before we import any trulens symbols here.
from app.evaluation.feedback import (
    get_feedback_functions,
    _suppress_trulens_import_noise,
)

with _suppress_trulens_import_noise():
    from trulens.core import Tru
    from trulens.apps.custom import TruCustomApp
    from trulens.apps.app import instrument
from app.settings import settings

logger = logging.getLogger(__name__)


class TruLensService:
    """Service to manage TruLens observability."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TruLensService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Tru() probes optional integrations (llama_index, etc.) and emits raw
        # debug prints when they are absent; suppress that import-time noise.
        with _suppress_trulens_import_noise():
            self.tru = Tru()
        self.feedbacks = get_feedback_functions()
        self._initialized = True
        logger.info(
            "TruLensService initialized with %d feedback functions",
            len(self.feedbacks),
        )

    def get_recorder(self, app_id: str, version: str = "v1") -> TruCustomApp:
        """
        Create a TruLens recorder for the LangGraph application.

        Only the top-level ``execute`` method is decorated with
        ``@instrument`` so that TruLens creates exactly **one**
        ``record_root`` span per pipeline run.  The individual agent
        node functions are called inside ``execute`` (through the
        LangGraph stream) but are NOT themselves ``@instrument``-ed
        entry points, so they appear as children of that single root.

        The LLM-level calls (_groq_completion, etc. on LLMClient) are
        already instrumented independently and will show up as nested
        child spans.
        """

        class LangGraphApp:
            """Thin wrapper whose ``execute`` becomes the TruLens record root."""

            @instrument
            def execute(
                self,
                requisition_text: str,
                current_state: Dict[str, Any],
                execute_fn: Any,
            ) -> Dict[str, Any]:
                """
                Run the full LangGraph pipeline.

                ``execute_fn`` is a callback that invokes ``graph.stream``
                and accumulates the final state dict.  We call it here so
                that TruLens captures the entire execution under a single
                root span.
                """
                final_state = execute_fn(current_state)

                # Attach a serialisable ``output`` key so the TruLens
                # dashboard can display the final candidates list.
                try:
                    final_state["output"] = json.dumps(
                        final_state.get("final_results", []), indent=2, default=str
                    )
                except Exception:
                    final_state["output"] = str(final_state.get("final_results", ""))

                return final_state

        app_instance = LangGraphApp()

        return TruCustomApp(
            app_id=app_id,
            app=app_instance,
            main_method=app_instance.execute,
            app_version=version,
            feedbacks=self.feedbacks,
        )

    def start_dashboard(self, port: int = 8501):
        """Start the TruLens dashboard."""
        try:
            self.tru.run_dashboard(port=port, force=True)
            logger.info(f"TruLens dashboard started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start TruLens dashboard: {str(e)}")

    def stop_dashboard(self):
        """Stop the TruLens dashboard."""
        try:
            self.tru.stop_dashboard()
            logger.info("TruLens dashboard stopped")
        except Exception as e:
            logger.error(f"Failed to stop TruLens dashboard: {str(e)}")


# Singleton instance
trulens_service = TruLensService()
