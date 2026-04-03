# Cowork Folder Instructions — Job Requisition & Skill Mapping System (Project ReqMatch)

> **Paste these into:** Settings → Cowork → Folder Instructions (for the project folder)
> **Or:** Save as `CLAUDE.md` in the root of the project folder

---

## Project Context

This is a **brownfield** AI-powered Job Requisition & Skill Mapping System. It is already in production/active development — not a greenfield build. Every instruction below assumes existing code, existing data, existing integrations, and existing technical debt.

### What the System Does
1. Clients or internal teams submit a job requisition (job title, required skills, duration, etc.) via a REST API
2. AI agents parse and normalize the job description (multi-agent architecture)
3. The system matches requisitions against internal team member profiles — evaluating skill fit, experience, and current availability
4. Returns a ranked list of best-fit candidates with confidence scores and plain-language reasoning

### Architecture Overview (Update as needed)
- **Architecture style:** Multi-agent system with orchestrator pattern
- **Core agents:**
  - JD Parser Agent — extracts and normalizes skills, experience levels, role requirements from raw job descriptions
  - Profile Enrichment Agent — keeps team member profiles current (skills, certifications, project history, availability)
  - Matching Agent — scores candidate-requisition fit using weighted skill overlap, experience relevance, and availability
  - Reasoning Agent — generates plain-language explanations for each recommendation
- **API layer:** REST API (FastAPI / Node.js — confirm in codebase)
- **Data stores:** Team member profiles DB, skills taxonomy/ontology, requisition history
- **LLM integration:** Used by parser and reasoning agents (model, provider, and prompt templates in codebase)
- **Deployment:** (Update: cloud provider, container orchestration, CI/CD pipeline details)

---

## Brownfield Rules — CRITICAL

These rules exist because this is an active system with real users and real data. Claude must follow them strictly.

### 1. Understand Before You Change
- Before modifying ANY file, read it completely. Then read files that import it or are imported by it.
- Before suggesting an architecture change, map out what currently depends on the component you want to change.
- Never assume a function is unused. Search for all references before recommending removal.
- If a piece of code looks wrong or redundant, it might be a workaround for a known issue. Ask me before "fixing" it.

### 2. Preserve What Works
- Never refactor working code unless I explicitly ask for it. "Improving" stable code introduces risk.
- Do not change API contracts (request/response schemas) without flagging it as a breaking change.
- Do not alter database schemas, even "small" column additions, without showing me the migration plan and rollback strategy.
- Do not change agent prompt templates without showing me a before/after comparison and explaining the impact on output quality.
- Preserve all existing error handling, logging, and monitoring hooks — even if they look verbose.

### 3. Respect the Dependency Chain
- Agent orchestration order matters. Never reorder agent execution without my approval.
- Skill taxonomy/ontology changes cascade everywhere — matching logic, scoring weights, profile normalization. Flag any taxonomy change as high-risk.
- LLM model or provider changes require evaluation against the existing test suite and benchmark scores before any recommendation.

### 4. Technical Debt Awareness
- This system has technical debt. That's expected. Don't try to fix all of it in every task.
- If you encounter tech debt while working on something else, note it separately (add to `TECH-DEBT.md` in the project folder) but don't fix it unless that's the task.
- When I ask you to add a feature, implement it in a way that works with the current architecture — not the ideal architecture. Flag the gap if it matters.

---

## My Role on This Project

I am the **Technical Architect** owning this system. My responsibilities:
- Architectural decisions and technical direction
- Code review standards and quality gates
- Agent design — prompt engineering, orchestration logic, evaluation criteria
- API contract design and versioning
- Performance, reliability, and scaling decisions
- Technical documentation and knowledge transfer
- Sprint planning from a technical perspective
- Presales support — effort estimation and technical solutioning for enhancements

---

## Task-Specific Instructions

### When Writing Status Reports & Client Docs

**Weekly Status Reports:**
- Use this structure: Summary → Completed This Week → In Progress → Planned Next Week → Risks & Blockers → Decisions Needed
- Always quantify progress (e.g., "4 of 7 API endpoints migrated" not "good progress on APIs")
- For AI/agent-related updates, translate technical details into business impact (e.g., "Matching accuracy improved from 74% to 82% on the benchmark set" not "adjusted embedding similarity threshold")
- Flag any changes to scope, timeline, or architecture as a separate callout — never bury them in the body
- Include a confidence level for the overall delivery timeline: On Track / At Risk / Delayed

**Technical Design Documents:**
- Start with the problem statement and business context — not the solution
- Include a "Current State" section before "Proposed Changes" — the reader needs to understand what exists
- For agent changes: document current prompt → proposed prompt → expected behavior change → evaluation plan
- For API changes: document current contract → proposed contract → migration path → backward compatibility plan
- Always include a "Risks & Rollback" section
- Use architecture diagrams (Mermaid format is fine) for any cross-component changes

**Client-Facing Documents:**
- Never expose internal agent names, LLM provider details, or prompt strategies
- Describe AI capabilities in terms of outcomes: "The system analyzes job requirements and identifies best-fit candidates" not "GPT-4 parses the JD and a vector similarity search ranks profiles"
- Always include data privacy and accuracy disclaimers where relevant
- Match the voice in my-voice.md — professional, structured, solution-oriented

### When Doing Code Review & Technical Documentation

**Code Review Assistance:**
- When I share code for review, check for:
  - Breaking changes to API contracts or agent interfaces
  - Missing error handling (especially around LLM API calls — these fail unpredictably)
  - Hardcoded values that should be configurable (model names, thresholds, weights)
  - Missing or inadequate logging (every agent decision should be traceable)
  - Security issues: prompt injection vectors, PII leakage in logs, unsanitized inputs
  - Performance: unnecessary sequential calls that could be parallel, missing caching opportunities
  - Test coverage: are edge cases covered? What about LLM response variability?
- Don't nitpick style unless it affects readability. We have linters for that.
- For agent-related code: verify that prompt templates are externalized, not inline

**Technical Documentation:**
- API docs: follow OpenAPI/Swagger format. Include request/response examples with realistic data.
- Agent documentation: for each agent, document Purpose → Input → Processing Logic → Output → Error Handling → Dependencies → Known Limitations
- Architecture docs: keep them updated as a living document, not a one-time artifact
- Runbooks: for every operational procedure, include Prerequisites → Steps → Verification → Rollback → Escalation path
- Use code snippets and real examples. No abstract descriptions of things that exist in the codebase.

### When Helping with Sprint Planning & Delivery Tracking

**Sprint Planning:**
- When I describe upcoming work, help me break it into stories with:
  - Clear acceptance criteria (testable, specific)
  - Technical subtasks (don't just say "implement" — break into: design, implement, test, document, deploy)
  - Dependency mapping (which stories block which)
  - Effort estimates in story points or t-shirt sizes — always flag if a story feels too large (>8 points = should be split)
- For AI/agent stories, always include an "Evaluation" subtask — we need to measure output quality, not just "does it run"
- Flag stories that touch the skill taxonomy, agent prompts, or scoring logic as requiring my review before implementation

**Delivery Tracking:**
- Help me maintain a sprint burndown view: total planned vs completed vs remaining vs blocked
- When preparing for standups or reviews, summarize by workstream: API, Agents, Data, Infrastructure
- Track technical risks separately from delivery risks
- For any slippage, always note: original estimate → current estimate → reason → mitigation

**Capacity & Resource Planning:**
- When I share team allocation data, help me identify: overloaded team members, skill gaps for upcoming work, single points of failure (one person owns a critical component)
- For AI-specific work (prompt engineering, agent tuning, evaluation), flag that these tasks take longer than typical development — they involve experimentation, not just implementation

---

## File & Folder Conventions

```
PROJECT ROOT/
├── CLAUDE.md                    ← (this file — project instructions for Cowork)
├── TECH-DEBT.md                 ← Running log of technical debt items
├── docs/
│   ├── architecture/            ← System design docs, diagrams
│   ├── api/                     ← API specifications, contract docs
│   ├── agents/                  ← Agent design docs, prompt templates
│   ├── runbooks/                ← Operational procedures
│   └── decisions/               ← Architecture Decision Records (ADRs)
├── reports/
│   ├── weekly/                  ← Weekly status reports
│   ├── sprint/                  ← Sprint review summaries
│   └── reviews/                 ← Monthly/quarterly business reviews
├── planning/
│   ├── backlog/                 ← Story breakdowns, roadmap
│   └── estimates/               ← Effort estimates, resource plans
└── outputs/                     ← Claude's finished deliverables go here
```

- Follow this structure. Don't create files outside of it without asking.
- Weekly reports: name as `weekly-status-YYYY-MM-DD.docx`
- ADRs: name as `ADR-NNN-short-title.md` (e.g., `ADR-003-switch-to-async-matching.md`)
- Sprint docs: name as `sprint-NN-review.docx`

---

## Domain Glossary

Use these terms consistently. Don't invent synonyms.

| Term | Meaning |
|------|---------|
| Requisition / Req | A job requisition submitted via the API |
| JD | Job Description — the raw text input in a requisition |
| Profile | An internal team member's skill/experience/availability record |
| Skill Taxonomy | The normalized hierarchy of skills the system recognizes |
| Confidence Score | 0–100 numeric score indicating match quality between a req and a profile |
| Reasoning | Plain-language explanation of why a candidate was recommended |
| Agent | An autonomous AI component in the multi-agent pipeline |
| Orchestrator | The component that coordinates agent execution order and data flow |
| Benchmark Set | The curated set of req-profile pairs used to evaluate matching quality |
| Availability Window | The time range a team member is available for a new engagement |

---

## What I Don't Want Claude Doing on This Project

- Don't suggest rewriting the system in a different language or framework unless I ask for a migration assessment
- Don't recommend replacing the multi-agent architecture with a single monolithic LLM call — the agent separation exists for observability, testability, and modularity
- Don't suggest "just use [hot new AI framework]" — any tool change needs evaluation against our requirements, not hype
- Don't generate synthetic team member profiles or fake requisition data without my approval — we have real test data
- Don't optimize agent prompts without showing me the current prompt first and explaining what you'd change and why
- Don't summarize or skip over error scenarios — in production AI systems, error handling IS the feature
