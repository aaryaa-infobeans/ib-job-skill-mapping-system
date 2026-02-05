"""LangGraph definition."""

import logging

from langgraph.graph import StateGraph, END

from app.ai.state import GraphState
from app.ai.agents.requisition_parsing import requisition_parsing_node
from app.ai.agents.skill_normalization import skill_normalization_node
from app.ai.agents.matching_scoring import matching_scoring_node
from app.ai.agents.explanation_generation import explanation_generation_node
from app.ai.agents.result_aggregation import result_aggregation_node

logger = logging.getLogger(__name__)


def create_graph():
    """Create the LangGraph for JD-Skill matching.
    
    Linear topology:
    START → JD_Parsing → Skill_Normalization → Matching_Scoring → 
    Explanation_Generation → Result_Aggregation → END
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("requisition_parsing", requisition_parsing_node)
    workflow.add_node("skill_normalization", skill_normalization_node)
    workflow.add_node("matching_scoring", matching_scoring_node)
    workflow.add_node("explanation_generation", explanation_generation_node)
    workflow.add_node("result_aggregation", result_aggregation_node)
    
    # Define linear edges
    workflow.set_entry_point("requisition_parsing")
    workflow.add_edge("requisition_parsing", "skill_normalization")
    workflow.add_edge("skill_normalization", "matching_scoring")
    workflow.add_edge("matching_scoring", "explanation_generation")
    workflow.add_edge("explanation_generation", "result_aggregation")
    workflow.add_edge("result_aggregation", END)
    
    # Compile and return
    graph = workflow.compile()
    logger.info("LangGraph compiled successfully")
    return graph
