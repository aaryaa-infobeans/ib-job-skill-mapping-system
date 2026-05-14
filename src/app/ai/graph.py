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


def should_continue(state: GraphState) -> str:
    """
    Generic conditional edge to stop the graph if an error exists.
    """
    error_message = state.get("error_message")
    if error_message:
        logger.warning(f"Stopping graph execution due to error: {error_message}")
        return "END"
    return "CONTINUE"


def create_graph(instrumented_app=None):
    """Create the LangGraph for JD-Skill matching with PII Scrubber."""
    workflow = StateGraph(GraphState)
    
    # Add nodes
    if instrumented_app:
        workflow.add_node("requisition_parsing", instrumented_app.requisition_parsing)
        workflow.add_node("skill_normalization", instrumented_app.skill_normalization)
        workflow.add_node("embedding", instrumented_app.embedding)
        workflow.add_node("rag_retrieval", instrumented_app.rag_retrieval)
        workflow.add_node("matching_scoring", instrumented_app.matching_scoring)
        workflow.add_node("explanation_generation", instrumented_app.explanation_generation)
        workflow.add_node("result_aggregation", instrumented_app.result_aggregation)
    else:
        workflow.add_node("requisition_parsing", requisition_parsing_node)
        workflow.add_node("skill_normalization", skill_normalization_node)
        workflow.add_node("embedding", embedding_node)
        workflow.add_node("rag_retrieval", rag_retrieval_node)
        workflow.add_node("matching_scoring", matching_scoring_node)
        workflow.add_node("explanation_generation", explanation_generation_node)
        workflow.add_node("result_aggregation", result_aggregation_node)
    
    # Define entry point
    workflow.set_entry_point("requisition_parsing")

    # Requisition Parsing -> Skill Normalization (or END on error)
    workflow.add_conditional_edges(
        "requisition_parsing",
        should_continue_after_parsing,
        {
            "END": END,
            "skill_normalization": "skill_normalization"
        }
    )
    
    # Skill Normalization -> Embedding (or END)
    workflow.add_conditional_edges(
        "skill_normalization",
        should_continue,
        {
            "END": END,
            "CONTINUE": "embedding"
        }
    )

    # Embedding -> RAG Retrieval (or END)
    workflow.add_conditional_edges(
        "embedding",
        should_continue,
        {
            "END": END,
            "CONTINUE": "rag_retrieval"
        }
    )

    # RAG Retrieval -> Matching Scoring (or END)
    workflow.add_conditional_edges(
        "rag_retrieval",
        should_continue,
        {
            "END": END,
            "CONTINUE": "matching_scoring"
        }
    )

    # Matching Scoring -> Explanation Generation (or END)
    workflow.add_conditional_edges(
        "matching_scoring",
        should_continue,
        {
            "END": END,
            "CONTINUE": "explanation_generation"
        }
    )

    # Explanation Generation -> Result Aggregation (or END)
    workflow.add_conditional_edges(
        "explanation_generation",
        should_continue,
        {
            "END": END,
            "CONTINUE": "result_aggregation"
        }
    )
    
    workflow.add_edge("result_aggregation", END)
    
    # Compile and return
    graph = workflow.compile()
    logger.info("LangGraph compiled successfully with fail-fast error handling")
    return graph
