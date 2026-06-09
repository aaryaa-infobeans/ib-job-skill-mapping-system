"""Graph execution wrapper with audit trail support."""

import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.ai.graph import create_graph
from app.ai.audit import save_checkpoint
from app.pii.audit_logger import PIIAuditLogger
from app.services.trulens_service import trulens_service

logger = logging.getLogger(__name__)


def save_pii_audit_log(
    db: Session,
    request_id: str,
    pii_metadata: Dict[str, Any]
) -> None:
    """Save PII scrubbing operation to audit trail.
    
    Args:
        db: Database session
        request_id: Request ID for linking
        pii_metadata: Metadata from PII scrubbing operation
    """
    try:
        audit_logger = PIIAuditLogger(db)
        
        for detection in pii_metadata.get("detections", []):
            audit_logger.log_scrub_operation(
                operation="scrub",
                entity_type="job_description",
                entity_id=request_id,
                field_name=detection.get("field_name", "unknown"),
                pii_type=detection.get("pii_type", "UNKNOWN"),
                action_taken=detection.get("action", "unknown"),
                scrubbed_value=f"[{detection.get('pii_type', 'UNKNOWN').upper()}_REDACTED]",
                detection_method=detection.get("method", "unknown"),
                confidence_score=detection.get("confidence", 1.0)
            )
        
        db.commit()
        logger.info(
            f"PII audit log saved: {len(pii_metadata.get('detections', []))} detections",
            extra={"request_id": request_id}
        )
    except Exception as e:
        logger.error(f"Failed to save PII audit log: {str(e)}", exc_info=True)
        db.rollback()


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
    # Initialize recorder — TruLens wraps execute() as the single record_root.
    # The graph uses the original node functions (instrumented_app=None) so that
    # each agent node does NOT create its own independent record in TruLens.
    recorder = trulens_service.get_recorder(app_id="IB-Skill-Match-Graph")
    graph = create_graph(instrumented_app=None)
    
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

    requisition_text = initial_state.get("requisition_input", {}).get("job_description", {}).get("jd_text", "")
    if not requisition_text:
        requisition_text = initial_state.get("requisition_input", {}).get("job_description", {}).get("title", "")
    correlation_id = initial_state.get("requisition_input", {}).get("correlation_id", "unknown")
    current_state = initial_state
    
    # 2. Execute the graph using stream to capture each node completion wrapped by TruLens recorder.app.execute
    
    try:
        def run_stream(state_to_run: Dict[str, Any]) -> Dict[str, Any]:
            local_state = state_to_run.copy()
            processed_logs_count = 0
            for event in graph.stream(local_state):
                for node_name, state_update in event.items():
                    logger.info(f"Node '{node_name}' completed, saving checkpoint.")
                    
                    # Update local state with node outputs
                    local_state.update(state_update)
                    
                    # Extract token metrics for this specific node
                    token_metrics = state_update.get("token_metrics", {}).get(node_name, {})
                    token_count = token_metrics.get("total_tokens")
                    
                    # 2a. Save any NEW LLM logs generated in this step
                    llm_logs = local_state.get("llm_call_logs", [])
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
                        "parsed_jd": local_state.get("parsed_jd"),
                        "normalized_skills": local_state.get("normalized_skills"),
                        "retrieved_candidates": local_state.get("retrieved_candidates"),
                        "candidate_scores": local_state.get("candidate_scores"),
                        "final_results": local_state.get("final_results"),
                        "total_evaluated": local_state.get("total_evaluated"),
                        "total_qualified": local_state.get("total_qualified"),
                        "cumulative_tokens": local_state.get("cumulative_tokens"),
                        "cumulative_cost_usd": local_state.get("cumulative_cost_usd"),
                    }
                    
                    if node_name == "pii_scrubber":
                        # Save PII scrubbing metadata and audit log
                        pii_metadata = local_state.get("pii_scrub_metadata", {})
                        checkpoint_state["pii_scrubbed"] = local_state.get("pii_scrubbed", False)
                        checkpoint_state["total_pii_found"] = pii_metadata.get("total_pii_found", 0)
                        checkpoint_state["fields_scrubbed"] = pii_metadata.get("fields_scrubbed", [])
                        
                        # Save to PII audit table if scrubbing occurred
                        if pii_metadata.get("detections"):
                            save_pii_audit_log(db, request_id, pii_metadata)
                    elif node_name == "requisition_parsing":
                        checkpoint_state["parsed_jd"] = local_state.get("parsed_jd")
                        # Update status to MATCHING (3) after JD is parsed
                        if req_record:
                            repo.update_requisition_status(req_record.id, 3) # MATCHING
                            db.commit()
                    
                    # Handle error state if node reported a FATAL error
                    error_message = local_state.get("error_message")
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
            return local_state

        # Mark when this run starts so we can compute feedback for ONLY the
        # events this run produces. Without this, compute_feedbacks(events=None)
        # re-evaluates every event for every prior record on each run, piling up
        # duplicate eval spans and re-scoring old records.
        from datetime import datetime, timezone, timedelta
        run_start = datetime.now(timezone.utc) - timedelta(seconds=1)

        with recorder as recording:
            final_state = recorder.app.execute(
                requisition_text=requisition_text,
                current_state=current_state,
                execute_fn=run_stream
            )
        current_state = final_state

        # Compute RAG feedback metrics (Answer Relevance, Context Relevance,
        # Groundedness) for THIS run only, scoping the events to those emitted
        # since run_start.
        try:
            run_events = recorder.connector.get_events(
                app_name=recorder.app_name,
                app_version=recorder.app_version,
                start_time=run_start,
            )
            recorder.compute_feedbacks(
                raise_error_on_no_feedbacks_computed=False,
                events=run_events,
            )
            logger.info(
                "TruLens feedback computation triggered for %d events from this run",
                len(run_events) if run_events is not None else 0,
            )
        except Exception as fb_err:
            logger.warning(f"TruLens feedback computation failed (non-fatal): {fb_err}")


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
