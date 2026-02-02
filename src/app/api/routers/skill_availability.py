"""Skill availability router."""

from fastapi import APIRouter

router = APIRouter(prefix="/skill-availability")


@router.post("/")
async def upsert_skill_availability():
    """Upsert skill availability."""
    # TODO: Implement endpoint
    return {"message": "Not implemented"}
