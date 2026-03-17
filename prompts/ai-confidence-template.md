# Prompt Template: AI Fit Confidence

**Version:** 1.0  
**Agent:** AIConfidenceAgent  
**Last Updated:** 2026-03-17  

## Template
```text
Evaluate the fit between the Candidate Profile and the Job Description.
Focus on experience alignment, skill depth (beyond keywords), and career trajectory.

Job Description:
{jd_text}

Candidate Profile:
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
```
