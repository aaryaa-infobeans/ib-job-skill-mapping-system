"""
LLM Token Tracking System for LangGraph Workflow

Tracks input/output tokens and costs at each checkpoint in the matching workflow.
Provides token accounting, cost aggregation, and observability across all LLM calls.

Usage:
    tracker = TokenTracker(openai_config)
    tracker.start_segment("jd_parsing")
    
    # Make LLM call
    response = llm_client.chat.completions.create(...)
    
    tracker.record_tokens(
        segment="jd_parsing",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        model=response.model
    )
    
    checkpoint = tracker.get_checkpoint_summary("jd_parsing")
    # Returns: {
    #     "segment": "jd_parsing",
    #     "prompt_tokens": 150,
    #     "completion_tokens": 220,
    #     "total_tokens": 370,
    #     "cost_usd": 0.00156
    # }
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
from enum import Enum


class ModelType(Enum):
    """Supported LLM models and their pricing."""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"


# Pricing rates (per 1M tokens) - Updated for Feb 2024
PRICING_RATES = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "text-embedding-3-large": {"input": 0.02, "output": 0.0},  # Output free for embeddings
}


@dataclass
class TokenRecord:
    """Record of a single LLM token usage."""
    segment: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "segment": self.segment,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CheckpointSummary:
    """Summary of tokens and cost for a single checkpoint."""
    segment: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    call_count: int = 0
    models_used: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "segment": self.segment,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "call_count": self.call_count,
            "models_used": self.models_used
        }


@dataclass
class RequestSummary:
    """Total summary for entire request/requisition."""
    request_id: str
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    segment_count: int = 0
    checkpoints: Dict[str, CheckpointSummary] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def duration_seconds(self) -> float:
        """Get request duration in seconds."""
        if self.end_time is None:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "segment_count": self.segment_count,
            "duration_seconds": round(self.duration_seconds(), 2),
            "cost_per_token": round(
                self.total_cost_usd / self.total_tokens if self.total_tokens > 0 else 0,
                8
            ),
            "checkpoints": {k: v.to_dict() for k, v in self.checkpoints.items()}
        }


class TokenTracker:
    """
    Track LLM tokens and costs across LangGraph workflow checkpoints.
    
    Features:
    - Per-checkpoint token accounting
    - Real-time cost calculation
    - Model pricing lookup
    - Segment-based tracking
    - Request-wide aggregation
    """
    
    def __init__(self, request_id: str, logger: Optional[logging.Logger] = None):
        """
        Initialize TokenTracker.
        
        Args:
            request_id: Unique identifier for the request
            logger: Optional logger instance
        """
        self.request_id = request_id
        self.logger = logger or logging.getLogger(__name__)
        
        # Storage
        self.token_records: List[TokenRecord] = []
        self.checkpoints: Dict[str, CheckpointSummary] = {}
        self.active_segments: set = set()
        
        # Summary
        self.summary = RequestSummary(request_id=request_id)
        
        self.logger.info(f"TokenTracker initialized for request: {request_id}")
    
    def start_segment(self, segment_name: str) -> None:
        """
        Mark the start of a segment/checkpoint.
        
        Args:
            segment_name: Name of the segment (e.g., 'jd_parsing')
        """
        if segment_name not in self.checkpoints:
            self.checkpoints[segment_name] = CheckpointSummary(segment=segment_name)
        
        self.active_segments.add(segment_name)
        self.logger.debug(f"Started segment: {segment_name}")
    
    def end_segment(self, segment_name: str) -> None:
        """
        Mark the end of a segment/checkpoint.
        
        Args:
            segment_name: Name of the segment
        """
        self.active_segments.discard(segment_name)
        self.logger.debug(f"Ended segment: {segment_name}")
    
    def record_tokens(
        self,
        segment: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4"
    ) -> TokenRecord:
        """
        Record token usage for an LLM call.
        
        Args:
            segment: Checkpoint/segment name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name for pricing lookup
            
        Returns:
            TokenRecord with computed cost
        """
        # Ensure segment exists
        if segment not in self.checkpoints:
            self.start_segment(segment)
        
        # Calculate cost
        cost = self._calculate_cost(prompt_tokens, completion_tokens, model)
        total_tokens = prompt_tokens + completion_tokens
        
        # Create record
        record = TokenRecord(
            segment=segment,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost
        )
        
        # Store record
        self.token_records.append(record)
        
        # Update checkpoint summary
        checkpoint = self.checkpoints[segment]
        checkpoint.prompt_tokens += prompt_tokens
        checkpoint.completion_tokens += completion_tokens
        checkpoint.total_tokens += total_tokens
        checkpoint.cost_usd += cost
        checkpoint.call_count += 1
        
        # Track models used
        if model not in checkpoint.models_used:
            checkpoint.models_used[model] = 0
        checkpoint.models_used[model] += 1
        
        # Update request summary
        self._update_request_summary()
        
        self.logger.info(
            f"Recorded tokens for {segment}: "
            f"prompt={prompt_tokens}, completion={completion_tokens}, cost=${cost:.6f}"
        )
        
        return record
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """
        Calculate cost for LLM call.
        
        Args:
            prompt_tokens: Prompt token count
            completion_tokens: Completion token count
            model: Model name
            
        Returns:
            Cost in USD
        """
        # Get pricing rates
        rates = PRICING_RATES.get(model, PRICING_RATES.get("gpt-4"))
        
        # Calculate cost (rates are per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * rates["input"]
        output_cost = (completion_tokens / 1_000_000) * rates["output"]
        
        return input_cost + output_cost
    
    def _update_request_summary(self) -> None:
        """Update the overall request summary."""
        total_prompt = sum(r.prompt_tokens for r in self.token_records)
        total_completion = sum(r.completion_tokens for r in self.token_records)
        total_cost = sum(r.cost_usd for r in self.token_records)
        
        self.summary.total_prompt_tokens = total_prompt
        self.summary.total_completion_tokens = total_completion
        self.summary.total_tokens = total_prompt + total_completion
        self.summary.total_cost_usd = total_cost
        self.summary.segment_count = len(self.checkpoints)
        self.summary.checkpoints = self.checkpoints
    
    def get_checkpoint_summary(self, segment: str) -> Optional[Dict]:
        """
        Get summary for a specific checkpoint.
        
        Args:
            segment: Checkpoint name
            
        Returns:
            Dictionary with token and cost summary, or None if not found
        """
        if segment not in self.checkpoints:
            self.logger.warning(f"Segment '{segment}' not found")
            return None
        
        return self.checkpoints[segment].to_dict()
    
    def get_all_checkpoints(self) -> Dict[str, Dict]:
        """
        Get summaries for all checkpoints.
        
        Returns:
            Dictionary mapping segment names to summaries
        """
        return {k: v.to_dict() for k, v in self.checkpoints.items()}
    
    def get_request_summary(self) -> Dict:
        """
        Get overall summary for the request.
        
        Returns:
            Dictionary with total tokens, cost, and per-checkpoint breakdown
        """
        self.summary.end_time = datetime.now()
        return self.summary.to_dict()
    
    def finalize(self) -> RequestSummary:
        """
        Finalize tracking and return summary.
        
        Returns:
            RequestSummary with all accumulated data
        """
        self.summary.end_time = datetime.now()
        self._update_request_summary()
        
        self.logger.info(
            f"Request {self.request_id} completed: "
            f"{self.summary.total_tokens} tokens, "
            f"${self.summary.total_cost_usd:.6f} cost"
        )
        
        return self.summary
    
    def to_json(self) -> str:
        """
        Convert entire tracking data to JSON.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.get_request_summary(), indent=2, default=str)
    
    def log_summary(self) -> None:
        """Log the request summary."""
        summary = self.get_request_summary()
        
        self.logger.info("=" * 70)
        self.logger.info("LLM TOKEN & COST SUMMARY")
        self.logger.info("=" * 70)
        self.logger.info(f"Request ID: {summary['request_id']}")
        self.logger.info(f"Duration: {summary['duration_seconds']}s")
        self.logger.info(f"Total Tokens: {summary['total_tokens']}")
        self.logger.info(f"  - Prompt: {summary['total_prompt_tokens']}")
        self.logger.info(f"  - Completion: {summary['total_completion_tokens']}")
        self.logger.info(f"Total Cost: ${summary['total_cost_usd']:.6f}")
        self.logger.info(f"Cost per Token: ${summary['cost_per_token']:.8f}")
        self.logger.info("-" * 70)
        
        self.logger.info("CHECKPOINT BREAKDOWN:")
        for segment, checkpoint in summary["checkpoints"].items():
            self.logger.info(f"\n  {segment}:")
            self.logger.info(f"    Tokens: {checkpoint['total_tokens']} "
                           f"(prompt: {checkpoint['prompt_tokens']}, "
                           f"completion: {checkpoint['completion_tokens']})")
            self.logger.info(f"    Calls: {checkpoint['call_count']}")
            self.logger.info(f"    Cost: ${checkpoint['cost_usd']:.6f}")
            self.logger.info(f"    Models: {checkpoint['models_used']}")
        
        self.logger.info("=" * 70)


def create_token_tracker(request_id: str) -> TokenTracker:
    """
    Factory function to create a TokenTracker instance.
    
    Args:
        request_id: Unique request identifier
        
    Returns:
        Initialized TokenTracker
    """
    logger = logging.getLogger(__name__)
    return TokenTracker(request_id, logger)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create tracker
    tracker = TokenTracker("req-12345")
    
    # Simulate workflow
    segments = [
        "jd_parsing",
        "skill_normalization",
        "matching_scoring",
        "explanation_generation",
        "result_aggregation"
    ]
    
    for segment in segments:
        tracker.start_segment(segment)
        
        # Simulate multiple LLM calls per segment
        for i in range(2):
            prompt_tokens = 150 + (i * 50)
            completion_tokens = 200 + (i * 100)
            
            tracker.record_tokens(
                segment=segment,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model="gpt-4"
            )
        
        tracker.end_segment(segment)
    
    # Get results
    tracker.log_summary()
    
    print("\nJSON Summary:")
    print(tracker.to_json())
