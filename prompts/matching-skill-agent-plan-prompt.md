# SpecKit Plan: IB Requisition Skill Match System Multi-Agent Enhancement

## OBJECTIVE

Generate a comprehensive, phase-based implementation plan to transform the IB Requisition Skill Match System into a production-ready, multi-agent, LangGraph-orchestrated AI platform while preserving existing codebase integrity.

---

## PLANNING CONSTRAINTS & GUARDRAILS

### Non-Negotiable Constraints
1. **Code Preservation**: Extend existing codebase; do NOT rewrite or restructure arbitrarily
2. **Tech Stack Immutability**: Python, LangGraph, PostgreSQL + pgvector (3072-dim), OpenAI-compatible models
3. **Schema Exactness**: Implement database schemas EXACTLY as specified
4. **Deterministic Execution**: LangGraph DAG must execute in strict order with no parallelization
5. **Zero Governance Skips**: ALL LLM calls must be logged and cost-tracked
6. **No Placeholders**: All code must be production-grade; no TODOs or fake implementations

### Quality Gates
- ✅ All agents must be stateless and independently testable
- ✅ All prompts must be externalized to `/prompts/*.py`
- ✅ All configuration must be ENV-driven
- ✅ All LLM costs must be tracked and auditable
- ✅ All embeddings must use real 3072-dim vectors via pgvector

---

## PHASE BREAKDOWN

### PHASE 1: Database Layer & Schema Foundation
**Goal**: Establish all required database schemas and seed data

**Tasks**:
1. Create migration script for `team_member_embeddings` table
   - UUID primary key with auto-generation
   - VECTOR(3072) column with pgvector indexing
   - profile_text TEXT for raw candidate data
   - metadata JSONB for extensibility
   - created_at timestamp tracking

2. Create migration script for `llm_request_log` table
   - Full request tracking: agent_name, prompt_name, model
   - Token counting: prompt_tokens, completion_tokens, total_tokens
   - Cost computation: cost_usd NUMERIC precision
   - Request correlation via request_id UUID

3. Create migration script for `skill_ontology` table
   - core_skill TEXT PRIMARY KEY
   - enriched_terms TEXT[] for skill expansion
   - Index on core_skill for fast lookups

4. Create migration script for `jd_certification_requirements` table
   - jd_type TEXT (job role category)
   - certification TEXT (certification name)
   - Composite indexing for JD type lookups

5. Seed skill ontology with provided ontology map
   - .net ecosystem skills
   - Python data/backend skills
   - API & backend frameworks
   - Cloud platform skills
   - Containerization & DevOps
   - AI/LLM skills
   - Vector database skills

6. Seed certification requirements with sample mappings
   - AI Engineer certifications
   - Cloud Engineer certifications
   - Backend Engineer certifications
   - Extensible schema for future roles

7. Create Alembic migration file
   - Proper versioning for schema changes
   - Reversibility of migrations
   - Track in version control

**Deliverables**:
- Alembic migration file `versions/{timestamp}_add_multi_agent_schema.py`
- SQL schema definitions
- Seeded ontology and certification data
- Indexing strategy for query performance

**Success Criteria**:
- All tables created with correct constraints
- pgvector extension installed and verified
- Seed data inserted without errors
- Migration reversible and idempotent

---

### PHASE 2: Agent Architecture & Base Classes
**Goal**: Implement stateless, testable agent framework

**Tasks**:
1. Create agent base class `BaseAgent`
   - Abstract methods: `execute()`, `validate_input()`, `format_output()`
   - State isolation pattern
   - Error handling & retry decorators
   - Observability hooks (logging, tracing)
   - Cost tracking integration

2. Implement `RequisitionParserAgent`
   - Parse raw requisition JSON into structured format
   - Extract: mandatory_skills, preferred_skills, experience_requirements, jd_level, location, certifications
   - Validation: ensure all required fields present
   - Output: structured `RequisitionData` dataclass
   - Unit testable with sample requisition JSON

3. Implement `ValidationAgent`
   - LLM-based quality gate using prompt from `/prompts/validation.py`
   - Detect missing mandatory skills
   - Detect unrealistic experience requirements (e.g., 10+ years for entry-level)
   - Detect conflicting constraints
   - Return: `ValidationResult(is_valid: bool, reasons: List[str])`
   - Early exit signal if invalid

4. Implement `NormalizerAgent`
   - Query `skill_ontology` table for canonical skills
   - Canonicalize skill names (e.g., "Node.js" → "nodejs")
   - Expand skills using enriched_terms
   - Align JD terminology with candidate terminology
   - Output: `NormalizedRequisition` with mapped skills
   - Cache ontology in memory for performance

5. Implement `EmbeddingAgent`
   - Generate 3072-dim embeddings for:
     - JD level text
     - Mandatory skills combined text
     - Preferred skills combined text
     - Certifications combined text (if present)
   - Use OpenAI embedding model (configurable via ENV)
   - Store embeddings in `team_member_embeddings` for candidates
   - Return: `EmbeddingResult` with all vector components

6. Implement `RAGRetrievalAgent`
   - Query pgvector using weighted multi-vector formula
   - Compute final_similarity = (0.45 * mandatory) + (0.25 * preferred) + (0.20 * jd_level) + (0.10 * certification)
   - Use inner product similarity metric
   - Filter candidates by minimum threshold (configurable)
   - Return ranked list: `List[RAGCandidate]` with similarity scores

7. Implement `ScoringAgent`
   - Reuse existing `compute_score()` logic
   - Extend with:
     - Normalized skills matching
     - Certification RAG matching
     - Profile text semantic enrichment
   - Load weights from ENV: WEIGHT_MANDATORY_SKILLS, etc.
   - Output: `ScoringResult(match_score, confidence, breakdown)`
   - No arbitrary math changes

8. Implement `RankingAgent`
   - Filter candidates where match_score >= FIT_SCORE_THRESHOLD (from ENV)
   - Sort descending by score
   - Generate narrative justification using `/prompts/ranking.py`
   - Example: "Strong alignment in mandatory skills (Python, FastAPI) with relevant AWS certification"
   - Output: `RankedCandidateList` with justifications

**Deliverables**:
- `src/app/ai/agents/base.py` - BaseAgent abstract class
- `src/app/ai/agents/requisition_parser.py` - Parser agent
- `src/app/ai/agents/validation.py` - Validation agent
- `src/app/ai/agents/normalizer.py` - Normalizer agent
- `src/app/ai/agents/embedding.py` - Embedding agent
- `src/app/ai/agents/rag_retrieval.py` - RAG retrieval agent
- `src/app/ai/agents/scoring.py` - Scoring agent
- `src/app/ai/agents/ranking.py` - Ranking agent
- Dataclasses for all agent inputs/outputs
- Unit tests for each agent

**Success Criteria**:
- Each agent independently testable with mock data
- No state shared between agent instances
- All agents follow single-responsibility principle
- No hardcoded values; all config from ENV
- Cost tracking hooks integrated

---

### PHASE 3: LLM Governance & Cost Tracking
**Goal**: Implement comprehensive LLM observability and cost governance

**Tasks**:
1. Create `LLMRequestInterceptor` middleware
   - Intercept ALL OpenAI API calls
   - Log to `llm_request_log` table
   - Track: agent_name, prompt_name, model, tokens (prompt/completion/total)
   - Compute cost_usd using configurable rates (ENV: OPENAI_INPUT_RATE, OPENAI_OUTPUT_RATE)
   - Assign unique request_id for tracing
   - Handle batch logging efficiently

2. Create cost tracking utility
   - Formula implementation: cost_usd = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
   - Rate constants from ENV
   - Cost aggregation by agent_name, prompt_name, model
   - Cost reporting interface

3. Create observability hooks
   - Integration with existing logging_config.py
   - Structured logging: agent execution, token counts, costs
   - Performance metrics: latency per agent
   - Error tracking with diagnostic context

4. Implement cost governance API endpoints
   - GET /metrics/llm-costs - cost summary by agent/model/prompt
   - GET /metrics/llm-usage - token usage tracking
   - GET /metrics/request-audit - full audit trail with request_id
   - Rate limiting awareness

**Deliverables**:
- `src/app/services/llm_governance.py` - Interceptor and cost tracking
- `src/app/services/cost_tracker.py` - Cost computation utilities
- API endpoints in appropriate controller
- Integration with existing logging

**Success Criteria**:
- Every LLM call logged with correct cost calculation
- Request IDs traceable end-to-end
- Cost accuracy verified against OpenAI API
- No LLM calls bypass governance

---

### PHASE 4: Prompt Management & Governance
**Goal**: Externalize all prompts with versioning and documentation

**Tasks**:
1. Create `/prompts/requisition_parser.py`
   - PARSER_SYSTEM_PROMPT constant
   - Purpose: Extract structured data from raw requisition JSON
   - Input: Raw requisition JSON string
   - Output: JSON with mandatory_skills, preferred_skills, jd_level, location, certifications
   - Version comment with last updated date

2. Create `/prompts/validation.py`
   - VALIDATION_SYSTEM_PROMPT constant
   - Purpose: Validate requisition realism and completeness
   - Input: Structured requisition data
   - Output: VALID or INVALID with specific reasons
   - Quality gates: missing mandatory skills, unrealistic experience, conflicting constraints

3. Create `/prompts/normalizer.py`
   - NORMALIZER_SYSTEM_PROMPT constant
   - Purpose: Normalize and canonicalize skills using ontology
   - Input: Requisition with raw skills
   - Output: Requisition with canonical skill names and expanded terms
   - Instruction: Query skill_ontology for enriched_terms

4. Create `/prompts/embedding.py`
   - EMBEDDING_INSTRUCTION constant
   - Purpose: Guide text preparation for embedding generation
   - Input: JD level text, mandatory skills, preferred skills, certifications
   - Output: Prepared text chunks for embedding

5. Create `/prompts/scoring.py`
   - SCORING_CONTEXT_PROMPT constant
   - Purpose: Provide context for semantic similarity and enrichment
   - Input: Candidate profile + JD context
   - Output: Semantic relevance factors for scoring logic

6. Create `/prompts/ranking.py`
   - RANKING_NARRATIVE_PROMPT constant
   - Purpose: Generate human-readable justifications for ranked candidates
   - Input: Candidate data + match score breakdown
   - Output: Professional narrative (example: "Strong alignment in mandatory skills...")
   - Format: Single paragraph, actionable insights

7. Create prompt registry
   - Central registry of all prompts with versions
   - Prompt auditing: who used which prompt, when
   - Fallback mechanisms for prompt versioning

**Deliverables**:
- All `/prompts/*.py` files with constants
- Prompt documentation with purpose/input/output
- Prompt registry utility
- Version tracking

**Success Criteria**:
- Zero inline prompts in business logic
- All prompts documented with purpose
- Prompts externalized and versioned
- Easy to update without code changes

---

### PHASE 5: LangGraph Workflow & DAG Orchestration
**Goal**: Implement strict DAG execution with retry and failure handling

**Tasks**:
1. Create LangGraph state schema
   - `AgentState` dataclass
   - Fields: requisition, validation_result, normalized_requisition, embeddings, rag_candidates, scores, ranked_results
   - Immutable state transitions
   - Error tracking in state

2. Implement DAG graph structure
   ```
   ENTRY → Parser → Validation → [EARLY_EXIT or Normalizer] → 
   Embedding → RAG_Retrieval → Scoring → Ranking → EXIT
   ```
   - Conditional branching for validation failure
   - Proper state threading through all nodes

3. Implement retry logic
   - Retry decorator for transient failures (e.g., LLM rate limits)
   - Exponential backoff strategy
   - Max retry attempts (configurable via ENV)
   - Failed request logging

4. Implement partial failure handling
   - Allow system to proceed with degraded functionality
   - Fallback strategies:
     - If embedding fails, use text similarity
     - If RAG retrieval fails, return all candidates
     - If scoring fails, use default score distribution
   - Error state tracking

5. Implement observability hooks
   - Node entry/exit logging
   - State transition logging
   - Timing metrics per node
   - Cost accumulation per request
   - Distributed tracing support (request_id threading)

6. Create workflow validator
   - Ensure DAG topology correctness
   - Validate state transitions
   - Check for orphaned nodes

7. Implement workflow executor
   - Execute DAG with state management
   - Handle early exits from validation
   - Aggregate metrics and costs
   - Return final result with lineage

**Deliverables**:
- `src/app/ai/workflow/graph.py` - LangGraph DAG definition
- `src/app/ai/workflow/state.py` - AgentState schema
- `src/app/ai/workflow/executor.py` - DAG executor with retries
- `src/app/ai/workflow/validators.py` - DAG validation
- Workflow documentation with diagram

**Success Criteria**:
- DAG executes in strict order per specification
- Validation early exit works correctly
- Retries handle transient failures
- Partial failures don't cascade
- All nodes observable and traceable

---

### PHASE 6: Integration with Existing Services
**Goal**: Integrate multi-agent system with existing API and database layers

**Tasks**:
1. Extend existing API endpoints
   - POST `/api/v1/requisitions/{id}/match` - trigger multi-agent workflow
   - GET `/api/v1/requisitions/{id}/matches` - retrieve cached results
   - GET `/api/v1/matches/{match_id}/details` - get detailed scoring breakdown
   - Enhanced response payloads with agent lineage and costs

2. Integrate with existing database service
   - Use existing team_member connection pool
   - Add methods for embeddings CRUD
   - Add methods for cost log writing
   - Add methods for skill ontology queries
   - Add methods for certification requirement queries

3. Create requisition matching service
   - Orchestrate workflow execution
   - Cache results with TTL (configurable)
   - Handle concurrent requests
   - Result persistence

4. Extend existing audit service
   - Log all matching operations
   - Track cost per requisition
   - Audit trail per candidate evaluation
   - Explainability data storage

5. Create matching result persistence
   - Store match results with full scoring breakdown
   - Store narrative justifications
   - Store cost breakdown
   - Timestamp and versioning

**Deliverables**:
- Enhanced API controllers
- Integration with existing services
- Database schema extensions (migrations)
- Result models and persistence logic

**Success Criteria**:
- Existing APIs enhanced without breaking changes
- New endpoints follow existing patterns
- Results cached and retrievable
- Full audit trail maintained

---

### PHASE 7: Configuration & Environment Setup
**Goal**: Ensure all configuration is externalized and ENV-driven

**Tasks**:
1. Create/update `.env.example`
   - LLM Configuration:
     - OPENAI_API_KEY
     - OPENAI_MODEL (default: gpt-4)
     - OPENAI_EMBEDDING_MODEL (default: text-embedding-3-large)
     - OPENAI_INPUT_RATE (cost per 1M input tokens)
     - OPENAI_OUTPUT_RATE (cost per 1M output tokens)
   - Agent Weights:
     - WEIGHT_MANDATORY_SKILLS=0.35
     - WEIGHT_PREFERRED_SKILLS=0.20
     - WEIGHT_EXPERIENCE=0.15
     - WEIGHT_SEMANTIC_SIMILARITY=0.10
     - WEIGHT_CERTIFICATION=0.10
     - WEIGHT_JD_TEXT=0.10
   - Thresholds:
     - FIT_SCORE_THRESHOLD=0.5
     - RAG_SIMILARITY_THRESHOLD=0.6
   - Retry Configuration:
     - MAX_RETRY_ATTEMPTS=3
     - RETRY_BACKOFF_FACTOR=2
   - Database:
     - DATABASE_URL
     - PGVECTOR_DIMENSION=3072

2. Create config loader utility
   - Validate all required ENV vars on startup
   - Type conversion (float for rates, int for thresholds)
   - Fallback defaults where appropriate
   - Config immutability

3. Update existing settings.py
   - Integrate new config with existing settings
   - Avoid duplication
   - Maintain backward compatibility

4. Create environment validation
   - Startup health check for ENV vars
   - Database connectivity check
   - LLM API access validation
   - pgvector availability check

**Deliverables**:
- Updated `.env.example`
- `src/app/config.py` - Config loader with validation
- Environment validation script
- Configuration documentation

**Success Criteria**:
- All magic numbers eliminated
- All LLM keys and rates configurable
- Config validation on startup
- Clear configuration documentation

---

### PHASE 8: Testing & Validation
**Goal**: Comprehensive testing strategy covering all agents and workflows

**Tasks**:
1. Create agent unit tests
   - Test each agent in isolation
   - Mock dependencies (LLM, database)
   - Test success and failure paths
   - Validate input/output contracts
   - Coverage target: >85%

2. Create integration tests
   - Test workflow with real database (containerized)
   - Test with mock LLM responses
   - Test error scenarios and retries
   - Test cost tracking accuracy
   - Coverage target: >75%

3. Create end-to-end tests
   - Full workflow from requisition to ranked results
   - Test with sample data
   - Validate result accuracy
   - Performance benchmarks

4. Create test data generators
   - Generate realistic requisitions
   - Generate realistic candidate profiles
   - Populate test database
   - Seed with skill ontology

5. Create cost accuracy tests
   - Verify cost formula implementation
   - Compare with OpenAI pricing
   - Test edge cases (zero tokens, max tokens)

6. Create embedding quality tests
   - Verify 3072-dim embeddings
   - Test pgvector storage/retrieval
   - Test similarity computations
   - Validate formula (0.45, 0.25, 0.20, 0.10)

7. Create workflow validation tests
   - DAG topology correctness
   - State transitions
   - Early exit on validation failure
   - Retry logic
   - Observability logging

**Deliverables**:
- `tests/unit/test_agents/` - Unit tests
- `tests/integration/test_workflow.py` - Integration tests
- `tests/e2e/test_matching_flow.py` - E2E tests
- `tests/test_data/generators.py` - Test data generation
- Test coverage reports

**Success Criteria**:
- All tests passing
- Coverage >80% overall
- No flaky tests
- Performance benchmarks documented
- Cost accuracy verified

---

### PHASE 9: Documentation & Knowledge Transfer
**Goal**: Comprehensive documentation for maintainability and future expansion

**Tasks**:
1. Create architecture documentation
   - System overview diagram
   - Agent dependency graph
   - DAG execution flow
   - Data flow diagram
   - Decision records (ADRs)

2. Create developer guide
   - Setup instructions
   - Agent implementation pattern
   - Adding new agents
   - Testing patterns
   - Debugging guide

3. Create operational guide
   - Monitoring & observability
   - Cost governance review
   - Troubleshooting common issues
   - Performance tuning
   - Database maintenance

4. Create prompt engineering guide
   - Prompt writing standards
   - Prompt versioning strategy
   - A/B testing prompts
   - Cost optimization

5. Create API documentation
   - OpenAPI/Swagger schema
   - Request/response examples
   - Error codes and handling
   - Rate limiting policies

6. Create database schema documentation
   - Table relationships
   - Indexing strategy
   - Maintenance procedures
   - Backup/restore procedures

**Deliverables**:
- Architecture documentation
- Developer guide
- Operational guide
- API documentation (Swagger)
- Database schema documentation

**Success Criteria**:
- Documentation comprehensive and accurate
- Examples working and tested
- Clear architecture rationale
- Future expansion guidelines clear

---

## IMPLEMENTATION SEQUENCE

### Sprint 1 (Week 1-2): Foundation
- Phase 1: Database Layer & Schema
- Phase 4: Prompt Management (parallel)

### Sprint 2 (Week 3-4): Agent Development
- Phase 2: Agent Architecture & Base Classes
- Phase 3: LLM Governance & Cost Tracking (parallel)

### Sprint 3 (Week 5-6): Orchestration & Integration
- Phase 5: LangGraph Workflow
- Phase 6: Integration with Existing Services (parallel)

### Sprint 4 (Week 7-8): Configuration, Testing & Documentation
- Phase 7: Configuration & Environment Setup
- Phase 8: Testing & Validation (parallel)
- Phase 9: Documentation & Knowledge Transfer

---

## SUCCESS CRITERIA & ACCEPTANCE TESTS

### Functional Acceptance
- ✅ End-to-end workflow executes successfully
- ✅ Multi-agent DAG produces deterministic results
- ✅ Validation agent correctly rejects invalid requisitions
- ✅ Scoring incorporates all seven weight components
- ✅ Ranking generates narrative justifications
- ✅ All results are explainable and auditable

### Non-Functional Acceptance
- ✅ All LLM calls tracked and cost computed
- ✅ Average workflow latency < 30 seconds
- ✅ Database queries optimized with proper indexing
- ✅ Retry logic handles 429 rate limit responses
- ✅ Partial failures don't cascade system-wide
- ✅ pgvector queries perform < 500ms for 10k candidates

### Quality Acceptance
- ✅ Test coverage > 80%
- ✅ Zero TODOs or placeholders
- ✅ All prompts externalized and versioned
- ✅ All configuration ENV-driven
- ✅ All agents independently testable
- ✅ Documentation comprehensive and current

### Operational Acceptance
- ✅ Cost reports accurate and auditable
- ✅ Observability logs complete and searchable
- ✅ Configuration validation on startup
- ✅ Database migrations reversible
- ✅ Runbooks document common operations

---

## RISK MITIGATION

### Technical Risks
| Risk | Mitigation |
|------|-----------|
| pgvector performance at scale | Indexing strategy, load testing, dimension optimization |
| LLM cost explosion | Governance logging, rate limiting, cost alerts |
| DAG deadlocks | Strict validation, state machine testing, timeout policies |
| Embedding quality | Quality metrics, sampling validation, model testing |
| Database schema evolution | Versioned migrations, rollback testing |

### Integration Risks
| Risk | Mitigation |
|------|-----------|
| Breaking existing APIs | Backward compatibility testing, feature flags |
| Data migration issues | Dry-run procedures, validation checksums |
| Performance regression | Baseline metrics, CI/CD performance gates |

---

## DELIVERABLES CHECKLIST

- [ ] Phase 1: Database migrations and seed data
- [ ] Phase 2: All seven agent implementations with tests
- [ ] Phase 3: LLM governance and cost tracking
- [ ] Phase 4: Prompt files in `/prompts/*.py`
- [ ] Phase 5: LangGraph DAG with full orchestration
- [ ] Phase 6: API endpoints and service integration
- [ ] Phase 7: `.env.example` and config validation
- [ ] Phase 8: Comprehensive test suite with >80% coverage
- [ ] Phase 9: Complete documentation and runbooks

---

## Document Metadata

| Property | Value |
|----------|-------|
| Version | 1.0 |
| Status | PLANNING |
| Purpose | SpecKit Plan for Multi-Agent Enhancement |
| Last Updated | 2026-02-03 |
| Audience | Engineering Team |
| Scope | Full system enhancement with 9 implementation phases |

