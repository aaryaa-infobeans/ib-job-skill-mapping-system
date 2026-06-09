"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from app.api.routers import health, jd_skill_mapping, matches, metrics, candidate_availability, feedback
from app.logging_config import configure_logging
from app.middleware import CorrelationIdMiddleware
from app.middleware.auth import OAuth2Middleware
from app.settings import settings
from app.db.session import SessionLocal
from app.db.repositories.skill_config import load_skill_config

# Configure structured JSON logging
configure_logging(log_level=settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        load_skill_config(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    lifespan=lifespan,
)

# Add OAuth2 authentication middleware (validates JWT tokens)
app.add_middleware(
    OAuth2Middleware,
    secret_key=settings.get_jwt_secret_key(),
    algorithm=settings.jwt_algorithm,
)

# Add middleware for correlation ID tracking
app.add_middleware(CorrelationIdMiddleware)

logger.info("Application starting", extra={
    "project": settings.project_name,
    "jwt_validation": "enabled" if settings.get_jwt_secret_key() else "dev mode (no signature validation)"
})

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router, prefix=settings.api_v1_prefix, tags=["metrics"])
app.include_router(
    candidate_availability.router, prefix=settings.api_v1_prefix, tags=["candidate-availability"]
)
app.include_router(
    jd_skill_mapping.router, prefix=settings.api_v1_prefix, tags=["jd-skill-mapping"]
)
app.include_router(matches.router, prefix=settings.api_v1_prefix, tags=["matches"])
app.include_router(feedback.router, prefix=settings.api_v1_prefix, tags=["feedback"])


@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint accessed")
    return {"message": "IB Job Skill Mapping System", "version": "0.1.0"}


