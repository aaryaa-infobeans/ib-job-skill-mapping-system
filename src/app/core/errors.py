"""Error handling."""
from fastapi import HTTPException


class ApplicationError(Exception):
    """Base application error."""

    pass


class NotFoundError(ApplicationError):
    """Resource not found error."""

    pass
