import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from src.app.db.session import get_db
from src.app.ai.availability_graph import availability_graph
from src.app.ai.agents.candidate_availability import CandidateAvailabilityRequest, CandidateAvailabilityResponse
from uuid import uuid4

router = APIRouter(prefix="/agents", tags=["candidate-availability"])

@router.post("/candidate-availability", response_model=CandidateAvailabilityResponse, status_code=200)
async def candidate_availability_endpoint(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        payload = await request.json()
        req_id = str(uuid4())
        logger = logging.getLogger("candidate_availability")
        logger.info(f"Received candidate availability request", extra={"request_id": req_id, "count": len(payload.get('team_member_ids', [])) or 1})
        # Run the LangGraph workflow
        state = {"input_data": payload, "db": db}
        result = await availability_graph.invoke_async(payload)
        logger.info(f"Candidate availability completed", extra={"request_id": req_id})
        return result
    except Exception as e:
        logger = logging.getLogger("candidate_availability")
        logger.error(f"Error in candidate availability endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
