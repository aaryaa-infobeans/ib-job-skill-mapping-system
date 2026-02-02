"""Job description to skill mapping router."""

import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.schemas.requisition import RequisitionRequest, RequisitionResponse
from app.db.repositories.requisition_repository import RequisitionRepository
from app.db.session import get_db
from app.ai.graph import create_graph

router = APIRouter(prefix="/jd-skill-mapping", tags=["jd-skill-mapping"])
logger = logging.getLogger(__name__)


def process_requisition_with_graph(correlation_id: str, request: RequisitionRequest):
    """Background task to process requisition through LangGraph."""
    try:
        logger.info(f"Starting graph processing for correlation_id={correlation_id}")
        
        # Create graph
        graph = create_graph()
        
        # Prepare initial state
        initial_state = {
            "requisition_input": {
                "request_id": request.request_id,
                "job_description": request.job_description.jd_text,
                "requested_team_ids": [],  # TODO: Add team filtering support
                "min_availability_percentage": 50,  # Default value
                "correlation_id": correlation_id,
            },
            "parsed_jd": None,
            "normalized_skills": None,
            "candidate_scores": None,
            "final_results": None,
            "error_message": None,
        }
        
        # Run graph
        final_state = graph.invoke(initial_state)
        
        logger.info(f"Graph processing completed for correlation_id={correlation_id}")
        logger.info(f"Final results: {final_state.get('final_results')}")
        
    except Exception as e:
        logger.error(f"Error processing requisition with graph: {str(e)}", exc_info=True)


@router.post("/", response_model=RequisitionResponse, status_code=202)
async def create_jd_skill_mapping(
    request: RequisitionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a job description to skill mapping requisition.

    This endpoint accepts a requisition request, validates it, persists it,
    and queues it for AI processing.
    """
    repo = RequisitionRepository(db)

    # Check for duplicate request_id
    existing = repo.get_requisition_by_request_id(request.request_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Request with request_id {request.request_id} already exists",
        )

    try:
        # Create requisition (using default auth_client_id=1 for now)
        req, correlation_id = repo.create_requisition(request, auth_client_id=1)
        db.commit()

        # Queue graph processing as background task
        background_tasks.add_task(process_requisition_with_graph, correlation_id, request)
        
        logger.info(f"Queued graph processing for correlation_id={correlation_id}")

        return RequisitionResponse(
            correlation_id=correlation_id,
            status="QUEUED_FOR_PROCESSING",
            received_at=req.received_at,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
