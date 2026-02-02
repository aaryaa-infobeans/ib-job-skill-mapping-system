"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routers import health, jd_skill_mapping, matches, skill_availability
from app.settings import settings

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(
    skill_availability.router, prefix=settings.api_v1_prefix, tags=["skill-availability"]
)
app.include_router(
    jd_skill_mapping.router, prefix=settings.api_v1_prefix, tags=["jd-skill-mapping"]
)
app.include_router(matches.router, prefix=settings.api_v1_prefix, tags=["matches"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "IB Job Skill Mapping System", "version": "0.1.0"}
