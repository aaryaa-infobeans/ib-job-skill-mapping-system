"""Base Agent class and common patterns for multi-agent architecture."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import uuid
from functools import wraps
import time


@dataclass
class ExecutionContext:
    """Context for agent execution."""
    request_id: str
    agent_name: str
    start_time: float
    input_data: Any
    
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return (time.time() - self.start_time) * 1000


class BaseAgent(ABC):
    """Abstract base class for all agents in the requisition skill matching system."""
    
    def __init__(self, agent_name: str, logger: Optional[logging.Logger] = None):
        self.agent_name = agent_name
        self.logger = logger or logging.getLogger(self.agent_name)
        self.execution_contexts: Dict[str, ExecutionContext] = {}
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute agent logic. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data before processing."""
        pass
    
    @abstractmethod
    def format_output(self, result: Any) -> Any:
        """Format output to expected structure."""
        pass
    
    def _execute_with_context(self, input_data: Any) -> Any:
        """Execute with context tracking."""
        request_id = str(uuid.uuid4())
        context = ExecutionContext(
            request_id=request_id,
            agent_name=self.agent_name,
            start_time=time.time(),
            input_data=input_data
        )
        self.execution_contexts[request_id] = context
        
        try:
            # Validate input
            if not self.validate_input(input_data):
                self.logger.warning(
                    f"Agent {self.agent_name}: Input validation failed",
                    extra={"request_id": request_id}
                )
                return None
            
            # Execute
            result = self.execute(input_data)
            
            # Log success
            self.logger.info(
                f"Agent {self.agent_name}: Execution successful",
                extra={
                    "request_id": request_id,
                    "duration_ms": context.elapsed_ms()
                }
            )
            
            return self.format_output(result)
            
        except Exception as e:
            self.logger.error(
                f"Agent {self.agent_name}: Execution failed - {str(e)}",
                extra={
                    "request_id": request_id,
                    "duration_ms": context.elapsed_ms(),
                    "error": str(e)
                },
                exc_info=True
            )
            raise
