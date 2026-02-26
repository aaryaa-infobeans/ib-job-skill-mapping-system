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
    
    # 1. Update status to PROCESSING (ID: 2)
    from app.db.repositories.requisition_repository import RequisitionRepository
    repo = RequisitionRepository(db)
    req_record = repo.get_requisition_by_request_id(request_id)
    if req_record:
        repo.update_requisition_status(req_record.id, 2)
        db.commit()

    correlation_id = initial_state.get("requisition_input", {}).get("correlation_id", "unknown")
    current_state = initial_state
    
    # 2. Execute the graph using stream to capture each node completion
    try:
        processed_logs_count = 0
        for event in graph.stream(current_state):
            for node_name, state_update in event.items():
                logger.info(f"Node '{node_name}' completed, saving checkpoint.")
                
                # Update current state with node outputs
                current_state.update(state_update)
                
                # Extract token metrics for this specific node
                token_metrics = state_update.get("token_metrics", {}).get(node_name, {})
                token_count = token_metrics.get("total_tokens")
                
                # 2a. Save any NEW LLM logs generated in this step
                llm_logs = current_state.get("llm_call_logs", [])
                if len(llm_logs) > processed_logs_count:
                    from app.ai.audit import save_llm_request_log
                    for i in range(processed_logs_count, len(llm_logs)):
                        log = llm_logs[i]
                        save_llm_request_log(
                            db=db,
                            request_id=request_id,
                            agent_name=log.get("agent_name"),
                            prompt_name=log.get("prompt_name"),
                            model=log.get("model"),
                            prompt_tokens=log.get("prompt_tokens"),
                            completion_tokens=log.get("completion_tokens"),
                            cost_usd=log.get("cost_usd"),
                            status=log.get("status", "SUCCESS"),
                            error_message=log.get("error_message"),
                        )
                    processed_logs_count = len(llm_logs)
                
                # 2b. Prepare and save checkpoint
                # We save a subset of the state to keep the DB lean but sufficient for resumption.
                # Redundant fields like llm_call_logs are excluded as they are in their own table.
                checkpoint_state = {
                    "correlation_id": correlation_id,
                    "parsed_jd": current_state.get("parsed_jd"),
                    "normalized_skills": current_state.get("normalized_skills"),
                    "retrieved_candidates": current_state.get("retrieved_candidates"),
                    "candidate_scores": current_state.get("candidate_scores"),
                    "final_results": current_state.get("final_results"),
                    "total_evaluated": current_state.get("total_evaluated"),
                    "total_qualified": current_state.get("total_qualified"),
                    "cumulative_tokens": current_state.get("cumulative_tokens"),
                    "cumulative_cost_usd": current_state.get("cumulative_cost_usd"),
                }
                
                # Update status based on node completion
                if node_name == "requisition_parsing":
                    if req_record:
                        repo.update_requisition_status(req_record.id, 3) # MATCHING
                        db.commit()
                
                # Handle error state if node reported a FATAL error
                error_message = current_state.get("error_message")
                if error_message:
                    checkpoint_state["error_message"] = error_message
                    # Save with actual node name but include error_message
                    save_checkpoint(
                        db=db,
                        request_id=request_id,
                        node_name=node_name,
                        state=checkpoint_state,
                        token_count=token_count
                    )
                    
                    # If it's a fatal error (not a fallback), we might want to stop
                    if "fallback" not in error_message.lower():
                        logger.error(f"Fatal error in node {node_name}: {error_message}")
                        if req_record:
                            repo.update_requisition_status(req_record.id, 5) # FAILED
                            db.commit()
                else:
                    # Save normal node checkpoint
                    save_checkpoint(
                        db=db,
                        request_id=request_id,
                        node_name=node_name,
                        state=checkpoint_state,
                        token_count=token_count
                    )

        # 3. Finalize and Store Results
        final_state = current_state
        final_results = final_state.get("final_results", [])
        
        if final_results is not None and not final_state.get("error_message"):
            from app.ai.results_cache import store_results
            metrics = {
                "total_evaluated": final_state.get("total_evaluated", 0),
                "total_qualified": final_state.get("total_qualified", 0),
                "token_count": final_state.get("cumulative_tokens", 0),
                "cost_usd": final_state.get("cumulative_cost_usd", 0.0),
            }
            store_results(correlation_id, final_results, metrics=metrics)
            if req_record:
                from datetime import datetime
                repo.update_requisition_status(req_record.id, 4, completed_at=datetime.utcnow()) # COMPLETED
                db.commit()
        
        # 4. Final summary
        cumulative_tokens = final_state.get("cumulative_tokens", 0)
        cumulative_cost = final_state.get("cumulative_cost_usd", 0.0)
        logger.info(
            f"Graph execution completed. Summary: {cumulative_tokens} tokens, ${cumulative_cost:.6f} cost",
            extra={"request_id": request_id}
        )
        
        return final_state

    except Exception as e:
        logger.exception(f"Fatal error during graph execution: {str(e)}", extra={"request_id": request_id})
        if req_record:
            repo.update_requisition_status(req_record.id, 5)
            db.commit()
        raise
