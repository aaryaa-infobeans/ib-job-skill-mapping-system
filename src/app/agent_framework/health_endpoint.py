"""
FastAPI /health endpoint that aggregates agent health from the Orchestrator.

This module exposes a single router that can be mounted on the existing
FastAPI app alongside the brownfield /health endpoint.  Once all agents
are migrated, the brownfield endpoint can be removed.

Usage (in src/app/main.py):
    from app.agent_framework.health_endpoint import create_health_router
    app.include_router(
        create_health_router(orchestrator),
        prefix="/agent-health",
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from .orchestrator import Orchestrator


def create_health_router(orchestrator: "Orchestrator") -> APIRouter:
    """
    Return a FastAPI router with /health and /dead-letter endpoints.

    Parameters
    ----------
    orchestrator:
        The running Orchestrator instance.  Passed via closure so the
        router has access without module-level globals.
    """
    router = APIRouter(tags=["agent-health"])

    @router.get(
        "/health",
        summary="Aggregate agent health",
        response_description=(
            "ok=all agents healthy, degraded=one+ degraded, "
            "unavailable=one+ down"
        ),
    )
    async def health() -> JSONResponse:
        """
        Returns aggregate health of all running agents.

        HTTP status codes:
          200  status=ok
          200  status=degraded   (system is functional but impaired)
          503  status=unavailable
        """
        result = await orchestrator.get_health()

        # Add dead-letter summary to health response
        dlq = orchestrator.dead_letter_store
        result["dead_letter"] = {
            "count": dlq.count(),
        }

        status_code = 503 if result["status"] == "unavailable" else 200
        return JSONResponse(content=result, status_code=status_code)

    @router.get(
        "/dead-letter",
        summary="Inspect dead-letter queue",
    )
    async def dead_letter(limit: int = 50) -> JSONResponse:
        """Return recent dead-letter entries for debugging."""
        dlq = orchestrator.dead_letter_store
        return JSONResponse(content={
            "total": dlq.count(),
            "entries": dlq.list_entries(limit=limit),
        })

    return router
