"""Health check endpoint."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Health check endpoint with database connectivity check.
    
    Returns:
        200 OK if system is healthy
        503 Service Unavailable if database is unreachable
    """
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "checks": {}
    }
    
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
        logger.info("Health check passed", extra={"checks": health_status["checks"]})
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_status
        )
    except Exception as exc:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"unhealthy: {str(exc)}"
        logger.error(
            "Health check failed",
            extra={"checks": health_status["checks"], "error": str(exc)},
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )

