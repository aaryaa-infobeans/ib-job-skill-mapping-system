# SpecKit Specification: IB Requisition Skill Match System

## MISSION

Enhance an EXISTING IB Requisition Skill Match System into a production-ready, multi-agent, LangGraph-orchestrated AI platform.
You MUST extend the existing codebase — do NOT rewrite or restructure arbitrarily.
The system is built using LangGraph, PostgreSQL, pgvector, and multi-agent LLM architectures.

---

## SYSTEM GOALS

- Deterministic JD ↔ Candidate matching
- Auditable and explainable scoring logic
- Full LLM governance & cost tracking
- Modular, stateless, independently testable agents
- Enterprise readiness (observability, retries, partial failure handling)

---

## CORE TECH STACK (NON-NEGOTIABLE)

- Python
- LangGraph (strict DAG execution)
- PostgreSQL + pgvector (3072-dim embeddings)
- OpenAI-compatible chat + embedding models
- ENV-driven configuration (no hardcoded values)

---

## DATABASE REQUIREMENTS (MUST IMPLEMENT EXACTLY)

### 1. Candidate Embeddings

```sql
CREATE TABLE team_member_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_member_id UUID REFERENCES team_member(id),
    embedding VECTOR(3072),
    profile_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Embedding Rules:**
- Embed ALL candidate data:
  - Skills
  - Experience
  - Certifications
  - Designation
  - Resume / uploaded profile text
- If profile text changes → re-embed and update

### 2. LLM Governance & Cost Tracking

```sql
CREATE TABLE llm_request_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID,
    agent_name TEXT,
    prompt_name TEXT,
    model TEXT,
    prompt_tokens INT,
    completion_tokens INT,
    total_tokens INT,
    cost_usd NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Cost Formula:**
```
cost_usd = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
```

**Requirement:** ALL LLM calls MUST be intercepted and logged.

---

## MULTI-AGENT DESIGN (STRICT)

Each agent MUST be:
- Stateless
- Independently testable
- Single-responsibility

### Agent 1: Requisition Parser Agent

**Input:** Raw requisition JSON

**Output:**
- Structured intent
- Mandatory skills
- Preferred skills
- Experience requirements
- JD level
- Location
- Certifications (if present)

### Agent 2: Validation Agent (LLM Quality Gate)

**Responsibilities:**
- Validate requisition completeness and realism
- Detect:
  - Missing mandatory skills
  - Unrealistic experience requirements
  - Conflicting constraints

**Behavior:** If INVALID → exit LangGraph DAG early with explicit reason

### Agent 3: Normalizer Agent (Skill Ontology Alignment)

**Schema:**
```sql
CREATE TABLE skill_ontology (
    core_skill TEXT PRIMARY KEY,
    enriched_terms TEXT[]
);
```

**Ontology Map (Populate with this data):**
```json
{
  ".net": ["windows development", "c#", "asp.net", "microsoft stack"],
  "python": ["backend", "scripting", "data engineering", "ai foundation"],
  "fastapi": ["api development", "asyncio", "rest", "backend"],
  "langchain": ["llm orchestration", "agentic ai", "prompt engineering"],
  "wordpress": ["cms", "php", "web development", "content management"],
  "react": ["frontend", "javascript", "ui development"],
  "aws": ["cloud computing", "serverless", "infrastructure"],
  "java": ["enterprise", "spring boot", "backend", "jvm"],
  "openai": ["llm", "generative ai", "gpt", "ai development"],
  "vector databases": ["pinecone", "milvus", "qdrant", "weaviate", "rag"],
  "docker": ["containerization", "devops", "kubernetes"]
}
```

**Responsibilities:**
- Canonicalize skills
- Expand skills via ontology
- Align JD terminology with candidate terminology

---

## CERTIFICATION INTELLIGENCE (NEW)

**Schema:**
```sql
CREATE TABLE jd_certification_requirements (
    jd_type TEXT,
    certification TEXT
);
```

**Sample Data:**
- AI Engineer → AWS ML, Azure AI, GCP ML
- Cloud Engineer → AWS SA, Azure Admin
- Backend Engineer → Oracle Java, Spring Certification

**Requirement:** This table MUST be used during RAG matching against candidate certifications.

---

## WEIGHTED MULTI-VECTOR RAG (CORE LOGIC)

For EACH JD generate embeddings for:
- JD Level
- Mandatory Skills
- Preferred Skills
- Certifications (optional)

**Final Similarity Formula (DO NOT CHANGE):**
```
final_similarity =
  (0.45 * mandatory_vector) +
  (0.25 * preferred_vector) +
  (0.20 * jd_level_vector) +
  (0.10 * certification_vector)
```

**Requirement:** Use pgvector inner product similarity.

---

## SCORING AGENT (MANDATORY)

**Requirements:**
- Reuse the existing `compute_score()` logic
- Extend it to include:
  - Normalized skills
  - Certification RAG matching
  - Profile text enrichment
- DO NOT change score math arbitrarily

**Weights (MUST be loaded from .env):**
```
WEIGHT_MANDATORY_SKILLS=0.35
WEIGHT_PREFERRED_SKILLS=0.20
WEIGHT_EXPERIENCE=0.15
WEIGHT_SEMANTIC_SIMILARITY=0.10
WEIGHT_CERTIFICATION=0.10
WEIGHT_JD_TEXT=0.10
FIT_SCORE_THRESHOLD=0.5
```

---

## RANKING AGENT

**Responsibilities:**
- Filter candidates where `match_score >= FIT_SCORE_THRESHOLD`
- Sort candidates descending by score
- Generate a professional narrative justification

**Example Output:**
```
"Strong alignment in mandatory skills (Python, FastAPI) with relevant AWS certification 
and high semantic JD similarity."
```

---

## LANGGRAPH WORKFLOW (STRICT DAG)

**Exact Implementation Required:**

```
ENTRY
 ↓
Requisition Parser
 ↓
Validation (early exit if invalid)
 ↓
Normalization
 ↓
Embedding
 ↓
Weighted RAG Retrieval
 ↓
Scoring
 ↓
Ranking
 ↓
EXIT
```

**DAG MUST support:**
- Retry logic
- Partial failure handling
- Observability hooks

---

## PROMPT GOVERNANCE (CRITICAL)

**ALL prompts MUST:**
- Live in `/prompts/*.py`
- Be named constants
- Include comments explaining:
  - Purpose
  - Input
  - Output

**Example:**
```python
VALIDATION_PROMPT = """
# Purpose: Validate requisition realism and completeness
# Input: Requisition JSON
# Output: VALID or INVALID with reasons
"""
```

**Requirement:** NO inline prompts in business logic.

---

## DELIVERABLES (REQUIRED OUTPUT)

You MUST generate:
- [x] SQL schemas
- [ ] Agent class implementations
- [ ] LangGraph workflow
- [ ] Scoring agent integration
- [ ] Weighted RAG retrieval logic
- [ ] Certification intelligence
- [ ] Prompt templates
- [ ] ENV-based configuration usage
- [ ] Sample test data
- [ ] Clean, extensible folder structure

---

## HARD RULES

- ❌ No monolithic functions
- ❌ No magic numbers
- ❌ No inline prompts
- ❌ No skipped governance
- ❌ No fake embeddings
- ❌ No TODOs or placeholders

---

## FINAL OUTPUT EXPECTATION

Produce a fully working, production-grade system blueprint and codebase suitable for:
- Enterprise hiring systems
- AI audits
- Cost governance
- Future agent expansion

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Database & Schema
- [ ] Create `team_member_embeddings` table
- [ ] Create `llm_request_log` table
- [ ] Create `skill_ontology` table
- [ ] Create `jd_certification_requirements` table
- [ ] Populate skill ontology
- [ ] Populate certification requirements
- [ ] Add pgvector extension

### Phase 2: Agent Implementation
- [ ] Implement `RequisitionParserAgent`
- [ ] Implement `ValidationAgent`
- [ ] Implement `NormalizerAgent`
- [ ] Implement `EmbeddingAgent`
- [ ] Implement `RAGRetrievalAgent`
- [ ] Implement `ScoringAgent`
- [ ] Implement `RankingAgent`

### Phase 3: LangGraph Workflow
- [ ] Create DAG graph structure
- [ ] Wire all agent transitions
- [ ] Implement early exit logic for validation
- [ ] Add retry mechanisms
- [ ] Add observability hooks

### Phase 4: Prompt Management
- [ ] Create `/prompts/requisition_parser.py`
- [ ] Create `/prompts/validation.py`
- [ ] Create `/prompts/normalizer.py`
- [ ] Create `/prompts/embedding.py`
- [ ] Create `/prompts/scoring.py`
- [ ] Create `/prompts/ranking.py`

### Phase 5: Configuration & Environment
- [ ] Update `.env` with all required weights
- [ ] Update `.env` with LLM cost rates
- [ ] Create config loader utility
- [ ] Document all ENV variables

### Phase 6: Testing & Validation
- [ ] Unit tests for each agent
- [ ] Integration tests for DAG
- [ ] Test data generation
- [ ] Cost tracking validation
- [ ] Embedding quality checks

---

## Document Metadata

| Property | Value |
|----------|-------|
| Version | 1.0 |
| Status | SPECIFICATION |
| Last Updated | 2026-02-03 |
| Author | SpecKit |
| Phase | Requirements Definition |

