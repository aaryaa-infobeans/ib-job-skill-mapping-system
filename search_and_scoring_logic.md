System Architecture: Search & Scoring Logic
This document provides a comprehensive technical overview of the embedding service, search mechanisms, and the multi-layered scoring system used in the IB Job Skill Mapping System.

1. Embedding Service
The system uses Google's Gemma model (via models/gemini-embedding-001) to generate vector representations of job descriptions and candidate profiles.

Technical Details:
Model: gemini-embedding-001 (Fallback if Gemma-300M is unavailable).
Dimension: 768-dimensional vectors.
Componentized Embedding: Instead of embedding the whole Job Description (JD) as one block, the system embeds specific components to allow for granular similarity matching:
JD Level: Experience level requirements.
Mandatory Skills: Canonical and alternative skill names.
Preferred Skills: Desired but not required skills.
Certifications: Normalized certification names and related concepts.
2. Phase 0: Hybrid Search (RAG Retrieval)
Phase 0 is a massive search across all active candidates to identify the top 40 best fits for deep evaluation. It combines keyword-based "BM25-like" counting with vector similarity.

The Hybrid Score Formula (SPEC-001):
HybridScore = (SkillBoost * 0.40) + (PreferredBoost * 0.20) + (VectorSimilarity * 0.25) + 0.15
Components & Weights:
SkillBoost (40%): 
(Matches / Total Mandatory Skills)
. This simulates BM25 by rewarding exact keyword matches for required skills.
PreferredBoost (20%): 
(Matches / Total Preferred Skills)
. Rewards candidates having optional "nice-to-have" skills.
VectorSimilarity (25%): A weighted average of four cosine similarities:
Mandatory Skills Similarity
Preferred Skills Similarity
JD Level/Text Similarity
Certification Similarity
Weighting: Weights originate from 
settings.py
 (default: Mandatory > Preferred > Level > Cert).
Selection Base (15%): A fixed constant (0.15) added to all candidates who pass the hard filters, ensuring a baseline score for pool entry.
Hard Filters (Fail-fast Gating):
Active Status: is_active must be true.
Experience Gap: experience_in_months >= min_months.
Skill Relevance: Candidate must have at least one match in either Mandatory or Preferred skills.
3. Phase 1: Agentic Scoring
Candidates from Phase 0 undergo a detailed, deterministic evaluation that accounts for role seniority and AI-enhanced reasoning.

Role-Based Logic:
The scoring logic changes based on the candidate's seniority:

Role Level	Exp Range	Mandatory Weight	Preferred Weight	Semantic Weight	Context Weight	Fit Threshold
SENIOR	8+ yrs	50%	20%	25%	5%	0.60
MID	2-8 yrs	40%	20%	25%	15%	0.50
JUNIOR	< 2 yrs	30%	30%	25%	15%	0.50
Step-by-Step Scoring Calculation:
1. Mandatory Skill Grouping (Agentic Logic)
Unlike simple keyword matching, the system uses Skill Groups. If a JD asks for "Python", and the candidate has "FastAPI" or "Django", the system recognizes this as satisfying the "Python" group, even if the word "Python" is missing.

2. Context Boost (Capped at 8%)
Context includes Location, Work Mode, Certifications, and Experience. These are calculated individually but their total contribution to the final score is capped at 0.08 (8%) to ensure skills remain the primary driver.

3. Skill Family Penalty (-0.1)
To prevent "Jack-of-all-trades" mismatching, a -0.1 penalty is applied if a candidate's profile is dominated by a different skill family (e.g., a Frontend expert applying for a Backend/AI role).

4. AI Fit Confidence & Boost
The system calls an LLM to evaluate the "fit" beyond keywords.

AI Boost: If AI Confidence >= 0.70, a boost of +0.05 to +0.08 is added.
Senior Waiver: If a Senior candidate fails the semantic similarity gate but has an AI Confidence >= 0.75, the system waives the gate and qualifies them, assuming the vector search missed subtle experience cues.
Summary of Weights (Global)
These weights are the backbone of the system's "Deterministic Hybrid Scoring" strategy:

Component	Weight Contribution (Base)	Details
Mandatory Skills	30% - 50%	Multi-word grouping & alternative matching.
Preferred Skills	20% - 30%	Secondary skill alignment.
Semantic Fit	25%	Pure vector similarity (Gemma).
Context Boost	5% - 15%	Exp/Cert/Loc/Mode (Hard capped at 8% total).
AI Confidence	+0.05 to +0.08	Late-stage boost for high-confidence matches.
Penalty	-0.10	Applied for role/skill family misalignment.

