"""AI Fit Confidence utility."""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from app.ai.utils.llm_client import llm_client

from app.settings import settings

logger = logging.getLogger(__name__)


CONFIDENCE_PROMPT = """
Evaluate the fit between the Candidate Profile and the Job Description.
Focus on experience alignment, skill depth (beyond keywords), and career trajectory.

Job Description:
{jd_text}

Candidate Profile and Structured Data:
{profile_text}

Provide evaluation in a valid JSON object:
{{
  "confidence_score": (float 0.0-1.0),
  "reasoning": "brief reasoning (max 15 words)",
  "key_strengths": ["strength1", "strength2"],
  "major_gaps": ["gap1"]
}}

IMPORTANT:
- Return ONLY the JSON object.
- DO NOT include escaped quotes within the reasoning text.
- Ensure all JSON fields are present.
- If a skill from the JD appears in "Skills on record", describe its proficiency level (e.g. "limited proficiency in Python — 2/5 rating, 6 months"). Do NOT say "lacks X" or "missing X" for a skill that is present on record. Only list a skill in major_gaps if it is completely absent from "Skills on record".
"""


def get_ai_fit_confidence(jd_text: str, profile_text: str, model: Optional[str] = None) -> Dict[str, Any]:
    """TASK-08: AI Fit Confidence."""
    try:
        messages = [
            {"role": "system", "content": "You are an expert technical recruiter. Respond ONLY in valid JSON."},
            {"role": "user", "content": CONFIDENCE_PROMPT.format(jd_text=jd_text, profile_text=profile_text)}
        ]
        
        # Determine model if not provided
        if not model:
            provider = settings.llm_provider.lower()
            if provider == "anthropic":
                model = settings.ib_anthropic_model
            elif provider == "groq":
                model = settings.groq_model
            elif provider == "google":
                model = settings.google_model
            elif provider in ("local", "ollama"):
                model = settings.llm_local_model
            else:
                model = settings.openai_model
        
        # Use global defaults from settings (no hardcoded temperature or max_tokens here)
        content, usage = llm_client.chat_completion(
            messages=messages,
            model=model,
            response_format={"type": "json_object"}
        )


        
        if not content:
            return {"confidence_score": 0.5, "reasoning": "LLM failed to respond", "error": True}
            
        data = _parse_json_robustly(content)
        return {
            "confidence_score": float(data.get("confidence_score", 0.5)),
            "reasoning": data.get("reasoning", ""),
            "key_strengths": data.get("key_strengths", []),
            "major_gaps": data.get("major_gaps", []),
            "usage": usage
        }
        
    except Exception as e:
        logger.error(f"AI confidence evaluation failed: {str(e)}")
        return {"confidence_score": 0.5, "reasoning": f"Error: {str(e)}", "error": True}

def _parse_json_robustly(text: str) -> Dict[str, Any]:
    """
    Robustly parse JSON from LLM response, handling markdown blocks and common errors.
    """
    try:
        # 1. Try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from markdown block
    import re
    json_block = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Try finding the first '{' and last '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        extracted = text[start_idx:end_idx+1]
        try:
            # Basic cleanup: remove unescaped newlines in strings (common LLM error)
            # This is complex to do right with regex, so we'll try to just load it first
            return json.loads(extracted)
        except json.JSONDecodeError:
            # Final attempt: replace unescaped newlines in reasoning (most common culprit)
            # Find the reasoning field and replace internal newlines
            try:
                # This is a bit hacky but targets the specific error seen: "... \n \n key_strengths: ..."
                cleaned = re.sub(r'("reasoning":\s*".*?")', lambda m: m.group(1).replace('\n', ' '), extracted, flags=re.DOTALL)
                return json.loads(cleaned)
            except:
                pass

    logger.error(f"Failed to parse JSON robustly from content: {text[:200]}...")
    return {}

def calculate_ai_boost(confidence: float) -> float:
    """Boosts final match score based on AI confidence scaling."""
    if confidence < settings.ai_confidence_threshold_boost:
        return 0.0
    
    # Scale from threshold to 1.0 -> boost_mid to boost_senior
    threshold = settings.ai_confidence_threshold_boost
    min_boost = settings.ai_boost_mid
    max_boost = settings.ai_boost_senior
    
    # (confidence - threshold) / (1.0 - threshold) is [0,1]
    scaled_boost = min_boost + ((max_boost - min_boost) * (confidence - threshold) / (1.0 - threshold))
    return round(min(max_boost, scaled_boost), 4)
