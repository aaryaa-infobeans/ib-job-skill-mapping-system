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
    
    # Get token metrics from state if available
    token_metrics = final_state.get("token_metrics", {})
    
    # Checkpoint 1: JD Parsing
    if final_state.get("parsed_jd"):
        jd_parsing_tokens = token_metrics.get("jd_parsing", {}).get("total_tokens")
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="jd_parsing",
            state={
                "parsed_jd": final_state.get("parsed_jd"),
                "correlation_id": correlation_id,
            },
            token_count=jd_parsing_tokens,
        )
    
    # Checkpoint 2: Skill Normalization
    if final_state.get("normalized_skills"):
        skill_norm_tokens = token_metrics.get("skill_normalization", {}).get("total_tokens")
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="skill_normalization",
            state={
                "normalized_skills": final_state.get("normalized_skills"),
                "correlation_id": correlation_id,
            },
            token_count=skill_norm_tokens,
        )
    
    # Checkpoint 3: Matching & Scoring
    if final_state.get("candidate_scores"):
        matching_tokens = token_metrics.get("matching_scoring", {}).get("total_tokens")
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="matching_scoring",
            state={
                "candidate_count": len(final_state.get("candidate_scores", [])),
                "correlation_id": correlation_id,
            },
            token_count=matching_tokens,
        )
    
    # Checkpoint 4: Explanation Generation
    if final_state.get("candidate_scores"):
        explanation_tokens = token_metrics.get("explanation_generation", {}).get("total_tokens")
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="explanation_generation",
            state={
                "candidate_count": len(final_state.get("candidate_scores", [])),
                "correlation_id": correlation_id,
                "qualified_count": final_state.get("total_qualified", 0),
            },
            token_count=explanation_tokens,
        )
    
    # Checkpoint 5: Result Aggregation (final)
    if final_state.get("final_results"):
        result_tokens = token_metrics.get("result_aggregation", {}).get("total_tokens")
        save_checkpoint(
            db=db,
            request_id=request_id,
            node_name="result_aggregation",
            state={
                "result_count": len(final_state.get("final_results", [])),
                "correlation_id": correlation_id,
                "status": "completed",
                "total_evaluated": final_state.get("total_evaluated", 0),
                "total_qualified": final_state.get("total_qualified", 0),
            },
            token_count=result_tokens,
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
    
    # Log final token summary
    cumulative_tokens = final_state.get("cumulative_tokens", 0)
    cumulative_cost = final_state.get("cumulative_cost_usd", 0.0)
    if cumulative_tokens > 0:
        logger.info(
            f"Graph execution completed with token summary: "
            f"{cumulative_tokens} total tokens, ${cumulative_cost:.6f} cost",
            extra={
                "request_id": request_id,
                "cumulative_tokens": cumulative_tokens,
                "cumulative_cost_usd": cumulative_cost,
            }
        )
    else:
        logger.info(
            "Graph execution completed with audit",
            extra={"request_id": request_id}
        )
    
    return final_state
