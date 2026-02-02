"""Prometheus metrics endpoint."""

import logging
from typing import Dict

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Create a custom registry for application metrics
registry = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    registry=registry,
)

# AI Agent metrics
ai_agent_executions_total = Counter(
    "ai_agent_executions_total",
    "Total AI agent executions",
    ["agent_name", "status"],
    registry=registry,
)

ai_agent_duration_seconds = Histogram(
    "ai_agent_duration_seconds",
    "AI agent execution time in seconds",
    ["agent_name"],
    registry=registry,
)

# LLM metrics
llm_token_usage_total = Counter(
    "llm_token_usage_total",
    "Total LLM tokens used",
    ["model", "token_type"],
    registry=registry,
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    registry=registry,
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=registry,
)

# Graph execution metrics
graph_executions_total = Counter(
    "graph_executions_total",
    "Total LangGraph executions",
    ["status"],
    registry=registry,
)

graph_execution_duration_seconds = Histogram(
    "graph_execution_duration_seconds",
    "LangGraph execution time in seconds",
    registry=registry,
)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus-formatted metrics
    """
    logger.debug("Metrics endpoint accessed")
    metrics_output = generate_latest(registry)
    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


def get_metrics_registry() -> CollectorRegistry:
    """Get the metrics registry for external use.
    
    Returns:
        The Prometheus collector registry
    """
    return registry
