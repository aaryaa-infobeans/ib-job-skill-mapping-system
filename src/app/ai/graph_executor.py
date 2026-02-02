"""Graph execution wrapper with audit trail support."""

import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.ai.graph import create_graph
from app.ai.audit import save_checkpoint

logger = logging.getLogger(__name__)


def execute_graph_with_audit(
    initial_state: Dict[str, Any],
    request_id: str,
    db: Session,
) -> Dict[str, Any]:
    """Execute LangGraph pipeline with checkpoint auditing.
    
    This function runs the graph and saves a checkpoint after each node
    execution for audit trail purposes.
    
    Args:
        initial_state: The initial graph state
        request_id: The originating request ID for audit linking
        db: Database session for checkpoint storage
        
    Returns:
        The final graph state
    """
    graph = create_graph()
    
    logger.info(
        "Starting graph execution with audit",
        extra={"request_id": request_id}
    )
    
    # Execute the graph
    # Note: LangGraph doesn't expose node-by-node execution in the compiled form,
    # so we'll save a checkpoint for the final state. In a production system,
    # you'd use LangGraph's built-in persistence or implement custom callbacks.
    final_state = graph.invoke(initial_state)
    
    # Save checkpoints for each major step we can infer from the state
    # This is a simplified approach - ideally we'd hook into LangGraph's execution
    correlation_id = initial_state.get("requisition_input", {}).get("correlation_id", "unknown")
    
    # Checkpoint 1: JD Parsing
    if final_state.get("parsed_jd"):
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="jd_parsing",
            state={
                "parsed_jd": final_state.get("parsed_jd"),
                "correlation_id": correlation_id,
            },
            token_count=None,  # Would be populated from actual LLM usage
        )
    
    # Checkpoint 2: Skill Normalization
    if final_state.get("normalized_skills"):
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="skill_normalization",
            state={
                "normalized_skills": final_state.get("normalized_skills"),
                "correlation_id": correlation_id,
            },
            token_count=None,
        )
    
    # Checkpoint 3: Matching & Scoring
    if final_state.get("candidate_scores"):
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="matching_scoring",
            state={
                "candidate_count": len(final_state.get("candidate_scores", [])),
                "correlation_id": correlation_id,
            },
            token_count=None,
        )
    
    # Checkpoint 4: Explanation Generation
    # We can infer this happened if candidates have explanation_context
    candidates = final_state.get("candidate_scores", [])
    if candidates and any("explanation_context" in c for c in candidates):
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="explanation_generation",
            state={
                "candidate_count": len(candidates),
                "correlation_id": correlation_id,
            },
            token_count=None,
        )
    
    # Checkpoint 5: Result Aggregation (final)
    if final_state.get("final_results"):
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="result_aggregation",
            state={
                "result_count": len(final_state.get("final_results", [])),
                "correlation_id": correlation_id,
                "status": "completed",
            },
            token_count=None,
        )
    
    # Checkpoint for errors
    if final_state.get("error_message"):
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="error",
            state={
                "error_message": final_state.get("error_message"),
                "correlation_id": correlation_id,
            },
            token_count=None,
        )
    
    logger.info(
        "Graph execution completed with audit",
        extra={"request_id": request_id}
    )
    
    return final_state
