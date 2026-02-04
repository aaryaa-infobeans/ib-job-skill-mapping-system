# SpecKit Tasks: IB Requisition Skill Match System Implementation

## TASK BREAKDOWN & EXECUTION PLAN

This document contains granular, actionable tasks extracted from the SpecKit Planning specification. Each task includes:
- Acceptance criteria
- Dependencies
- Effort estimate (Story Points)
- Priority level
- Owner/Assignee placeholder

---

## PHASE 1: DATABASE LAYER & SCHEMA FOUNDATION

### Task P1-T1: Create pgvector Extension & Setup
**Description**: Enable pgvector extension on PostgreSQL database for 3072-dimensional vector operations

**Acceptance Criteria**:
- [ ] pgvector extension installed on target PostgreSQL instance
- [ ] Verified with `SELECT * FROM pg_extension WHERE extname = 'vector';`
- [ ] No conflicts with existing extensions
- [ ] Version compatibility checked (>= 0.5.0)

**Dependencies**: None (foundational)

**Effort**: 2 SP

**Priority**: CRITICAL

**Tasks**:
```sql
-- Task P1-T1.1: Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Task P1-T1.2: Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Task P1-T1.3: Test vector operations
SELECT '[1,2,3]'::vector <-> '[1,2,3]'::vector AS distance;
```

---

### Task P1-T2: Create `team_member_embeddings` Migration
**Description**: Implement Alembic migration for candidate embedding storage

**Acceptance Criteria**:
- [ ] Migration file created: `alembic/versions/{timestamp}_add_team_member_embeddings.py`
- [ ] Forward migration creates table with all columns
- [ ] Reverse migration drops table cleanly
- [ ] Indexes created on team_member_id and created_at
- [ ] VECTOR(3072) column validates dimensionality
- [ ] Migration runs without errors
- [ ] Schema matches specification exactly

**Dependencies**: Task P1-T1 (pgvector extension)

**Effort**: 3 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P1-T2.1: Create migration template
# alembic/versions/{timestamp}_add_team_member_embeddings.py

def upgrade():
    op.create_table(
        'team_member_embeddings',
        sa.Column('id', sa.UUID(), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column('team_member_id', sa.UUID(), nullable=False),
        sa.Column('embedding', Vector(3072), nullable=False),
        sa.Column('profile_text', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['team_member_id'], ['team_member.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_team_member_embeddings_team_member_id', 'team_member_embeddings', ['team_member_id'])
    op.create_index('idx_team_member_embeddings_created_at', 'team_member_embeddings', ['created_at'])

def downgrade():
    op.drop_table('team_member_embeddings')
```

---

### Task P1-T3: Create `llm_request_log` Migration
**Description**: Implement Alembic migration for LLM request governance and cost tracking

**Acceptance Criteria**:
- [ ] Migration file created: `alembic/versions/{timestamp}_add_llm_request_log.py`
- [ ] All columns created: request_id, agent_name, prompt_name, model, tokens, cost_usd
- [ ] created_at timestamp with server default
- [ ] Composite index on (request_id, created_at) for efficient querying
- [ ] Numeric type for cost_usd with precision(10, 4)
- [ ] Migration runs without errors
- [ ] Reverse migration clean

**Dependencies**: Task P1-T1 (foundational)

**Effort**: 2 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P1-T3.1: Create migration
# alembic/versions/{timestamp}_add_llm_request_log.py

def upgrade():
    op.create_table(
        'llm_request_log',
        sa.Column('id', sa.UUID(), server_default=sa.func.gen_random_uuid(), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=True),
        sa.Column('agent_name', sa.String(255), nullable=False),
        sa.Column('prompt_name', sa.String(255), nullable=False),
        sa.Column('model', sa.String(255), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_llm_request_log_request_id_created_at', 'llm_request_log', ['request_id', 'created_at'])
    op.create_index('idx_llm_request_log_agent_name', 'llm_request_log', ['agent_name'])
```

---

### Task P1-T4: Create `skill_ontology` Migration
**Description**: Implement Alembic migration for skill canonicalization and expansion

**Acceptance Criteria**:
- [ ] Migration file created with table definition
- [ ] core_skill TEXT PRIMARY KEY enforces uniqueness
- [ ] enriched_terms TEXT[] array column for skill expansion
- [ ] Index on core_skill for fast lookups
- [ ] Migration runs without errors
- [ ] Table ready for seed data

**Dependencies**: Task P1-T1 (foundational)

**Effort**: 1 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P1-T4.1: Create migration
# alembic/versions/{timestamp}_add_skill_ontology.py

def upgrade():
    op.create_table(
        'skill_ontology',
        sa.Column('core_skill', sa.String(255), nullable=False),
        sa.Column('enriched_terms', sa.ARRAY(sa.String(255)), nullable=True),
        sa.PrimaryKeyConstraint('core_skill')
    )
    op.create_index('idx_skill_ontology_core_skill', 'skill_ontology', ['core_skill'])
```

---

### Task P1-T5: Create `jd_certification_requirements` Migration
**Description**: Implement Alembic migration for certification intelligence

**Acceptance Criteria**:
- [ ] Migration file created with table definition
- [ ] jd_type TEXT column for job role category
- [ ] certification TEXT column for certification name
- [ ] Composite primary key (jd_type, certification)
- [ ] Index on jd_type for efficient lookups
- [ ] Migration reversible

**Dependencies**: Task P1-T1 (foundational)

**Effort**: 1 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P1-T5.1: Create migration
# alembic/versions/{timestamp}_add_jd_certification_requirements.py

def upgrade():
    op.create_table(
        'jd_certification_requirements',
        sa.Column('jd_type', sa.String(255), nullable=False),
        sa.Column('certification', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('jd_type', 'certification')
    )
    op.create_index('idx_jd_certification_jd_type', 'jd_certification_requirements', ['jd_type'])
```

---

### Task P1-T6: Seed `skill_ontology` Table
**Description**: Populate skill_ontology with provided ontology map

**Acceptance Criteria**:
- [ ] All 10 core skills inserted
- [ ] Enriched terms correctly parsed and inserted
- [ ] No duplicate entries
- [ ] Query returns correct enriched_terms for each skill
- [ ] Data matches specification exactly

**Dependencies**: Task P1-T4 (skill_ontology table must exist)

**Effort**: 2 SP

**Priority**: HIGH

**Tasks**:
```python
# Task P1-T6.1: Create seed script
# scripts/seed_skill_ontology.py

SKILL_ONTOLOGY_MAP = {
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

# Task P1-T6.2: Execute seed
# Run: python scripts/seed_skill_ontology.py
```

---

### Task P1-T7: Seed `jd_certification_requirements` Table
**Description**: Populate certification requirements for job types

**Acceptance Criteria**:
- [ ] AI Engineer → AWS ML, Azure AI, GCP ML inserted
- [ ] Cloud Engineer → AWS SA, Azure Admin inserted
- [ ] Backend Engineer → Oracle Java, Spring Certification inserted
- [ ] No duplicate entries
- [ ] Query returns correct certifications for each JD type

**Dependencies**: Task P1-T5 (jd_certification_requirements table must exist)

**Effort**: 1 SP

**Priority**: HIGH

**Tasks**:
```python
# Task P1-T7.1: Create seed script
# scripts/seed_jd_certifications.py

CERTIFICATIONS = {
    "AI Engineer": ["AWS ML", "Azure AI", "GCP ML"],
    "Cloud Engineer": ["AWS SA", "Azure Admin"],
    "Backend Engineer": ["Oracle Java", "Spring Certification"]
}
```

---

### Task P1-T8: Database Validation & Indexing Verification
**Description**: Validate all schema and indexes are correct

**Acceptance Criteria**:
- [ ] All 4 tables exist with correct columns
- [ ] All indexes created and active
- [ ] pgvector operations function correctly
- [ ] Foreign key constraints enforced
- [ ] VACUUM ANALYZE run on all tables
- [ ] No schema conflicts with existing tables

**Dependencies**: Tasks P1-T2 through P1-T7

**Effort**: 1 SP

**Priority**: HIGH

**Validation Checklist**:
```sql
-- Task P1-T8.1: Validate table structure
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('team_member_embeddings', 'llm_request_log', 'skill_ontology', 'jd_certification_requirements');

-- Task P1-T8.2: Validate indexes
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('team_member_embeddings', 'llm_request_log', 'skill_ontology', 'jd_certification_requirements');

-- Task P1-T8.3: Test pgvector
SELECT count(*) FROM (SELECT '[1,2,3]'::vector) AS test;

-- Task P1-T8.4: VACUUM ANALYZE
VACUUM ANALYZE team_member_embeddings;
VACUUM ANALYZE llm_request_log;
VACUUM ANALYZE skill_ontology;
VACUUM ANALYZE jd_certification_requirements;
```

---

## PHASE 2: AGENT ARCHITECTURE & BASE CLASSES

### Task P2-T1: Create BaseAgent Abstract Class
**Description**: Implement foundational agent class with common patterns

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/base.py`
- [ ] Abstract class with abstract methods: execute(), validate_input(), format_output()
- [ ] Error handling decorator implemented
- [ ] Retry decorator with exponential backoff
- [ ] Observability hooks (logging, tracing)
- [ ] Cost tracking integration points
- [ ] Unit tests with 100% coverage
- [ ] No state shared between instances

**Dependencies**: None (foundational)

**Effort**: 5 SP

**Priority**: CRITICAL

**Implementation Template**:
```python
# src/app/ai/agents/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from functools import wraps

class BaseAgent(ABC):
    def __init__(self, agent_name: str, logger: logging.Logger):
        self.agent_name = agent_name
        self.logger = logger
        self.execution_context = {}
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute agent logic"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        pass
    
    @abstractmethod
    def format_output(self, result: Any) -> Any:
        """Format output"""
        pass
    
    def _retry_with_backoff(self, func, max_retries=3):
        """Retry with exponential backoff"""
        pass
    
    def _log_execution(self, result: Any, duration: float):
        """Log agent execution metrics"""
        pass
    
    def _track_cost(self, tokens: Dict[str, int], model: str):
        """Track LLM cost"""
        pass
```

---

### Task P2-T2: Implement RequisitionParserAgent
**Description**: Parse raw requisition JSON into structured format

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/requisition_parser.py`
- [ ] Input: Raw requisition JSON string
- [ ] Output: `RequisitionData` dataclass with all fields
- [ ] Extracted fields: mandatory_skills, preferred_skills, experience_requirements, jd_level, location, certifications
- [ ] Validates all required fields present
- [ ] Handles malformed JSON gracefully
- [ ] Unit tests with 100% coverage
- [ ] Tested with 5+ sample requisitions

**Dependencies**: Task P2-T1 (BaseAgent)

**Effort**: 5 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P2-T2.1: Create dataclass
# src/app/ai/agents/requisition_parser.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RequisitionData:
    structured_intent: str
    mandatory_skills: List[str]
    preferred_skills: List[str]
    experience_requirements: str
    jd_level: str
    location: str
    certifications: Optional[List[str]] = None

# Task P2-T2.2: Implement parser agent
class RequisitionParserAgent(BaseAgent):
    def execute(self, raw_requisition: str) -> RequisitionData:
        pass
```

---

### Task P2-T3: Implement ValidationAgent
**Description**: LLM-based quality gate for requisitions

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/validation.py`
- [ ] Uses prompt from `/prompts/validation.py`
- [ ] Detects: missing mandatory skills, unrealistic experience, conflicting constraints
- [ ] Output: `ValidationResult(is_valid: bool, reasons: List[str])`
- [ ] Returns structured reason list for early exit
- [ ] LLM call logged with tokens and cost
- [ ] Unit tests with mock LLM
- [ ] Tested with 10+ invalid requisitions

**Dependencies**: Task P2-T1 (BaseAgent)

**Effort**: 6 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P2-T3.1: Create result dataclass
from dataclasses import dataclass

@dataclass
class ValidationResult:
    is_valid: bool
    reasons: List[str]
    confidence: float

# Task P2-T3.2: Implement validation agent
class ValidationAgent(BaseAgent):
    def execute(self, requisition: RequisitionData) -> ValidationResult:
        # Use VALIDATION_PROMPT from /prompts/validation.py
        # Log LLM call with cost tracking
        pass
```

---

### Task P2-T4: Implement NormalizerAgent
**Description**: Canonicalize and expand skills via ontology

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/normalizer.py`
- [ ] Queries `skill_ontology` table
- [ ] Canonicalizes skill names (e.g., "Node.js" → "nodejs")
- [ ] Expands skills using enriched_terms
- [ ] Output: `NormalizedRequisition` with mapped skills
- [ ] Ontology cached in-memory for performance
- [ ] Handles unmatched skills gracefully
- [ ] Unit tests with 100% coverage

**Dependencies**: Task P2-T1 (BaseAgent), Task P1-T6 (skill_ontology data)

**Effort**: 5 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P2-T4.1: Create normalized data structure
from dataclasses import dataclass

@dataclass
class NormalizedRequisition:
    original_mandatory_skills: List[str]
    normalized_mandatory_skills: List[str]
    expanded_mandatory_terms: List[str]
    original_preferred_skills: List[str]
    normalized_preferred_skills: List[str]
    expanded_preferred_terms: List[str]

# Task P2-T4.2: Implement normalizer agent
class NormalizerAgent(BaseAgent):
    def __init__(self, db_connection):
        super().__init__("normalizer", logger)
        self.ontology_cache = self._load_ontology()
    
    def execute(self, requisition: RequisitionData) -> NormalizedRequisition:
        pass
    
    def _load_ontology(self):
        # Load skill_ontology into memory
        pass
```

---

### Task P2-T5: Implement EmbeddingAgent
**Description**: Generate 3072-dim embeddings for JD components

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/embedding.py`
- [ ] Generates embeddings for: JD level, mandatory skills, preferred skills, certifications
- [ ] Uses OpenAI embedding model (configurable via ENV)
- [ ] Returns `EmbeddingResult` with all vectors
- [ ] Stores embeddings in `team_member_embeddings` for candidates
- [ ] Validates 3072-dim embeddings
- [ ] Batches API calls for efficiency
- [ ] LLM cost tracked
- [ ] Unit tests with mock embeddings

**Dependencies**: Task P2-T1 (BaseAgent), Task P1-T2 (team_member_embeddings table)

**Effort**: 6 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P2-T5.1: Create embedding result dataclass
from dataclasses import dataclass
import numpy as np

@dataclass
class EmbeddingResult:
    jd_level_vector: np.ndarray  # 3072-dim
    mandatory_vector: np.ndarray  # 3072-dim
    preferred_vector: np.ndarray  # 3072-dim
    certification_vector: Optional[np.ndarray] = None  # 3072-dim

# Task P2-T5.2: Implement embedding agent
class EmbeddingAgent(BaseAgent):
    def execute(self, normalized_requisition: NormalizedRequisition) -> EmbeddingResult:
        # Generate embeddings using OpenAI API
        # Validate 3072-dim
        # Log cost
        pass
```

---

### Task P2-T6: Implement RAGRetrievalAgent
**Description**: Weighted multi-vector RAG retrieval from pgvector

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/rag_retrieval.py`
- [ ] Implements weighted formula: (0.45 * mandatory) + (0.25 * preferred) + (0.20 * jd_level) + (0.10 * certification)
- [ ] Uses pgvector inner product similarity
- [ ] Filters by minimum threshold (configurable)
- [ ] Returns `List[RAGCandidate]` sorted by similarity
- [ ] Efficient pgvector queries (< 500ms for 10k candidates)
- [ ] Unit tests with 100% coverage

**Dependencies**: Task P2-T1 (BaseAgent), Task P2-T5 (embeddings)

**Effort**: 6 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P2-T6.1: Create RAG candidate dataclass
from dataclasses import dataclass

@dataclass
class RAGCandidate:
    team_member_id: str
    final_similarity: float
    mandatory_similarity: float
    preferred_similarity: float
    jd_level_similarity: float
    certification_similarity: float

# Task P2-T6.2: Implement RAG retrieval agent
class RAGRetrievalAgent(BaseAgent):
    def execute(self, embedding_result: EmbeddingResult) -> List[RAGCandidate]:
        # Query pgvector with weighted formula
        # Filter by threshold
        # Sort descending
        pass
    
    def _compute_weighted_similarity(self, weights, similarities):
        # final_similarity = (0.45 * m) + (0.25 * p) + (0.20 * j) + (0.10 * c)
        pass
```

---

### Task P2-T7: Implement ScoringAgent
**Description**: Extended scoring with normalized skills and certifications

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/scoring.py`
- [ ] Reuses existing `compute_score()` logic
- [ ] Extends with: normalized skills, certification RAG matching, profile text enrichment
- [ ] Loads weights from ENV: WEIGHT_MANDATORY_SKILLS, WEIGHT_PREFERRED_SKILLS, etc.
- [ ] Output: `ScoringResult(match_score, confidence, breakdown)`
- [ ] No arbitrary math changes
- [ ] Unit tests with 100% coverage

**Dependencies**: Task P2-T1 (BaseAgent), Task P2-T6 (RAG candidates)

**Effort**: 7 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P2-T7.1: Create scoring result dataclass
from dataclasses import dataclass

@dataclass
class ScoringResult:
    team_member_id: str
    match_score: float
    confidence: float
    score_breakdown: Dict[str, float]
    weighted_components: Dict[str, float]

# Task P2-T7.2: Implement scoring agent
class ScoringAgent(BaseAgent):
    def execute(self, rag_candidate: RAGCandidate, profile_data: Dict) -> ScoringResult:
        # Reuse existing compute_score()
        # Load weights from ENV
        # Include certification matching
        # Include profile enrichment
        pass
    
    def _load_weights_from_env(self):
        # WEIGHT_MANDATORY_SKILLS=0.35
        # WEIGHT_PREFERRED_SKILLS=0.20
        # ... etc
        pass
```

---

### Task P2-T8: Implement RankingAgent
**Description**: Filter, sort, and justify ranked candidates

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/agents/ranking.py`
- [ ] Filters candidates where match_score >= FIT_SCORE_THRESHOLD
- [ ] Sorts descending by match_score
- [ ] Uses prompt from `/prompts/ranking.py` for narratives
- [ ] Output: `RankedCandidateList` with justifications
- [ ] Example narrative generated and validated
- [ ] Unit tests with 100% coverage

**Dependencies**: Task P2-T1 (BaseAgent), Task P2-T7 (ScoringAgent)

**Effort**: 5 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P2-T8.1: Create ranking result dataclass
from dataclasses import dataclass

@dataclass
class RankedCandidate:
    team_member_id: str
    match_score: float
    narrative_justification: str
    rank_position: int

@dataclass
class RankedCandidateList:
    candidates: List[RankedCandidate]
    total_evaluated: int
    total_qualified: int

# Task P2-T8.2: Implement ranking agent
class RankingAgent(BaseAgent):
    def execute(self, scored_candidates: List[ScoringResult]) -> RankedCandidateList:
        # Filter by FIT_SCORE_THRESHOLD
        # Sort descending
        # Generate narratives via LLM
        pass
```

---

## PHASE 3: LLM GOVERNANCE & COST TRACKING

### Task P3-T1: Create LLMRequestInterceptor Middleware
**Description**: Intercept and log all OpenAI API calls

**Acceptance Criteria**:
- [ ] File created: `src/app/services/llm_governance.py`
- [ ] Intercepts all LLM calls (chat, embeddings)
- [ ] Logs to `llm_request_log` table
- [ ] Tracks: agent_name, prompt_name, model, prompt_tokens, completion_tokens, total_tokens
- [ ] Assigns unique request_id for tracing
- [ ] Cost computed using configurable rates
- [ ] Batch logging for efficiency
- [ ] No LLM calls bypass governance
- [ ] Unit tests with mock DB

**Dependencies**: Task P1-T3 (llm_request_log table)

**Effort**: 7 SP

**Priority**: CRITICAL

**Implementation Checklist**:
```python
# Task P3-T1.1: Create interceptor class
# src/app/services/llm_governance.py

import uuid
from typing import Dict, Optional
from datetime import datetime

class LLMRequestInterceptor:
    def __init__(self, db_connection, config):
        self.db = db_connection
        self.config = config
        self.request_id = uuid.uuid4()
    
    def log_request(self, agent_name: str, prompt_name: str, model: str, 
                   prompt_tokens: int, completion_tokens: int) -> None:
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self._compute_cost(prompt_tokens, completion_tokens, model)
        
        # INSERT into llm_request_log
        pass
    
    def _compute_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        input_rate = self.config.get('OPENAI_INPUT_RATE')
        output_rate = self.config.get('OPENAI_OUTPUT_RATE')
        return (prompt_tokens * input_rate) + (completion_tokens * output_rate)
```

---

### Task P3-T2: Create Cost Tracking Utility
**Description**: Cost computation and aggregation utilities

**Acceptance Criteria**:
- [ ] File created: `src/app/services/cost_tracker.py`
- [ ] Formula implemented: cost_usd = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
- [ ] Rate constants from ENV
- [ ] Cost aggregation by agent_name, prompt_name, model
- [ ] Cost reporting interface
- [ ] Unit tests with 100% coverage

**Dependencies**: Task P3-T1 (LLMRequestInterceptor)

**Effort**: 3 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P3-T2.1: Create cost tracker class
# src/app/services/cost_tracker.py

class CostTracker:
    def __init__(self, config):
        self.input_rate = config.get('OPENAI_INPUT_RATE')
        self.output_rate = config.get('OPENAI_OUTPUT_RATE')
    
    def compute_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens * self.input_rate) + (completion_tokens * self.output_rate)
    
    def aggregate_costs_by_agent(self) -> Dict[str, float]:
        # Query llm_request_log, SUM(cost_usd) GROUP BY agent_name
        pass
    
    def get_cost_summary(self, agent_name: Optional[str] = None) -> Dict:
        # Return cost breakdown
        pass
```

---

### Task P3-T3: Create Observability Hooks
**Description**: Logging and tracing integration

**Acceptance Criteria**:
- [ ] File created: `src/app/services/observability.py`
- [ ] Integration with existing logging_config.py
- [ ] Structured logging for agent execution
- [ ] Performance metrics: latency per agent
- [ ] Error tracking with diagnostic context
- [ ] Request tracing with request_id
- [ ] Unit tests

**Dependencies**: Task P2-T1 through P2-T8 (agents)

**Effort**: 4 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P3-T3.1: Create observability class
# src/app/services/observability.py

class ObservabilityHooks:
    def __init__(self, logger):
        self.logger = logger
    
    def log_agent_entry(self, agent_name: str, input_size: int, request_id: str):
        pass
    
    def log_agent_exit(self, agent_name: str, duration: float, success: bool, request_id: str):
        pass
    
    def log_llm_call(self, agent_name: str, model: str, tokens: Dict, cost: float):
        pass
```

---

### Task P3-T4: Create Cost Governance API Endpoints
**Description**: REST endpoints for cost monitoring and auditing

**Acceptance Criteria**:
- [ ] Endpoint: GET `/metrics/llm-costs` - cost summary by agent/model/prompt
- [ ] Endpoint: GET `/metrics/llm-usage` - token usage tracking
- [ ] Endpoint: GET `/metrics/request-audit` - full audit trail with request_id
- [ ] Response format: JSON with time-series or aggregated data
- [ ] Authentication required
- [ ] Unit tests for endpoints

**Dependencies**: Task P3-T1 through P3-T3

**Effort**: 4 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P3-T4.1: Create cost metrics controller
# src/app/api/controllers/metrics_controller.py

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/llm-costs")
async def get_llm_costs(agent_name: Optional[str] = None):
    # Query llm_request_log
    # Aggregate by agent_name, model, prompt_name
    # Return summary
    pass

@router.get("/llm-usage")
async def get_llm_usage():
    # Query token totals
    # Return time-series data
    pass

@router.get("/request-audit")
async def get_request_audit(request_id: Optional[str] = None):
    # Return full audit trail
    pass
```

---

## PHASE 4: PROMPT MANAGEMENT & GOVERNANCE

### Task P4-T1: Create `/prompts/requisition_parser.py`
**Description**: Prompt for parsing requisitions into structured format

**Acceptance Criteria**:
- [ ] File created: `prompts/requisition_parser.py`
- [ ] PARSER_SYSTEM_PROMPT constant defined
- [ ] Comments explain: Purpose, Input, Output
- [ ] Prompt instructs extraction of all required fields
- [ ] Prompt returns JSON-formatted output

**Dependencies**: None (prompts are standalone)

**Effort**: 2 SP

**Priority**: HIGH

---

### Task P4-T2: Create `/prompts/validation.py`
**Description**: Prompt for LLM-based requisition validation

**Acceptance Criteria**:
- [ ] File created: `prompts/validation.py`
- [ ] VALIDATION_SYSTEM_PROMPT constant defined
- [ ] Instructs validation checks
- [ ] Returns VALID or INVALID with reasons

**Dependencies**: None

**Effort**: 2 SP

**Priority**: CRITICAL

---

### Task P4-T3: Create `/prompts/normalizer.py`
**Description**: Prompt for skill normalization via ontology

**Acceptance Criteria**:
- [ ] File created: `prompts/normalizer.py`
- [ ] NORMALIZER_SYSTEM_PROMPT constant defined
- [ ] Instructs skill canonicalization and expansion

**Dependencies**: None

**Effort**: 2 SP

**Priority**: HIGH

---

### Task P4-T4: Create `/prompts/embedding.py`
**Description**: Prompt guidance for text preparation

**Acceptance Criteria**:
- [ ] File created: `prompts/embedding.py`
- [ ] EMBEDDING_INSTRUCTION constant defined
- [ ] Guides text chunking for embedding generation

**Dependencies**: None

**Effort**: 1 SP

**Priority**: MEDIUM

---

### Task P4-T5: Create `/prompts/scoring.py`
**Description**: Prompt for scoring context and enrichment

**Acceptance Criteria**:
- [ ] File created: `prompts/scoring.py`
- [ ] SCORING_CONTEXT_PROMPT constant defined
- [ ] Provides semantic relevance factors

**Dependencies**: None

**Effort**: 2 SP

**Priority**: HIGH

---

### Task P4-T6: Create `/prompts/ranking.py`
**Description**: Prompt for narrative justification generation

**Acceptance Criteria**:
- [ ] File created: `prompts/ranking.py`
- [ ] RANKING_NARRATIVE_PROMPT constant defined
- [ ] Instructs generation of human-readable justifications
- [ ] Example output matches specification

**Dependencies**: None

**Effort**: 2 SP

**Priority**: HIGH

---

### Task P4-T7: Create Prompt Registry & Versioning
**Description**: Central prompt management and versioning

**Acceptance Criteria**:
- [ ] File created: `src/app/services/prompt_registry.py`
- [ ] Registry class with version tracking
- [ ] Audit logging: who used which prompt, when
- [ ] Fallback mechanisms for prompt versions
- [ ] Unit tests

**Dependencies**: Tasks P4-T1 through P4-T6

**Effort**: 3 SP

**Priority**: MEDIUM

---

## PHASE 5: LANGGRAPH WORKFLOW & DAG ORCHESTRATION

### Task P5-T1: Create LangGraph State Schema
**Description**: Define workflow state structure

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/workflow/state.py`
- [ ] `AgentState` dataclass defined
- [ ] Fields: requisition, validation_result, normalized_requisition, embeddings, rag_candidates, scores, ranked_results
- [ ] Immutable state transitions
- [ ] Error tracking fields
- [ ] Unit tests

**Dependencies**: All Phase 2 agents (data structures)

**Effort**: 2 SP

**Priority**: CRITICAL

---

### Task P5-T2: Implement DAG Graph Structure
**Description**: Create LangGraph DAG matching specification

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/workflow/graph.py`
- [ ] DAG nodes: Parser → Validation → [EARLY_EXIT or Normalizer] → Embedding → RAG → Scoring → Ranking → EXIT
- [ ] Conditional branching for validation failure
- [ ] Proper state threading
- [ ] All transitions defined
- [ ] Unit tests with mock agents

**Dependencies**: Task P5-T1 (state schema), All Phase 2 agents

**Effort**: 6 SP

**Priority**: CRITICAL

**Implementation Template**:
```python
# src/app/ai/workflow/graph.py

from langgraph.graph import StateGraph

def create_agent_graph():
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("parser", requisition_parser_node)
    graph.add_node("validation", validation_node)
    graph.add_node("normalizer", normalizer_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("ranking", ranking_node)
    
    # Add edges
    graph.add_edge("parser", "validation")
    graph.add_conditional_edges("validation", validation_router)  # early exit logic
    graph.add_edge("normalizer", "embedding")
    # ... etc
    
    return graph.compile()
```

---

### Task P5-T3: Implement Retry Logic
**Description**: Add exponential backoff retry mechanism

**Acceptance Criteria**:
- [ ] Retry decorator for transient failures
- [ ] Exponential backoff strategy
- [ ] Max retry attempts configurable via ENV
- [ ] Failed request logging
- [ ] Integration with all agents
- [ ] Unit tests with mock retries

**Dependencies**: Task P5-T2 (DAG structure)

**Effort**: 4 SP

**Priority**: HIGH

**Implementation Checklist**:
```python
# Task P5-T3.1: Create retry decorator
# src/app/ai/workflow/retries.py

def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 2.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
        return wrapper
    return decorator
```

---

### Task P5-T4: Implement Partial Failure Handling
**Description**: System resilience with degradation

**Acceptance Criteria**:
- [ ] Fallback strategies defined
- [ ] Embedding failure → use text similarity
- [ ] RAG retrieval failure → return all candidates
- [ ] Scoring failure → use default distribution
- [ ] Error state tracking in AgentState
- [ ] Integration with all agents
- [ ] Unit tests

**Dependencies**: Task P5-T2 (DAG structure)

**Effort**: 5 SP

**Priority**: HIGH

---

### Task P5-T5: Implement Observability Hooks
**Description**: Comprehensive workflow tracing

**Acceptance Criteria**:
- [ ] Node entry/exit logging
- [ ] State transition logging
- [ ] Timing metrics per node
- [ ] Cost accumulation per request
- [ ] Request ID threading through DAG
- [ ] Distributed tracing support
- [ ] Unit tests

**Dependencies**: Task P3-T3 (observability), Task P5-T2 (DAG)

**Effort**: 5 SP

**Priority**: HIGH

---

### Task P5-T6: Create Workflow Validator
**Description**: DAG topology and state validation

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/workflow/validators.py`
- [ ] DAG topology validation
- [ ] State transition validation
- [ ] Orphaned node detection
- [ ] Cycle detection
- [ ] Unit tests

**Dependencies**: Task P5-T2 (DAG structure)

**Effort**: 3 SP

**Priority**: MEDIUM

---

### Task P5-T7: Implement Workflow Executor
**Description**: DAG execution with state management

**Acceptance Criteria**:
- [ ] File created: `src/app/ai/workflow/executor.py`
- [ ] Execute DAG with state management
- [ ] Handle early exits
- [ ] Aggregate metrics and costs
- [ ] Return final result with lineage
- [ ] Unit tests with end-to-end scenarios

**Dependencies**: Task P5-T2 through P5-T5

**Effort**: 5 SP

**Priority**: CRITICAL

---

## PHASE 6: INTEGRATION WITH EXISTING SERVICES

### Task P6-T1: Extend API Endpoints
**Description**: Create new REST endpoints for matching

**Acceptance Criteria**:
- [ ] POST `/api/v1/requisitions/{id}/match` - trigger workflow
- [ ] GET `/api/v1/requisitions/{id}/matches` - retrieve results
- [ ] GET `/api/v1/matches/{match_id}/details` - detailed breakdown
- [ ] Response payloads include agent lineage and costs
- [ ] Authentication integrated
- [ ] Unit tests for endpoints

**Dependencies**: Task P5-T7 (workflow executor)

**Effort**: 4 SP

**Priority**: CRITICAL

---

### Task P6-T2: Integrate with Database Service
**Description**: Connect multi-agent system to existing DB layer

**Acceptance Criteria**:
- [ ] Reuse existing team_member connection pool
- [ ] Add embeddings CRUD methods
- [ ] Add cost log writing methods
- [ ] Add skill ontology query methods
- [ ] Add certification requirement query methods
- [ ] Connection pooling optimized
- [ ] Unit tests with mock DB

**Dependencies**: Task P1 (database schema)

**Effort**: 4 SP

**Priority**: HIGH

---

### Task P6-T3: Create Requisition Matching Service
**Description**: Orchestrate workflow execution

**Acceptance Criteria**:
- [ ] File created: `src/app/services/requisition_matching_service.py`
- [ ] Orchestrates workflow execution
- [ ] Caches results with TTL (configurable)
- [ ] Handles concurrent requests
- [ ] Result persistence
- [ ] Unit tests

**Dependencies**: Task P5-T7 (executor), Task P6-T2 (DB integration)

**Effort**: 4 SP

**Priority**: HIGH

---

### Task P6-T4: Extend Audit Service
**Description**: Log matching operations and costs

**Acceptance Criteria**:
- [ ] Extend existing audit service
- [ ] Log all matching operations
- [ ] Track cost per requisition
- [ ] Audit trail per candidate evaluation
- [ ] Explainability data storage
- [ ] Unit tests

**Dependencies**: Task P3 (cost tracking)

**Effort**: 3 SP

**Priority**: MEDIUM

---

### Task P6-T5: Create Matching Result Persistence
**Description**: Store match results with full breakdown

**Acceptance Criteria**:
- [ ] Create `matching_results` table schema
- [ ] Store match results with scoring breakdown
- [ ] Store narrative justifications
- [ ] Store cost breakdown
- [ ] Timestamp and versioning
- [ ] Migration file created
- [ ] Queries optimized

**Dependencies**: Task P1 (database schema)

**Effort**: 3 SP

**Priority**: MEDIUM

---

## PHASE 7: CONFIGURATION & ENVIRONMENT SETUP

### Task P7-T1: Create/Update `.env.example`
**Description**: Document all required environment variables

**Acceptance Criteria**:
- [ ] File created/updated: `.env.example`
- [ ] All LLM variables documented
- [ ] All weight variables documented
- [ ] All threshold variables documented
- [ ] All retry configuration documented
- [ ] All database variables documented
- [ ] Comments explain usage and defaults
- [ ] No actual secrets in file

**Dependencies**: None (documentation)

**Effort**: 2 SP

**Priority**: MEDIUM

**Content Checklist**:
```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_INPUT_RATE=0.003  # per 1M tokens
OPENAI_OUTPUT_RATE=0.006  # per 1M tokens

# Agent Weights
WEIGHT_MANDATORY_SKILLS=0.35
WEIGHT_PREFERRED_SKILLS=0.20
WEIGHT_EXPERIENCE=0.15
WEIGHT_SEMANTIC_SIMILARITY=0.10
WEIGHT_CERTIFICATION=0.10
WEIGHT_JD_TEXT=0.10

# Thresholds
FIT_SCORE_THRESHOLD=0.5
RAG_SIMILARITY_THRESHOLD=0.6

# Retry Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2

# Database
DATABASE_URL=postgresql://...
PGVECTOR_DIMENSION=3072
```

---

### Task P7-T2: Create Config Loader Utility
**Description**: ENV variable validation and loading

**Acceptance Criteria**:
- [ ] File created: `src/app/config.py`
- [ ] Validate all required ENV vars on load
- [ ] Type conversion (float for rates, int for counts)
- [ ] Fallback defaults where appropriate
- [ ] Config immutability
- [ ] Unit tests with various ENV states

**Dependencies**: None (foundational)

**Effort**: 3 SP

**Priority**: CRITICAL

**Implementation Template**:
```python
# src/app/config.py

from pydantic import BaseSettings, validator

class Config(BaseSettings):
    # LLM Config
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_input_rate: float
    openai_output_rate: float
    
    # Weights
    weight_mandatory_skills: float = 0.35
    weight_preferred_skills: float = 0.20
    # ... etc
    
    # Thresholds
    fit_score_threshold: float = 0.5
    rag_similarity_threshold: float = 0.6
    
    @validator('weight_mandatory_skills')
    def validate_weight(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Weight must be between 0 and 1')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

---

### Task P7-T3: Update Existing settings.py
**Description**: Integrate new config with existing settings

**Acceptance Criteria**:
- [ ] No duplication with existing settings
- [ ] Backward compatibility maintained
- [ ] All new vars integrated
- [ ] Existing tests pass
- [ ] Clear import patterns

**Dependencies**: Task P7-T2 (config loader)

**Effort**: 2 SP

**Priority**: HIGH

---

### Task P7-T4: Create Environment Validation
**Description**: Startup health check for configuration

**Acceptance Criteria**:
- [ ] File created: `src/app/services/env_validation.py`
- [ ] Check all required ENV vars present
- [ ] Database connectivity check
- [ ] LLM API access validation
- [ ] pgvector availability check
- [ ] Clear error messages for missing config
- [ ] Called on app startup
- [ ] Unit tests

**Dependencies**: Task P7-T2 (config loader)

**Effort**: 3 SP

**Priority**: HIGH

---

## PHASE 8: TESTING & VALIDATION

### Task P8-T1: Create Agent Unit Tests
**Description**: Test each agent in isolation

**Acceptance Criteria**:
- [ ] Tests for all 7 agents
- [ ] Mock dependencies (LLM, DB)
- [ ] Success path tests
- [ ] Failure path tests
- [ ] Input validation tests
- [ ] Output contract validation
- [ ] Coverage target: >85%
- [ ] Tests in `tests/unit/test_agents/`

**Dependencies**: Phase 2 agents

**Effort**: 10 SP

**Priority**: CRITICAL

**Structure**:
```
tests/unit/test_agents/
  test_requisition_parser.py
  test_validation.py
  test_normalizer.py
  test_embedding.py
  test_rag_retrieval.py
  test_scoring.py
  test_ranking.py
```

---

### Task P8-T2: Create Integration Tests
**Description**: Test workflow with real database

**Acceptance Criteria**:
- [ ] Tests in `tests/integration/test_workflow.py`
- [ ] Test with containerized database
- [ ] Mock LLM responses
- [ ] Error scenarios
- [ ] Retry logic
- [ ] Cost tracking accuracy
- [ ] Coverage target: >75%

**Dependencies**: Phase 5 (workflow), Phase 6 (integration)

**Effort**: 8 SP

**Priority**: CRITICAL

---

### Task P8-T3: Create End-to-End Tests
**Description**: Full workflow validation

**Acceptance Criteria**:
- [ ] Tests in `tests/e2e/test_matching_flow.py`
- [ ] Full requisition to ranked results
- [ ] Sample data
- [ ] Result accuracy validation
- [ ] Performance benchmarks documented
- [ ] Integration with all systems

**Dependencies**: Phase 6 (integration)

**Effort**: 6 SP

**Priority**: HIGH

---

### Task P8-T4: Create Test Data Generators
**Description**: Realistic test data generation

**Acceptance Criteria**:
- [ ] File created: `tests/test_data/generators.py`
- [ ] Generate realistic requisitions
- [ ] Generate realistic candidate profiles
- [ ] Populate test database
- [ ] Seed skill ontology
- [ ] Reproducible data generation

**Dependencies**: Phase 1 (schema)

**Effort**: 4 SP

**Priority**: MEDIUM

---

### Task P8-T5: Create Cost Accuracy Tests
**Description**: Verify cost formula correctness

**Acceptance Criteria**:
- [ ] Cost formula test cases
- [ ] Compare with OpenAI pricing
- [ ] Edge cases (zero tokens, max tokens)
- [ ] Rounding accuracy
- [ ] Coverage > 95%

**Dependencies**: Phase 3 (cost tracking)

**Effort**: 3 SP

**Priority**: HIGH

---

### Task P8-T6: Create Embedding Quality Tests
**Description**: Validate embedding generation and storage

**Acceptance Criteria**:
- [ ] Verify 3072-dim embeddings
- [ ] pgvector storage/retrieval tests
- [ ] Similarity computation validation
- [ ] Formula verification: (0.45, 0.25, 0.20, 0.10)
- [ ] Performance benchmarks

**Dependencies**: Phase 2 (embedding agent), Phase 5 (workflow)

**Effort**: 5 SP

**Priority**: HIGH

---

### Task P8-T7: Create Workflow Validation Tests
**Description**: DAG topology and execution validation

**Acceptance Criteria**:
- [ ] DAG topology tests
- [ ] State transition tests
- [ ] Early exit validation
- [ ] Retry logic tests
- [ ] Observability logging tests
- [ ] Coverage > 90%

**Dependencies**: Phase 5 (workflow)

**Effort**: 6 SP

**Priority**: HIGH

---

## PHASE 9: DOCUMENTATION & KNOWLEDGE TRANSFER

### Task P9-T1: Create Architecture Documentation
**Description**: System overview and design rationale

**Acceptance Criteria**:
- [ ] File created: `docs/architecture/multi-agent-system.md`
- [ ] System overview diagram
- [ ] Agent dependency graph
- [ ] DAG execution flow diagram
- [ ] Data flow diagram
- [ ] Decision records (ADRs)
- [ ] Rationale for design choices

**Dependencies**: All previous phases

**Effort**: 5 SP

**Priority**: MEDIUM

---

### Task P9-T2: Create Developer Guide
**Description**: Setup and development documentation

**Acceptance Criteria**:
- [ ] File created: `docs/developer-guide.md`
- [ ] Setup instructions
- [ ] Agent implementation pattern
- [ ] Adding new agents guide
- [ ] Testing patterns
- [ ] Debugging guide
- [ ] Code examples

**Dependencies**: All previous phases

**Effort**: 5 SP

**Priority**: MEDIUM

---

### Task P9-T3: Create Operational Guide
**Description**: Monitoring and operations documentation

**Acceptance Criteria**:
- [ ] File created: `docs/operational-guide.md`
- [ ] Monitoring & observability
- [ ] Cost governance review process
- [ ] Troubleshooting guide
- [ ] Performance tuning
- [ ] Database maintenance

**Dependencies**: Phase 3 (governance), Phase 6 (integration)

**Effort**: 4 SP

**Priority**: MEDIUM

---

### Task P9-T4: Create Prompt Engineering Guide
**Description**: Prompt management best practices

**Acceptance Criteria**:
- [ ] File created: `docs/prompt-engineering-guide.md`
- [ ] Prompt writing standards
- [ ] Versioning strategy
- [ ] A/B testing approach
- [ ] Cost optimization tips
- [ ] Examples and anti-patterns

**Dependencies**: Phase 4 (prompts)

**Effort**: 3 SP

**Priority**: LOW

---

### Task P9-T5: Create API Documentation
**Description**: REST API specification

**Acceptance Criteria**:
- [ ] OpenAPI/Swagger schema generated
- [ ] Request/response examples
- [ ] Error codes and handling
- [ ] Rate limiting policies
- [ ] Authentication details
- [ ] Published to API documentation site

**Dependencies**: Phase 6 (API endpoints)

**Effort**: 3 SP

**Priority**: MEDIUM

---

### Task P9-T6: Create Database Schema Documentation
**Description**: Database design documentation

**Acceptance Criteria**:
- [ ] File created: `docs/database-schema.md`
- [ ] Table relationships diagram
- [ ] Index strategy explanation
- [ ] Maintenance procedures
- [ ] Backup/restore procedures
- [ ] Performance tuning guide

**Dependencies**: Phase 1 (schema)

**Effort**: 3 SP

**Priority**: MEDIUM

---

## TASK SUMMARY & SEQUENCING

### Critical Path Tasks (Must Complete First)
1. **P1-T1**: pgvector setup
2. **P1-T2**: team_member_embeddings migration
3. **P1-T3**: llm_request_log migration
4. **P2-T1**: BaseAgent class
5. **P7-T2**: Config loader
6. **P5-T1**: State schema
7. **P5-T2**: DAG graph
8. **P5-T7**: Workflow executor

### Parallel Streams
- **Stream A**: Database (Phase 1) → Data Services (Phase 3) → Governance (Phase 3)
- **Stream B**: Agents (Phase 2) → Workflow (Phase 5) → API Integration (Phase 6)
- **Stream C**: Prompts (Phase 4) → Config (Phase 7) → Testing (Phase 8)

### Testing Gates
- After Phase 2: Unit tests for all agents
- After Phase 5: Integration tests for DAG
- After Phase 6: E2E tests for full flow
- Final: >80% coverage overall

---

## Document Metadata

| Property | Value |
|----------|-------|
| Version | 1.0 |
| Status | TASK SPECIFICATION |
| Total Task Points | ~150 SP |
| Estimated Duration | 8 weeks |
| Last Updated | 2026-02-03 |
| Target Audience | Engineering Team |

