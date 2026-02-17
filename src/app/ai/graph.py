"""LangGraph definition with PII Scrubber (Node 0)."""

import logging

from langgraph.graph import StateGraph, END

from app.ai.state import GraphState
from app.ai.agents.pii_scrubber import pii_scrubber_node, should_continue_after_pii_scrubbing
from app.ai.agents.requisition_parsing import requisition_parsing_node
from app.ai.agents.skill_normalization import skill_normalization_node
from app.ai.agents.embedding import embedding_node
from app.ai.agents.rag_retrieval import rag_retrieval_node
from app.ai.agents.matching_scoring import matching_scoring_node
from app.ai.agents.explanation_generation import explanation_generation_node
from app.ai.agents.result_aggregation import result_aggregation_node

logger = logging.getLogger(__name__)


def should_continue_after_parsing(state: GraphState) -> str:
    """
    Determine if the graph should continue after requisition parsing.
    
    If there's an error (e.g., validation failure), stop the graph.
    Otherwise, continue to skill normalization.
    
    Args:
        state: Current graph state
        
    Returns:
        "END" if error exists, "skill_normalization" otherwise
    """
    error_message = state.get("error_message")
    
    if error_message:
        logger.warning(f"Stopping graph execution due to error: {error_message}")
        return "END"
    
    return "skill_normalization"


def create_graph():
    """Create the LangGraph for JD-Skill matching with PII Scrubber.
    
    Topology v1.1 (CR-PII-001):
    START → PII_Scrubber (Node 0) → [Validation Gate]
                                    ↓ (if pii_scrubbed=False) → END (HTTP 422)
                                    ↓ (if pii_scrubbed=True) → JD_Parsing → 
                                    [Check for errors]
                                    ↓ (if error) → END
                                    ↓ (if success) → Skill_Normalization → Embedding → 
                                    RAG_Retrieval → Matching_Scoring → Explanation_Generation → 
                                    Result_Aggregation → END
    
    Changes from v1.0:
    - Added Node 0: PII_Scrubber_Agent (TASK-PII-101)
    - Added validation gate after scrubbing (FR-PII-005)
    - Updated state schema with pii_scrubbed flag (TASK-PII-103)
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes (Node 0: PII Scrubber is now first)
    workflow.add_node("pii_scrubber", pii_scrubber_node)  # NEW: Node 0
    workflow.add_node("requisition_parsing", requisition_parsing_node)
    workflow.add_node("skill_normalization", skill_normalization_node)
    workflow.add_node("embedding", embedding_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("matching_scoring", matching_scoring_node)
    workflow.add_node("explanation_generation", explanation_generation_node)
    workflow.add_node("result_aggregation", result_aggregation_node)
    
    # Define edges with Node 0 as entry point
    workflow.set_entry_point("pii_scrubber")  # CHANGED: Was "requisition_parsing"
    
    # Add validation gate after PII scrubbing (FR-PII-005)
    workflow.add_conditional_edges(
        "pii_scrubber",
        should_continue_after_pii_scrubbing,
        {
            "END": END,
            "requisition_parsing": "requisition_parsing"
        }
    )
    
    # Add conditional edge after parsing to check for errors (existing logic)
    workflow.add_conditional_edges(
        "requisition_parsing",
        should_continue_after_parsing,
        {
            "END": END,
            "skill_normalization": "skill_normalization"
        }
    )
    
    # Continue with linear edges for successful path
    workflow.add_edge("skill_normalization", "embedding")
    workflow.add_edge("embedding", "rag_retrieval")
    workflow.add_edge("rag_retrieval", "matching_scoring")
    workflow.add_edge("matching_scoring", "explanation_generation")
    workflow.add_edge("explanation_generation", "result_aggregation")
    workflow.add_edge("result_aggregation", END)
    
    # Compile and return
    graph = workflow.compile()
    logger.info("LangGraph v1.1 compiled successfully with PII Scrubber (Node 0)")
    return graph
