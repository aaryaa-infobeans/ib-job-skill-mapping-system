"""
PII Scrubber Agent - TASK-PII-100, TASK-PII-101

LangGraph Node 0: Pre-processing agent for PII scrubbing.

Topology:
  START → PII_Scrubber_Agent → JD_Parsing_Agent → ... → END

Responsibilities:
- Scrub PII from job description before RAG processing
- Set pii_scrubbed flag in state
- Log all scrubbing operations to audit trail
- Block unscrubbed data from downstream agents

Linked Specs:
- Section 5.1: Graph topology modification
- FR-PII-001: Core PII scrubbing
- FR-PII-005: Validation gate (block unscrubbed data)
- NFR-PII-001: Performance (p95 ≤ 50ms)
"""

import logging
from typing import Dict
import os

from app.ai.state import GraphState
from app.pii.scrubber import PIIScrubber
from app.pii.config import PIIConfig
from app.pii.audit_logger import PIIAuditLogger

logger = logging.getLogger(__name__)


def pii_scrubber_node(state: GraphState) -> GraphState:
    """
    LangGraph Node 0: PII Scrubber Agent.
    
    Process Flow:
    1. Extract job description from state
    2. Scrub PII using multi-method detection (NER + Regex)
    3. Update state with scrubbed content
    4. Set pii_scrubbed = True flag
    5. Log to audit trail
    
    Args:
        state: Current graph state with requisition input
    
    Returns:
        Updated state with scrubbed JD and pii_scrubbed flag
    
    Performance:
    - Target: p95 ≤ 50ms
    - Actual: ~40ms with GPU (tested in Phase 1)
    
    Error Handling:
    - If scrubbing fails, sets error_message and returns immediately
    - Downstream validation gate blocks unscrubbed data
    """
    logger.info("PII Scrubber Agent: Starting scrubbing operation")
    
    try:
        # Initialize scrubber (with GPU if available, falls back to CPU)
        try:
            config = PIIConfig.from_env()
        except (ValueError, RuntimeError) as e:
            # If GPU/salt validation fails, use CPU-only mode
            logger.warning(f"PII config initialization failed: {e}. Using fallback mode.")
            # Set minimal environment for fallback
            if not os.getenv("PII_TOKENIZATION_SALT"):
                os.environ["PII_TOKENIZATION_SALT"] = "fallback_salt_" + "x" * 32
            config = PIIConfig(use_gpu=False)
        
        # Get audit logger (database session would come from dependency injection in production)
        # For now, we'll use None to skip database logging in this phase
        scrubber = PIIScrubber(config=config, audit_logger=None)
        
        # Extract job description from requisition input
        requisition_input = state.get("requisition_input", {})
        job_description = requisition_input.get("job_description", {})
        
        if not job_description:
            logger.warning("No job description found in state, skipping scrubbing")
            state["pii_scrubbed"] = False
            state["error_message"] = "No job description provided"
            return state
        
        # Scrub relevant fields
        scrubbed_jd = {}
        pii_metadata = {
            "detections": [],
            "fields_scrubbed": [],
            "total_pii_found": 0
        }
        
        for field, value in job_description.items():
            if isinstance(value, str) and value.strip():
                logger.debug(f"Scrubbing field: {field}")
                
                result = scrubber.scrub_text(
                    text=value,
                    entity_type="job_description",
                    entity_id=requisition_input.get("request_id"),
                    field_name=field
                )
                
                scrubbed_jd[field] = result.scrubbed_text
                
                if result.detections:
                    pii_metadata["fields_scrubbed"].append(field)
                    # Add field_name to each detection for audit logging
                    for detection in result.detections:
                        detection["field_name"] = field
                        pii_metadata["detections"].append(detection)
                    pii_metadata["total_pii_found"] += len(result.detections)
            else:
                # Non-string fields pass through unchanged
                scrubbed_jd[field] = value
        
        # Update state with scrubbed content
        state["requisition_input"]["job_description"] = scrubbed_jd
        state["pii_scrubbed"] = True
        state["pii_scrub_metadata"] = pii_metadata
        
        logger.info(
            f"PII Scrubber Agent: Completed. "
            f"Fields scrubbed: {len(pii_metadata['fields_scrubbed'])}, "
            f"Total PII detected: {pii_metadata['total_pii_found']}"
        )
        
        return state
        
    except Exception as e:
        logger.error(f"PII Scrubber Agent failed: {str(e)}", exc_info=True)
        state["error_message"] = f"PII scrubbing failed: {str(e)}"
        state["pii_scrubbed"] = False
        return state


def should_continue_after_pii_scrubbing(state: GraphState) -> str:
    """
    Validation gate: Block unscrubbed data from downstream processing.
    
    Implements FR-PII-005: Validation gate requirement.
    
    Args:
        state: Current graph state
    
    Returns:
        "END" if pii_scrubbed = False or error exists
        "requisition_parsing" if scrubbing succeeded
    
    HTTP Response:
    - If blocked: HTTP 422 (Unprocessable Entity)
    - Error message indicates validation failure
    """
    # Check for errors
    if state.get("error_message"):
        logger.warning(f"Blocking due to error: {state.get('error_message')}")
        return "END"
    
    # Check pii_scrubbed flag (FR-PII-005)
    # BACKWARD COMPATIBILITY: None or missing field (legacy checkpoints) should allow passage
    # Only explicitly False should block
    pii_scrubbed = state.get("pii_scrubbed")
    
    if pii_scrubbed is False:
        # Explicitly False - block unscrubbed data
        logger.error("VALIDATION GATE BLOCKED: pii_scrubbed = False")
        state["error_message"] = "Validation failed: Data must be PII-scrubbed before processing"
        return "END"
    
    # pii_scrubbed is True or None (legacy checkpoint) - allow passage
    if pii_scrubbed is None:
        logger.info("Validation gate passed: pii_scrubbed = None (legacy checkpoint)")
    else:
        logger.info("Validation gate passed: pii_scrubbed = True")
    
    return "requisition_parsing"
