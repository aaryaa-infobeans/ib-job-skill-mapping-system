"""RAG Retrieval node for LangGraph."""

import logging
import numpy as np
from typing import Dict, List, Any

from app.ai.state import GraphState
from app.ai.utils.rag_retrieval import RAGRetrievalAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

def rag_retrieval_node(state: GraphState) -> GraphState:
    """Execute RAG retrieval using embeddings."""
    logger.info("Executing RAG_Retrieval_Agent node")
    
    # Reset error message for this node run
    state["error_message"] = None
    
    embedding_data = state.get("embedding_result")
    if not embedding_data:
        logger.warning("No embedding_result in state, skipping RAG retrieval")
        state["retrieved_candidates"] = []
        return state
    
    try:
        # 1. Prepare EmbeddingResult
        embedding_result = EmbeddingResult(
            jd_level_vector=np.array(embedding_data.get("jd_level_vector")),
            mandatory_vector=np.array(embedding_data.get("mandatory_vector")),
            preferred_vector=np.array(embedding_data.get("preferred_vector")),
            certification_vector=np.array(embedding_data.get("certification_vector")) if embedding_data.get("certification_vector") else None,
            model=embedding_data.get("model", "models/embedding-001")
        )
        
        # 2. Get requirements from state for Hard Filters
        parsed_jd = state.get("parsed_jd") or {}
        normalized_skills = state.get("normalized_skills") or {}
        
        jd_text = parsed_jd.get("jd_text", "")
        mandatory_ids = normalized_skills.get("mandatory_skill_ids", [])
        preferred_ids = normalized_skills.get("preferred_skill_ids", [])
        
        experience_req = parsed_jd.get("experience") or {}
        min_experience_months = experience_req.get("min_months")
        
        initial_filter_ids = state.get("target_member_ids")
        
        # 3. Initialize and execute RAG agent
        db = SessionLocal()
        try:
            agent = RAGRetrievalAgent(db_connection=db)
            candidates = agent.execute(
                embedding_result, 
                query_text=jd_text, 
                filter_ids=initial_filter_ids,
                mandatory_ids=mandatory_ids,
                preferred_ids=preferred_ids,
                min_experience_months=min_experience_months
            )
            
            # Convert RAGCandidate objects to dicts for state
            state["retrieved_candidates"] = [
                {
                    "team_member_id": c.team_member_id,
                    "final_similarity": c.final_similarity,
                    "mandatory_similarity": c.mandatory_similarity,
                    "preferred_similarity": c.preferred_similarity,
                    "jd_level_similarity": c.jd_level_similarity,
                    "certification_similarity": c.certification_similarity,
                    "phase0_score_breakdown": c.phase0_score_breakdown
                }
                for c in candidates
            ]
            
            logger.info(f"RAG_Retrieval_Agent completed with {len(state['retrieved_candidates'])} candidates (Hybrid BM25+Gemma)")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in rag_retrieval_node: {str(e)}", exc_info=True)
        state["error_message"] = f"RAG retrieval failed: {str(e)}"
        state["retrieved_candidates"] = []
        
    return state
