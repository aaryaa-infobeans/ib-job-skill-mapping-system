"""LangGraph Workflow for requisition skill matching."""

import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from src.app.ai.agents.requisition_parser import RequisitionParserAgent
from src.app.ai.agents.validation import ValidationAgent
from src.app.ai.agents.normalizer import NormalizerAgent
from src.app.ai.agents.embedding import EmbeddingAgent
from src.app.ai.agents.rag_retrieval import RAGRetrievalAgent
from src.app.ai.agents.scoring import ScoringAgent
from src.app.ai.agents.ranking import RankingAgent
from src.app.ai.agents.models import (
    RequisitionData,
    ValidationResult,
    NormalizedRequisition,
    EmbeddingResult,
    RankedCandidateList,
    ScoringResult,
    RAGCandidate,
)


class WorkflowState(Dict[str, Any]):
    """State dictionary for workflow execution."""
    
    def __setitem__(self, key, value):
        """Override to allow state updates."""
        super().__setitem__(key, value)


class RequisitionMatchingWorkflow:
    """DAG-based workflow for requisition skill matching."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("workflow")
        
        # Initialize agents
        self.parser = RequisitionParserAgent(logger)
        self.validator = ValidationAgent(logger)
        self.normalizer = NormalizerAgent(logger=logger)
        self.embedding = EmbeddingAgent(logger)
        self.rag = RAGRetrievalAgent(logger=logger)
        self.scoring = ScoringAgent(logger)
        self.ranking = RankingAgent(logger)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph DAG."""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("parse", self._node_parse)
        workflow.add_node("validate", self._node_validate)
        workflow.add_node("normalize", self._node_normalize)
        workflow.add_node("embed", self._node_embed)
        workflow.add_node("rag_retrieve", self._node_rag_retrieve)
        workflow.add_node("score", self._node_score)
        workflow.add_node("rank", self._node_rank)
        workflow.add_node("failed", self._node_failed)
        
        # Add edges
        workflow.add_edge(START, "parse")
        workflow.add_edge("parse", "validate")
        workflow.add_conditional_edges(
            "validate",
            self._should_continue_after_validation,
            {
                "continue": "normalize",
                "failed": "failed"
            }
        )
        workflow.add_edge("normalize", "embed")
        workflow.add_edge("embed", "rag_retrieve")
        workflow.add_edge("rag_retrieve", "score")
        workflow.add_edge("score", "rank")
        workflow.add_edge("rank", END)
        workflow.add_edge("failed", END)
        
        return workflow.compile()
    
    def _node_parse(self, state: Dict) -> Dict:
        """Parse raw requisition."""
        try:
            raw_req = state.get("raw_requisition")
            parsed = self.parser._execute_with_context(raw_req)
            state["requisition_data"] = parsed
            state["step"] = "parse"
            return state
        except Exception as e:
            self.logger.error(f"Parse step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _node_validate(self, state: Dict) -> Dict:
        """Validate requisition."""
        try:
            req_data = state.get("requisition_data")
            validation_result = self.validator._execute_with_context(req_data)
            state["validation_result"] = validation_result
            state["step"] = "validate"
            return state
        except Exception as e:
            self.logger.error(f"Validate step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _should_continue_after_validation(self, state: Dict) -> str:
        """Determine if we should continue after validation."""
        validation_result = state.get("validation_result")
        if validation_result and not validation_result.is_valid:
            self.logger.info(f"Validation failed: {validation_result.reasons}")
            return "failed"
        return "continue"
    
    def _node_normalize(self, state: Dict) -> Dict:
        """Normalize and expand skills."""
        try:
            req_data = state.get("requisition_data")
            normalized = self.normalizer._execute_with_context(req_data)
            state["normalized_requisition"] = normalized
            state["step"] = "normalize"
            return state
        except Exception as e:
            self.logger.error(f"Normalize step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _node_embed(self, state: Dict) -> Dict:
        """Generate embeddings."""
        try:
            normalized = state.get("normalized_requisition")
            embeddings = self.embedding._execute_with_context(normalized)
            state["embeddings"] = embeddings
            state["step"] = "embed"
            return state
        except Exception as e:
            self.logger.error(f"Embed step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _node_rag_retrieve(self, state: Dict) -> Dict:
        """Retrieve candidates via RAG."""
        try:
            embeddings = state.get("embeddings")
            candidates = self.rag._execute_with_context(embeddings)
            state["rag_candidates"] = candidates
            state["step"] = "rag_retrieve"
            return state
        except Exception as e:
            self.logger.error(f"RAG retrieve step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _node_score(self, state: Dict) -> Dict:
        """Score candidates."""
        try:
            rag_candidates = state.get("rag_candidates", [])
            scored_candidates = []
            
            for candidate in rag_candidates:
                scored = self.scoring._execute_with_context(candidate)
                scored_candidates.append(scored)
            
            state["scored_candidates"] = scored_candidates
            state["step"] = "score"
            return state
        except Exception as e:
            self.logger.error(f"Scoring step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _node_rank(self, state: Dict) -> Dict:
        """Rank and justify candidates."""
        try:
            scored_candidates = state.get("scored_candidates", [])
            ranked = self.ranking._execute_with_context(scored_candidates)
            state["ranked_candidates"] = ranked
            state["step"] = "rank"
            return state
        except Exception as e:
            self.logger.error(f"Ranking step failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    def _node_failed(self, state: Dict) -> Dict:
        """Handle workflow failure."""
        state["step"] = "failed"
        state["success"] = False
        return state
    
    def execute(self, raw_requisition: str) -> Dict:
        """
        Execute the complete workflow.
        
        Args:
            raw_requisition: Raw requisition JSON string
            
        Returns:
            Final state dict with results
        """
        initial_state = {
            "raw_requisition": raw_requisition,
            "success": True,
            "step": "start"
        }
        
        # Run workflow
        final_state = self.graph.invoke(initial_state)
        
        return final_state
