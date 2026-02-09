"""Normalizer Agent - Canonicalizes and expands skills via ontology."""

import logging
from typing import Any, Dict, List, Optional
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RequisitionData, NormalizedRequisition


class NormalizerAgent(BaseAgent):
    """Normalize and expand skills using skill ontology."""
    
    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("normalizer", logger)
        self.db = db_connection
        self.ontology_cache: Dict[str, List[str]] = {}
        self._load_ontology()
    
    def _load_ontology(self):
        """Load skill ontology from database into memory."""
        if not self.db:
            # Use default ontology if no DB connection
            self.ontology_cache = {
                ".net": ["windows development", "c#", "asp.net", "microsoft stack"],
                "python": ["backend", "scripting", "data engineering", "ai foundation"],
                "fastapi": ["api development", "asyncio", "rest", "backend"],
                "langchain": ["llm orchestration", "agentic ai", "prompt engineering"],
                "react": ["frontend", "javascript", "ui development"],
                "aws": ["cloud computing", "serverless", "infrastructure"],
                "java": ["enterprise", "spring boot", "backend", "jvm"],
                "docker": ["containerization", "devops", "kubernetes"],
            }
            return
        
        try:
            # Query skill_ontology table
            result = self.db.execute("SELECT core_skill, enriched_terms FROM skill_ontology")
            for row in result:
                core_skill = row[0].lower().strip()
                enriched_terms = row[1] or []
                self.ontology_cache[core_skill] = [t.lower().strip() for t in enriched_terms]
            
            self.logger.info(f"Loaded {len(self.ontology_cache)} skills from ontology")
        except Exception as e:
            self.logger.error(f"Failed to load ontology from DB: {str(e)}", exc_info=True)
            # Fall back to empty cache
            self.ontology_cache = {}
    
    def execute(self, requisition: RequisitionData) -> NormalizedRequisition:
        """
        Normalize and expand skills using ontology.
        
        Args:
            requisition: RequisitionData with skills to normalize
            
        Returns:
            NormalizedRequisition with normalized and expanded skills
        """
        # Normalize mandatory skills
        norm_mandatory = []
        expanded_mandatory_terms = []
        
        for skill in requisition.mandatory_skills:
            normalized = self._canonicalize_skill(skill)
            norm_mandatory.append(normalized)
            
            # Add enriched terms
            if normalized in self.ontology_cache:
                expanded_mandatory_terms.extend(self.ontology_cache[normalized])
        
        # Normalize preferred skills
        norm_preferred = []
        expanded_preferred_terms = []
        
        for skill in requisition.preferred_skills:
            normalized = self._canonicalize_skill(skill)
            norm_preferred.append(normalized)
            
            # Add enriched terms
            if normalized in self.ontology_cache:
                expanded_preferred_terms.extend(self.ontology_cache[normalized])
        
        result = NormalizedRequisition(
            original_mandatory_skills=requisition.mandatory_skills,
            normalized_mandatory_skills=norm_mandatory,
            expanded_mandatory_terms=list(set(expanded_mandatory_terms)),  # Deduplicate
            original_preferred_skills=requisition.preferred_skills,
            normalized_preferred_skills=norm_preferred,
            expanded_preferred_terms=list(set(expanded_preferred_terms)),  # Deduplicate
            original_requisition=requisition
        )
        
        return result
    
    def _canonicalize_skill(self, skill: str) -> str:
        """
        Canonicalize a skill name.
        
        Args:
            skill: Skill name to canonicalize
            
        Returns:
            Canonicalized skill name
        """
        skill_lower = skill.lower().strip()
        
        # Direct lookup
        if skill_lower in self.ontology_cache:
            return skill_lower
        
        # Try fuzzy matching with common variations
        variations = {
            "node.js": "nodejs",
            "node js": "nodejs",
            "javascript": "javascript",
            "typescript": "typescript",
            "kubernetes": "kubernetes",
            "k8s": "kubernetes",
            "golang": "go",
            "csharp": ".net",
            "c#": ".net",
            "asp.net core": ".net",
            "fastapi": "fastapi",
            "flask": "python",
            "django": "python",
        }
        
        if skill_lower in variations:
            return variations[skill_lower]
        
        # Return as-is if no match found
        return skill_lower
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is RequisitionData."""
        if not isinstance(input_data, RequisitionData):
            self.logger.warning(f"Input must be RequisitionData, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: NormalizedRequisition) -> NormalizedRequisition:
        """Format output - already in correct format."""
        return result
