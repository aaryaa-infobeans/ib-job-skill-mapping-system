"""Job description to skill mapping router."""
from fastapi import APIRouter

router = APIRouter(prefix="/jd-skill-mapping")


@router.post("/")
async def create_jd_skill_mapping():
    """Create job description to skill mapping."""
    # TODO: Implement endpoint
    return {"message": "Not implemented"}
