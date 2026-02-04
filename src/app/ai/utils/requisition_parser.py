"""Requisition Parser Agent - Parses raw requisition JSON into structured format."""

import json
import logging
from typing import Any, Dict, Optional
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RequisitionData


class RequisitionParserAgent(BaseAgent):
    """Parse raw requisition JSON into structured RequisitionData."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("requisition_parser", logger)
    
    def execute(self, raw_requisition: str) -> RequisitionData:
        """
        Parse raw requisition JSON string into structured format.
        
        Args:
            raw_requisition: JSON string or dict representing the requisition
            
        Returns:
            RequisitionData with all extracted fields
        """
        # Parse JSON if string
        if isinstance(raw_requisition, str):
            req_dict = json.loads(raw_requisition)
        else:
            req_dict = raw_requisition
        
        # Extract fields with safe defaults
        mandatory_skills = req_dict.get("mandatory_skills", [])
        if isinstance(mandatory_skills, str):
            mandatory_skills = [s.strip() for s in mandatory_skills.split(",")]
        
        preferred_skills = req_dict.get("preferred_skills", [])
        if isinstance(preferred_skills, str):
            preferred_skills = [s.strip() for s in preferred_skills.split(",")]
        
        certifications = req_dict.get("certifications", [])
        if isinstance(certifications, str):
            certifications = [c.strip() for c in certifications.split(",")]
        
        # Create structured requisition
        requisition = RequisitionData(
            structured_intent=req_dict.get("title", ""),
            mandatory_skills=[s.lower().strip() for s in mandatory_skills],
            preferred_skills=[s.lower().strip() for s in preferred_skills],
            experience_requirements=req_dict.get("experience", ""),
            jd_level=req_dict.get("level", "mid"),
            location=req_dict.get("location", ""),
            certifications=[c.lower().strip() for c in certifications] if certifications else None,
            raw_requisition=req_dict
        )
        
        return requisition
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate that input is valid JSON and contains required fields.
        
        Args:
            input_data: Raw input (string or dict)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to parse if string
            if isinstance(input_data, str):
                json.loads(input_data)
            elif not isinstance(input_data, dict):
                self.logger.warning("Input must be JSON string or dict")
                return False
            
            # Check required fields
            req_dict = json.loads(input_data) if isinstance(input_data, str) else input_data
            required_fields = ["title", "mandatory_skills"]
            
            for field in required_fields:
                if field not in req_dict:
                    self.logger.warning(f"Missing required field: {field}")
                    return False
            
            return True
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}", exc_info=True)
            return False
    
    def format_output(self, result: RequisitionData) -> RequisitionData:
        """Format output - in this case, already in correct format."""
        return result
