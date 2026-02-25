"""AI Fit Confidence utility using Groq llama-3.1-8b."""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from app.ai.utils.llm_client import llm_client

logger = logging.getLogger(__name__)

CONFIDENCE_PROMPT = """
Evaluate the fit between the Candidate Profile and the Job Description.
Focus on experience alignment, skill depth (beyond keywords), and career trajectory.

Job Description:
{jd_text}

Candidate Profile:
{profile_text}

Provide your evaluation in JSON format with:
- "confidence_score": (float between 0.0 and 1.0)
- "reasoning": (short 2-sentence explanation of fit)
- "key_strengths": (list of 2-3 top skills matched)
- "major_gaps": (list of 1-2 critical gaps, if any)
"""

def get_ai_fit_confidence(jd_text: str, profile_text: str) -> Dict[str, Any]:
    """TASK-08: AI Fit Confidence (Groq llama-3.1-8b)."""
    try:
        messages = [
            {"role": "system", "content": "You are an expert technical recruiter. Respond ONLY in valid JSON."},
            {"role": "user", "content": CONFIDENCE_PROMPT.format(jd_text=jd_text, profile_text=profile_text)}
        ]
        
        # Using Groq llama-3.1-8b-instant as specified (mapped to groq_model in settings or passed explicitly)
        # We use temperature 0.0 for deterministic evaluation
        content, usage = llm_client.chat_completion(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        if not content:
            return {"confidence_score": 0.5, "reasoning": "LLM failed to respond", "error": True}
            
        data = json.loads(content)
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

def calculate_ai_boost(confidence: float) -> float:
    """Boosts final match score: >= 0.70 confidence -> +0.05 to +0.08 boost (scaled)."""
    if confidence < 0.70:
        return 0.0
    
    # Scale from 0.70 to 1.0 -> 0.05 to 0.08
    # (confidence - 0.70) / (1.0 - 0.70) is [0,1]
    # 0.05 + 0.03 * [0,1]
    scaled_boost = 0.05 + (0.03 * (confidence - 0.70) / 0.30)
    return round(min(0.08, scaled_boost), 4)
