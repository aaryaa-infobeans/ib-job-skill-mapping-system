"""Middleware package."""

from app.middleware.correlation import CorrelationIdMiddleware

__all__ = ["CorrelationIdMiddleware"]
