"""Audit trail utilities for LangGraph execution."""

import logging
import json
from datetime import datetime, date
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.db.models.models import LangGraphCheckpoint, LLMRequestLog

logger = logging.getLogger(__name__)


def convert_dates_to_iso(obj: Any) -> Any:
    """Recursively convert date and datetime objects to ISO format strings.
    
    Args:
        obj: Object to convert (dict, list, date, datetime, or other)
        
    Returns:
        Object with all dates converted to ISO strings
    """
    if isinstance(obj, dict):
        return {k: convert_dates_to_iso(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_dates_to_iso(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    else:
        return obj


def save_checkpoint(
    db: Session,
    request_id: str,
    node_name: str,
    state: Dict[str, Any],
    token_count: Optional[int] = None,
) -> None:
    """Save a LangGraph checkpoint to the database for audit trail.
    
    Args:
        db: Database session
        request_id: The originating request ID
        node_name: Name of the graph node that was executed
        state: The graph state after node execution
        token_count: Number of LLM tokens consumed (if applicable)
    """
    try:
        # Convert any date/datetime objects to ISO strings for JSON serialization
        serializable_state = convert_dates_to_iso(state)
        
        checkpoint = LangGraphCheckpoint(
            request_id=request_id,
            node_name=node_name,
            state_json=serializable_state,
            token_count=token_count,
            created_at=datetime.utcnow(),
        )
        db.add(checkpoint)
        db.commit()
        
        logger.info(
            "Saved checkpoint",
            extra={
                "request_id": request_id,
                "node_name": node_name,
                "token_count": token_count,
            },
        )
    except Exception as exc:
        logger.error(
            "Failed to save checkpoint",
            extra={
                "request_id": request_id,
                "node_name": node_name,
                "error": str(exc),
            },
            exc_info=True,
        )
        db.rollback()
        # Don't raise - audit failure shouldn't stop the workflow


def get_checkpoints_for_request(
    db: Session, request_id: str
) -> list[LangGraphCheckpoint]:
    """Retrieve all checkpoints for a request.
    
    Args:
        db: Database session
        request_id: The request ID to query
        
    Returns:
        List of checkpoint records ordered by creation time
    """
    return (
        db.query(LangGraphCheckpoint)
        .filter(LangGraphCheckpoint.request_id == request_id)
        .order_by(LangGraphCheckpoint.created_at)
        .all()
    )


def calculate_total_tokens(db: Session, request_id: str) -> int:
    """Calculate total token usage for a request.
    
    Args:
        db: Database session
        request_id: The request ID to query
        
    Returns:
        Total token count across all checkpoints
    """
    checkpoints = get_checkpoints_for_request(db, request_id)
    return sum(cp.token_count or 0 for cp in checkpoints)


def save_llm_request_log(
    db: Session,
    request_id: str,
    agent_name: str,
    prompt_name: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
) -> None:
    """Log an LLM request to the database for auditing and cost tracking.
    
    Args:
        db: Database session
        request_id: The originating request ID
        agent_name: Name of the agent making the request
        prompt_name: Name/type of the prompt being used
        model: LLM model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        cost_usd: Computed cost in USD
    """
    try:
        log_entry = LLMRequestLog(
            request_id=request_id,
            agent_name=agent_name,
            prompt_name=prompt_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(
            "Logged LLM request",
            extra={
                "request_id": request_id,
                "agent_name": agent_name,
                "model": model,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost_usd": cost_usd,
            },
        )
    except Exception as exc:
        logger.error(
            "Failed to log LLM request",
            extra={
                "request_id": request_id,
                "agent_name": agent_name,
                "error": str(exc),
            },
            exc_info=True,
        )
        db.rollback()
