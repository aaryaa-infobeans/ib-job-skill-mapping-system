"""Job description to skill mapping router."""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.requisition import RequisitionRequest, RequisitionResponse
from app.db.repositories.requisition_repository import RequisitionRepository
from app.db.session import get_db

router = APIRouter(prefix="/jd-skill-mapping", tags=["jd-skill-mapping"])


@router.post("/", response_model=RequisitionResponse, status_code=202)
async def create_jd_skill_mapping(request: RequisitionRequest, db: Session = Depends(get_db)):
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

        return RequisitionResponse(
            correlation_id=correlation_id,
            status="QUEUED_FOR_PROCESSING",
            received_at=req.received_at,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
