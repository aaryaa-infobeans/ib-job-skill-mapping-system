"""
Extended LangGraph State with Token Tracking

Adds token and cost tracking fields to the workflow state so they persist
across checkpoints and can be displayed at each step.

Usage:
    state = AgentState(
        requisition_id="req-12345",
        correlation_id="corr-xyz",
        ...
    )
    
    # In each node:
    state.token_tracker.record_tokens(
        segment="jd_parsing",
        prompt_tokens=150,
        completion_tokens=220,
        model="gpt-4"
    )
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.app.services.token_tracking import TokenTracker


@dataclass
class TokenMetadata:
    """Token and cost metadata for a checkpoint."""
    segment: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    call_count: int = 0
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "segment": self.segment,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "call_count": self.call_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class ExtendedAgentState:
    """
    Extended workflow state with token tracking.
    
    Inherits from base AgentState and adds:
    - token_tracker: TokenTracker instance
    - token_checkpoints: List of token metadata per checkpoint
    - cumulative_cost: Running total cost
    - cumulative_tokens: Running total tokens
    """
    
    # Requisition data
    requisition_id: str
    correlation_id: str
    parsed_jd: Optional[Dict] = None
    normalized_skills: Optional[Dict] = None
    candidate_matches: Optional[List] = None
    scored_candidates: Optional[List] = None
    ranked_candidates: Optional[List] = None
    explanations: Optional[List] = None
    
    # Workflow status
    status: str = "pending"
    current_checkpoint: str = ""
    error: Optional[str] = None
    
    # Token and cost tracking
    token_tracker: Optional[TokenTracker] = None
    token_checkpoints: List[TokenMetadata] = field(default_factory=list)
    cumulative_tokens: int = 0
    cumulative_cost_usd: float = 0.0
    
    # Metadata
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize token tracker if not provided."""
        if self.token_tracker is None:
            self.token_tracker = TokenTracker(request_id=self.requisition_id)
        
        if self.started_at is None:
            self.started_at = datetime.now()
        
        self.updated_at = datetime.now()
    
    def enter_checkpoint(self, checkpoint_name: str) -> None:
        """
        Mark entry into a checkpoint.
        
        Args:
            checkpoint_name: Name of the checkpoint
        """
        self.current_checkpoint = checkpoint_name
        self.status = f"processing_{checkpoint_name}"
        self.updated_at = datetime.now()
        
        if self.token_tracker:
            self.token_tracker.start_segment(checkpoint_name)
    
    def exit_checkpoint(self, checkpoint_name: str) -> None:
        """
        Mark exit from a checkpoint and update cumulative metrics.
        
        Args:
            checkpoint_name: Name of the checkpoint
        """
        if self.token_tracker:
            self.token_tracker.end_segment(checkpoint_name)
            
            # Get checkpoint summary
            summary = self.token_tracker.get_checkpoint_summary(checkpoint_name)
            if summary:
                # Create metadata record
                metadata = TokenMetadata(
                    segment=checkpoint_name,
                    prompt_tokens=summary["prompt_tokens"],
                    completion_tokens=summary["completion_tokens"],
                    total_tokens=summary["total_tokens"],
                    cost_usd=summary["cost_usd"],
                    call_count=summary["call_count"],
                    timestamp=datetime.now()
                )
                self.token_checkpoints.append(metadata)
                
                # Update cumulative
                self.cumulative_tokens = self.token_tracker.summary.total_tokens
                self.cumulative_cost_usd = self.token_tracker.summary.total_cost_usd
        
        self.status = f"completed_{checkpoint_name}"
        self.updated_at = datetime.now()
    
    def record_tokens(
        self,
        segment: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4"
    ) -> None:
        """
        Record token usage in the workflow.
        
        Args:
            segment: Checkpoint name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name
        """
        if self.token_tracker:
            self.token_tracker.record_tokens(
                segment=segment,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=model
            )
            
            # Update cumulative
            self.cumulative_tokens = self.token_tracker.summary.total_tokens
            self.cumulative_cost_usd = self.token_tracker.summary.total_cost_usd
        
        self.updated_at = datetime.now()
    
    def mark_complete(self) -> None:
        """Mark the workflow as completed."""
        self.status = "completed"
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        
        if self.token_tracker:
            self.token_tracker.finalize()
    
    def mark_error(self, error_message: str) -> None:
        """
        Mark the workflow with an error.
        
        Args:
            error_message: Description of the error
        """
        self.status = "error"
        self.error = error_message
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def get_checkpoint_summary(self, checkpoint_name: str) -> Optional[Dict]:
        """
        Get token summary for a specific checkpoint.
        
        Args:
            checkpoint_name: Name of the checkpoint
            
        Returns:
            Dictionary with token and cost info, or None
        """
        if self.token_tracker:
            return self.token_tracker.get_checkpoint_summary(checkpoint_name)
        return None
    
    def get_all_checkpoints_summary(self) -> Dict[str, Dict]:
        """
        Get token summaries for all checkpoints.
        
        Returns:
            Dictionary mapping checkpoint names to summaries
        """
        if self.token_tracker:
            return self.token_tracker.get_all_checkpoints()
        return {}
    
    def get_request_summary(self) -> Dict:
        """
        Get overall request summary with all token/cost data.
        
        Returns:
            Dictionary with request-level metrics
        """
        if self.token_tracker:
            return self.token_tracker.get_request_summary()
        
        return {
            "requisition_id": self.requisition_id,
            "correlation_id": self.correlation_id,
            "total_tokens": self.cumulative_tokens,
            "total_cost_usd": self.cumulative_cost_usd,
            "checkpoints": {m.segment: m.to_dict() for m in self.token_checkpoints}
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "requisition_id": self.requisition_id,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "current_checkpoint": self.current_checkpoint,
            "cumulative_tokens": self.cumulative_tokens,
            "cumulative_cost_usd": round(self.cumulative_cost_usd, 6),
            "token_checkpoints": [m.to_dict() for m in self.token_checkpoints],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(
                (self.completed_at or datetime.now() - self.started_at).total_seconds(), 2
            ) if self.started_at else None,
            "error": self.error
        }
    
    def log_checkpoint_entry(self, logger) -> None:
        """
        Log checkpoint entry with current metrics.
        
        Args:
            logger: Logger instance
        """
        logger.info(
            f"Entering checkpoint: {self.current_checkpoint} | "
            f"Cumulative Tokens: {self.cumulative_tokens} | "
            f"Cumulative Cost: ${self.cumulative_cost_usd:.6f}"
        )
    
    def log_checkpoint_exit(self, logger) -> None:
        """
        Log checkpoint exit with updated metrics.
        
        Args:
            logger: Logger instance
        """
        checkpoint_summary = self.get_checkpoint_summary(self.current_checkpoint)
        if checkpoint_summary:
            logger.info(
                f"Exiting checkpoint: {self.current_checkpoint} | "
                f"Checkpoint Tokens: {checkpoint_summary['total_tokens']} | "
                f"Checkpoint Cost: ${checkpoint_summary['cost_usd']:.6f} | "
                f"Total Cumulative Tokens: {self.cumulative_tokens} | "
                f"Total Cost: ${self.cumulative_cost_usd:.6f}"
            )
    
    def log_final_summary(self, logger) -> None:
        """
        Log final request summary.
        
        Args:
            logger: Logger instance
        """
        logger.info("=" * 80)
        logger.info("REQUEST COMPLETION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Requisition ID: {self.requisition_id}")
        logger.info(f"Correlation ID: {self.correlation_id}")
        logger.info(f"Status: {self.status}")
        logger.info(f"Total Duration: {round((self.completed_at - self.started_at).total_seconds(), 2)}s")
        logger.info("-" * 80)
        logger.info(f"Total Tokens Used: {self.cumulative_tokens}")
        logger.info(f"Total Cost: ${self.cumulative_cost_usd:.6f}")
        logger.info("-" * 80)
        
        if self.token_checkpoints:
            logger.info("CHECKPOINT BREAKDOWN:")
            for checkpoint in self.token_checkpoints:
                logger.info(f"\n  {checkpoint.segment}:")
                logger.info(f"    - Prompt Tokens: {checkpoint.prompt_tokens}")
                logger.info(f"    - Completion Tokens: {checkpoint.completion_tokens}")
                logger.info(f"    - Total Tokens: {checkpoint.total_tokens}")
                logger.info(f"    - LLM Calls: {checkpoint.call_count}")
                logger.info(f"    - Cost: ${checkpoint.cost_usd:.6f}")
        
        logger.info("=" * 80)


# Example usage
if __name__ == "__main__":
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create state
    state = ExtendedAgentState(
        requisition_id="req-12345",
        correlation_id="corr-xyz-789"
    )
    
    # Simulate workflow
    checkpoints = [
        "jd_parsing",
        "skill_normalization",
        "matching_scoring",
        "explanation_generation",
        "result_aggregation"
    ]
    
    for checkpoint in checkpoints:
        state.enter_checkpoint(checkpoint)
        state.log_checkpoint_entry(logger)
        
        # Simulate token usage
        state.record_tokens(
            segment=checkpoint,
            prompt_tokens=150,
            completion_tokens=220,
            model="gpt-4"
        )
        
        state.exit_checkpoint(checkpoint)
        state.log_checkpoint_exit(logger)
    
    # Mark complete
    state.mark_complete()
    state.log_final_summary(logger)
    
    # Print JSON summary
    print("\nJSON Summary:")
    import json
    print(json.dumps(state.get_request_summary(), indent=2, default=str))
