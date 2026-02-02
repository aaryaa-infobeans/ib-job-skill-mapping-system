"""Job description parsing agent."""

import logging

from app.ai.state import GraphState

logger = logging.getLogger(__name__)


def jd_parsing_node(state: GraphState) -> GraphState:
    """Parse job description and extract structured information.
    
    This is a stub implementation that logs execution.
    """
    logger.info("Executing JD_Parsing_Agent node")
    logger.info(f"Processing request_id: {state['requisition_input']['request_id']}")
    
    # Stub: Create placeholder parsed JD
    state["parsed_jd"] = {
        "normalized_title": "Software Engineer",
        "normalized_role": "Developer",
        "extracted_mandatory_skills": ["Python", "FastAPI"],
        "extracted_preferred_skills": ["Docker", "Kubernetes"],
    }
    
    logger.info("JD_Parsing_Agent completed")
    return state
