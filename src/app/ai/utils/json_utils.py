import json
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_json_from_response(content: str) -> Optional[Dict[str, Any]]:
    """Robustly extract JSON from LLM response, handling markdown blocks and whitespace."""
    if not content or not content.strip():
        logger.error("LLM returned an empty response")
        return None
        
    content = content.strip()
    
    # Try parsing directly first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
        
    # Attempt to extract from markdown code blocks
    # Look for ```json ... ``` or just ``` ... ```
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Try finding the first '{' and last '}' if standard methods fail
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1 and end > start:
        json_str = content[start:end+1].strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extracted JSON substring: {str(e)}")
            
    logger.error(f"Could not extract valid JSON from LLM response. Raw response: {content[:500]}...")
    return None
