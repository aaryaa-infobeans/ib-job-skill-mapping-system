"""Tracing and observability utilities for LangGraph."""

import functools
import logging
import time
from typing import Any, Dict, Callable

from trulens.core.session import TruSession
from trulens_eval.tru_custom_app import instrument

logger = logging.getLogger(__name__)

def trace_node(node_name: str):
    """
    Decorator to trace a LangGraph node execution.
    
    Captures:
    - Input state
    - Output state update
    - Latency
    - Success/Failure
    """
    def decorator(func: Callable):
        @instrument # TruLens instrumentation
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            start_time = time.time()
            
            # Log input (simplified for JSON structure)
            # We avoid logging the full state if it's too large, but capture key inputs
            input_preview = {k: v for k, v in state.items() if k not in ['candidate_scores', 'retrieved_candidates']}
            
            logger.info(
                f"Node '{node_name}' starting",
                extra={
                    "node": node_name,
                    "input_keys": list(state.keys()),
                    "request_id": state.get("requisition_input", {}).get("correlation_id", "unknown")
                }
            )
            
            try:
                # If we are within a TruLens recording context, ensure this is captured
                # Note: @instrument already handles basic capture if called within recorder context
                result = func(state, *args, **kwargs)
                
                latency = time.time() - start_time
                
                # Log output/update
                logger.info(
                    f"Node '{node_name}' completed in {latency:.4f}s",
                    extra={
                        "node": node_name,
                        "latency": latency,
                        "output_keys": list(result.keys()) if isinstance(result, dict) else "N/A"
                    }
                )
                
                # Add metadata to state if it's a dict
                if isinstance(result, dict):
                    if "node_metadata" not in result:
                        result["node_metadata"] = {}
                    
                    result["node_metadata"][node_name] = {
                        "latency": latency,
                        "timestamp": time.time(),
                        "status": "SUCCESS"
                    }
                
                return result
                
            except Exception as e:
                latency = time.time() - start_time
                logger.error(
                    f"Node '{node_name}' failed after {latency:.4f}s: {str(e)}",
                    exc_info=True,
                    extra={
                        "node": node_name,
                        "latency": latency,
                        "error": str(e)
                    }
                )
                
                # Ensure error is propagated or handled in state
                if isinstance(state, dict):
                    state["error_message"] = f"Error in {node_name}: {str(e)}"
                
                raise
                
        return wrapper
    return decorator
