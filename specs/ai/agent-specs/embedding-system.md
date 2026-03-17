# Agent Specification: Embedding System

**Version:** 1.2  
**Modified By:** CR-SCORE-003  
**Last Updated:** 2026-03-17  

## 1. Purpose
The Embedding System manages the generation of vector representations for both job descriptions and candidate profiles using local transformer models.

## 2. Model Configuration
- **Primary Local Model**: `google/embeddinggemma-300m`
  - **Source**: HuggingFace Transformers
  - **Dimensions**: 768
  - **Pooling**: Mean
  - **Normalization**: L2
  - **Device**: CPU (standard) or CUDA (if available)

## 3. Multi-Vector Strategy
To improve match precision, the system segments data into thematic vectors:

| Vector Name | Target Field | Purpose |
| :--- | :--- | :--- |
| `skills_embedding` | Normalized Skill Sets | Targeted skill similarity matching. |
| `resume_embedding` | Profile Summary / Bio | Role, title, and career context matching. |
| `certifications_embedding` | Credential List | Verification of mandatory certifications. |

## 4. Ingestion & Retrieval
- **Ingestion**: `profile_text` is scrubbed of PII before being passed to the embedding agent.
- **Retrieval**: The `RAGRetrievalAgent` routes sub-queries to specific columns based on the requirement type (e.g., Mandatory Skills -> `skills_embedding`).

## 5. Failover
- If the local model fails to load, the system cascades to the fallback provider defined in `settings.py` (e.g., OpenAI or Google Vertex).
