"""Matches router."""
from fastapi import APIRouter

router = APIRouter(prefix="/matches")


@router.get("/")
async def get_matches():
    """Get matches."""
    # TODO: Implement endpoint
    return {"message": "Not implemented"}
