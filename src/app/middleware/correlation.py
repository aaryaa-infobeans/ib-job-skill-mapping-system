"""Middleware for correlation ID tracking and request logging."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import set_correlation_id

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation_id to requests and log API calls."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add correlation_id.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            The response with correlation_id header
        """
        # Extract or generate correlation_id
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Set correlation_id in context for logging
        set_correlation_id(correlation_id)

        # Log incoming request
        start_time = time.time()
        logger.info(
            "Incoming request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as exc:
            # Log exception
            status_code = 500
            error = str(exc)
            logger.error(
                "Request failed with exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "exception": error,
                },
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Record metrics (import here to avoid circular dependency)
        try:
            from app.api.routers.metrics import (
                http_requests_total,
                http_request_duration_seconds,
            )
            
            # Record request count
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code,
            ).inc()
            
            # Record request duration
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration_ms / 1000.0)
        except ImportError:
            # Metrics not available yet during initialization
            pass

        # Log response
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # Add correlation_id to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response

