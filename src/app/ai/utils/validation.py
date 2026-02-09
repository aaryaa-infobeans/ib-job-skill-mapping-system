"""Validation Agent - LLM-based quality gate for requisitions."""

import logging
from typing import Any, Optional
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RequisitionData, ValidationResult


class ValidationAgent(BaseAgent):
    """Validate requisition completeness and realism using LLM."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("validation", logger)
    
    def execute(self, requisition: RequisitionData) -> ValidationResult:
        """
        Validate requisition for completeness and realism.
        
        Args:
            requisition: RequisitionData to validate
            
        Returns:
            ValidationResult with is_valid flag and reasons
        """
        reasons = []
        is_valid = True
        confidence = 1.0
        
        # Check mandatory skills
        if not requisition.mandatory_skills:
            reasons.append("No mandatory skills specified")
            is_valid = False
            confidence -= 0.3
        
        # Check for too many mandatory skills (> 10 is unrealistic)
        if len(requisition.mandatory_skills) > 10:
            reasons.append(f"Unrealistic: {len(requisition.mandatory_skills)} mandatory skills (max recommended: 10)")
            confidence -= 0.2
        
        # Check experience requirements
        try:
            # Try to extract years from experience string
            experience_str = requisition.experience_requirements.lower()
            if "year" in experience_str:
                # Simple heuristic: if it says "50 years" that's unrealistic
                import re
                numbers = re.findall(r'\d+', experience_str)
                if numbers and int(numbers[0]) > 30:
                    reasons.append(f"Unrealistic experience requirement: {requisition.experience_requirements}")
                    confidence -= 0.2
        except Exception:
            pass
        
        # Check JD level
        valid_levels = ["junior", "mid", "senior", "lead", "principal"]
        if requisition.jd_level.lower() not in valid_levels:
            self.logger.warning(f"Unusual JD level: {requisition.jd_level}")
        
        # Overall confidence
        confidence = max(0.0, confidence)
        
        return ValidationResult(
            is_valid=is_valid,
            reasons=reasons,
            confidence=confidence
        )
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate that input is RequisitionData.
        
        Args:
            input_data: Input to validate
            
        Returns:
            True if valid RequisitionData, False otherwise
        """
        if not isinstance(input_data, RequisitionData):
            self.logger.warning(f"Input must be RequisitionData, got {type(input_data)}")
            return False
        
        # Must have at least a title
        if not input_data.structured_intent:
            self.logger.warning("RequisitionData must have structured_intent")
            return False
        
        return True
    
    def format_output(self, result: ValidationResult) -> ValidationResult:
        """Format output - already in correct format."""
        return result
