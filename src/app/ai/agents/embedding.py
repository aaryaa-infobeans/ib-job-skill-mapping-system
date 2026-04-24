"""Embedding node for LangGraph."""

import logging
from typing import Dict, List, Any

from app.ai.state import GraphState
from app.ai.utils.embedding import EmbeddingAgent
from app.ai.utils.models import NormalizedRequisition, RequisitionData
from app.observability.tracing import trace_node

logger = logging.getLogger(__name__)

@trace_node("embedding")
def embedding_node(state: GraphState) -> GraphState:
    """Generate embeddings for JD components."""
    logger.info("Executing Embedding_Agent node")
    
    # Reset error message for this node run
    state["error_message"] = None
    
    parsed_jd = state.get("parsed_jd")
    normalized_skills = state.get("normalized_skills")
    
    if not parsed_jd or not normalized_skills:
        logger.warning("Missing parsed_jd or normalized_skills, skipping embedding")
        return state
        
    try:
        # Map state to RequisitionData (Utility model)
        requisition_data = RequisitionData(
            structured_intent=parsed_jd.get("normalized_title", ""),
            mandatory_skills=parsed_jd.get("extracted_mandatory_skills", []),
            preferred_skills=parsed_jd.get("extracted_preferred_skills", []),
            experience_requirements=str(parsed_jd.get("experience", "")),
            jd_level=parsed_jd.get("normalized_role", ""),
            location=", ".join(parsed_jd.get("location", [])),
            certifications=parsed_jd.get("certifications_required", []),
            raw_requisition=state["requisition_input"].get("job_description")
        )
        
        # Map to NormalizedRequisition
        norm_req = NormalizedRequisition(
            original_mandatory_skills=parsed_jd.get("extracted_mandatory_skills", []),
            normalized_mandatory_skills=normalized_skills.get("mandatory_skill_ids", []),
            expanded_mandatory_terms=list(normalized_skills.get("mandatory_enriched", {}).keys()),
            original_preferred_skills=parsed_jd.get("extracted_preferred_skills", []),
            normalized_preferred_skills=normalized_skills.get("preferred_skill_ids", []),
            expanded_preferred_terms=list(normalized_skills.get("preferred_enriched", {}).keys()),
            original_certifications=normalized_skills.get("original_certifications", []),
            normalized_certifications=normalized_skills.get("normalized_certifications", []),
            expanded_certification_terms=list(normalized_skills.get("certification_enriched", {}).keys()),
            original_requisition=requisition_data
        )
        
        # Initialize and execute agent
        agent = EmbeddingAgent()
        embedding_result = agent.execute(norm_req)
        
        # Convert EmbeddingResult to dict for state (convert np to list for JSON)
        state["embedding_result"] = {
            "jd_level_vector": embedding_result.jd_level_vector.tolist() if embedding_result.jd_level_vector is not None else None,
            "mandatory_vector": embedding_result.mandatory_vector.tolist() if embedding_result.mandatory_vector is not None else None,
            "preferred_vector": embedding_result.preferred_vector.tolist() if embedding_result.preferred_vector is not None else None,
            "certification_vector": embedding_result.certification_vector.tolist() if embedding_result.certification_vector is not None else None,
            "full_jd_vector": embedding_result.full_jd_vector.tolist() if embedding_result.full_jd_vector is not None else None,
            "model": embedding_result.model
        }
        
        logger.info("Embedding_Agent completed successfully")
        
    except Exception as e:
        logger.error(f"Error in embedding_node: {str(e)}", exc_info=True)
        state["error_message"] = f"Embedding generation failed: {str(e)}"
        
    return state
