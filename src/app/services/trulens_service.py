"""TruLens service for observability and instrumentation."""

import logging
import os
from typing import Any, Dict, List, Optional

from trulens_eval import Tru, TruChain, TruCustomApp
from trulens_eval.tru_custom_app import instrument

from app.evaluation.feedback import get_feedback_functions
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
            
        self.tru = Tru()
        # Initialize database if not exists
        # self.tru.migrate_database() 
        
        self.feedbacks = get_feedback_functions()
        self._initialized = True
        logger.info("TruLensService initialized with %d feedback functions", len(self.feedbacks))

    def get_recorder(self, app_id: str, version: str = "v1") -> TruCustomApp:
        """
        Create a TruLens recorder for the LangGraph application.
        """
        from app.ai.agents.pii_scrubber import pii_scrubber_node
        from app.ai.agents.requisition_parsing import requisition_parsing_node
        from app.ai.agents.skill_normalization import skill_normalization_node
        from app.ai.agents.embedding import embedding_node
        from app.ai.agents.rag_retrieval import rag_retrieval_node
        from app.ai.agents.matching_scoring import matching_scoring_node
        from app.ai.agents.explanation_generation import explanation_generation_node
        from app.ai.agents.result_aggregation import result_aggregation_node

        class LangGraphApp:
            @instrument
            def execute(self, state, request_id=None):
                # This is the entry point for TruLens recording
                from app.ai.graph import create_graph
                graph = create_graph()
                # Use invoke instead of stream for simple recording, 
                # or we can wrap the stream loop here
                return graph.invoke(state)

            @instrument
            def pii_scrubber(self, state): return pii_scrubber_node(state)
            @instrument
            def requisition_parsing(self, state): return requisition_parsing_node(state)
            @instrument
            def skill_normalization(self, state): return skill_normalization_node(state)
            @instrument
            def embedding(self, state): return embedding_node(state)
            @instrument
            def rag_retrieval(self, state): return rag_retrieval_node(state)
            @instrument
            def matching_scoring(self, state): return matching_scoring_node(state)
            @instrument
            def explanation_generation(self, state): return explanation_generation_node(state)
            @instrument
            def result_aggregation(self, state): return result_aggregation_node(state)

        return TruCustomApp(
            app_id=app_id,
            app=LangGraphApp(),
            app_version=version,
            feedbacks=self.feedbacks
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
