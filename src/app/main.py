"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routers import health

app = FastAPI(
    title="IB Job Skill Mapping System",
    version="0.1.0",
)

# Include routers
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "IB Job Skill Mapping System"}
