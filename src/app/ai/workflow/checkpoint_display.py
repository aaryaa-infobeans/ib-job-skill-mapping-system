"""
LangGraph Checkpoint Display Utility

Formats and displays checkpoint information with token and cost metrics
in a human-readable format for logging and debugging.

Usage:
    display = CheckpointDisplay(state)
    
    # Display all checkpoints
    display.print_all_checkpoints()
    
    # Display single checkpoint
    display.print_checkpoint("jd_parsing")
    
    # Get formatted output
    output = display.format_checkpoints()
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from tabulate import tabulate

from src.app.ai.workflow.extended_state import ExtendedAgentState


class CheckpointDisplay:
    """
    Format and display LangGraph checkpoint information with token/cost metrics.
    """
    
    def __init__(self, state: ExtendedAgentState, logger: Optional[logging.Logger] = None):
        """
        Initialize checkpoint display.
        
        Args:
            state: ExtendedAgentState with checkpoint data
            logger: Optional logger instance
        """
        self.state = state
        self.logger = logger or logging.getLogger(__name__)
    
    def print_all_checkpoints(self) -> None:
        """Print all checkpoints with their token and cost metrics."""
        output = self.format_checkpoints()
        print(output)
        self.logger.info(output)
    
    def print_checkpoint(self, checkpoint_name: str) -> None:
        """
        Print a specific checkpoint.
        
        Args:
            checkpoint_name: Name of the checkpoint
        """
        summary = self.state.get_checkpoint_summary(checkpoint_name)
        if not summary:
            print(f"Checkpoint '{checkpoint_name}' not found")
            return
        
        output = self._format_single_checkpoint(checkpoint_name, summary)
        print(output)
        self.logger.info(output)
    
    def format_checkpoints(self) -> str:
        """
        Format all checkpoint information.
        
        Returns:
            Formatted string representation
        """
        lines = []
        
        # Header
        lines.append("=" * 100)
        lines.append("LangGraph Checkpoints: Token & Cost Tracking".center(100))
        lines.append("=" * 100)
        
        # Requisition info
        lines.append(f"\nRequisition ID: {self.state.requisition_id}")
        lines.append(f"Correlation ID: {self.state.correlation_id}")
        lines.append(f"Status: {self.state.status}")
        
        # Checkpoint table
        if self.state.token_checkpoints:
            lines.append("\n" + "-" * 100)
            lines.append("CHECKPOINT DETAILS")
            lines.append("-" * 100)
            
            table_data = []
            for i, checkpoint in enumerate(self.state.token_checkpoints, 1):
                table_data.append([
                    i,
                    checkpoint.segment,
                    checkpoint.prompt_tokens,
                    checkpoint.completion_tokens,
                    checkpoint.total_tokens,
                    checkpoint.call_count,
                    f"${checkpoint.cost_usd:.6f}"
                ])
            
            headers = [
                "#",
                "Checkpoint",
                "Prompt Tokens",
                "Completion Tokens",
                "Total Tokens",
                "LLM Calls",
                "Cost USD"
            ]
            
            lines.append(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Summary
        lines.append("\n" + "-" * 100)
        lines.append("CUMULATIVE TOTALS")
        lines.append("-" * 100)
        lines.append(f"Total Tokens: {self.state.cumulative_tokens}")
        lines.append(f"Total Cost: ${self.state.cumulative_cost_usd:.6f}")
        
        if self.state.started_at and self.state.completed_at:
            duration = (self.state.completed_at - self.state.started_at).total_seconds()
            lines.append(f"Duration: {duration:.2f}s")
            if self.state.cumulative_tokens > 0:
                tokens_per_second = self.state.cumulative_tokens / duration
                lines.append(f"Throughput: {tokens_per_second:.2f} tokens/second")
        
        lines.append("=" * 100)
        
        return "\n".join(lines)
    
    def _format_single_checkpoint(self, name: str, summary: Dict) -> str:
        """
        Format a single checkpoint.
        
        Args:
            name: Checkpoint name
            summary: Checkpoint summary dictionary
            
        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"\nCheckpoint: {name}")
        lines.append("-" * 50)
        lines.append(f"  Prompt Tokens:     {summary['prompt_tokens']:>10}")
        lines.append(f"  Completion Tokens: {summary['completion_tokens']:>10}")
        lines.append(f"  Total Tokens:      {summary['total_tokens']:>10}")
        lines.append(f"  LLM Calls:         {summary['call_count']:>10}")
        lines.append(f"  Cost USD:          ${summary['cost_usd']:>9.6f}")
        lines.append(f"  Models Used:       {str(summary['models_used']):>}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """
        Convert checkpoints to dictionary format.
        
        Returns:
            Dictionary representation
        """
        return {
            "requisition_id": self.state.requisition_id,
            "correlation_id": self.state.correlation_id,
            "status": self.state.status,
            "total_tokens": self.state.cumulative_tokens,
            "total_cost_usd": self.state.cumulative_cost_usd,
            "checkpoints": [
                {
                    "node": cp.segment,
                    "state_keys": self._get_state_keys_for_checkpoint(cp.segment),
                    "prompt_tokens": cp.prompt_tokens,
                    "completion_tokens": cp.completion_tokens,
                    "total_tokens": cp.total_tokens,
                    "llm_calls": cp.call_count,
                    "cost_usd": round(cp.cost_usd, 6),
                    "timestamp": cp.timestamp.isoformat() if cp.timestamp else None
                }
                for cp in self.state.token_checkpoints
            ]
        }
    
    def _get_state_keys_for_checkpoint(self, checkpoint_name: str) -> List[str]:
        """
        Get relevant state keys for a checkpoint.
        
        Args:
            checkpoint_name: Name of the checkpoint
            
        Returns:
            List of state keys used at this checkpoint
        """
        # Map checkpoint names to relevant state keys
        checkpoint_keys = {
            "jd_parsing": ["parsed_jd", "correlation_id"],
            "skill_normalization": ["normalized_skills", "correlation_id"],
            "matching_scoring": ["scored_candidates", "correlation_id", "candidate_count"],
            "explanation_generation": ["explanations", "correlation_id", "candidate_count"],
            "result_aggregation": ["ranked_candidates", "status", "result_count", "correlation_id"]
        }
        
        return checkpoint_keys.get(checkpoint_name, ["correlation_id"])


def display_checkpoints(state: ExtendedAgentState, logger: Optional[logging.Logger] = None) -> str:
    """
    Convenience function to display checkpoints.
    
    Args:
        state: ExtendedAgentState with checkpoint data
        logger: Optional logger instance
        
    Returns:
        Formatted string
    """
    display = CheckpointDisplay(state, logger)
    return display.format_checkpoints()


# Example usage and testing
if __name__ == "__main__":
    import logging
    from src.app.ai.workflow.extended_state import ExtendedAgentState, TokenMetadata
    from datetime import datetime, timedelta
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create mock state with checkpoints
    state = ExtendedAgentState(
        requisition_id="req-12345",
        correlation_id="corr-xyz-789"
    )
    
    # Simulate checkpoint data
    checkpoints_data = [
        {
            "segment": "jd_parsing",
            "prompt_tokens": 150,
            "completion_tokens": 220,
            "cost_usd": 0.00156,
            "call_count": 1
        },
        {
            "segment": "skill_normalization",
            "prompt_tokens": 200,
            "completion_tokens": 300,
            "cost_usd": 0.00240,
            "call_count": 2
        },
        {
            "segment": "matching_scoring",
            "prompt_tokens": 500,
            "completion_tokens": 1500,
            "cost_usd": 0.01380,
            "call_count": 50
        },
        {
            "segment": "explanation_generation",
            "prompt_tokens": 300,
            "completion_tokens": 800,
            "cost_usd": 0.00720,
            "call_count": 10
        },
        {
            "segment": "result_aggregation",
            "prompt_tokens": 100,
            "completion_tokens": 150,
            "cost_usd": 0.00108,
            "call_count": 1
        }
    ]
    
    # Add checkpoints to state
    for data in checkpoints_data:
        metadata = TokenMetadata(
            segment=data["segment"],
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            total_tokens=data["prompt_tokens"] + data["completion_tokens"],
            cost_usd=data["cost_usd"],
            call_count=data["call_count"],
            timestamp=datetime.now()
        )
        state.token_checkpoints.append(metadata)
    
    # Update cumulative
    state.cumulative_tokens = sum(cp.total_tokens for cp in state.token_checkpoints)
    state.cumulative_cost_usd = sum(cp.cost_usd for cp in state.token_checkpoints)
    state.completed_at = datetime.now()
    
    # Display
    display = CheckpointDisplay(state, logger)
    
    print("\n" + "=" * 100)
    print("CHECKPOINT DISPLAY TEST")
    print("=" * 100)
    
    display.print_all_checkpoints()
    
    print("\n" + "=" * 100)
    print("DICTIONARY REPRESENTATION")
    print("=" * 100)
    
    import json
    print(json.dumps(display.to_dict(), indent=2, default=str))
