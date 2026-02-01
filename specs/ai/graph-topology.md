# LangGraph Graph Topology

## 1. Purpose
This document defines the structure of the LangGraph execution graph, outlining the nodes and edges that orchestrate the AI agent pipeline.

## 2. Graph Visualization (Conceptual)
```
[START]
   |
   v
[JD_Parsing_Agent]
   |
   v
[Skill_Normalization_Agent]
   |
   v
[Availability_Evaluation_Agent] --> (Deterministic, non-LLM)
   |
   v
[Matching_Scoring_Agent] --> (Deterministic, non-LLM)
   |
   v
[Explanation_Generation_Agent]
   |
   v
[Result_Aggregation_Agent]
   |
   v
[END]
```

## 3. Node Descriptions

### 3.1. `JD_Parsing_Agent`
- **Purpose**: To parse the raw `jd_text` from the requisition and structure the key components.
- **Type**: LLM-based.

### 3.2. `Skill_Normalization_Agent`
- **Purpose**: To take the skills extracted by the parsing agent and map them to the canonical `skill_master` dictionary.
- **Type**: LLM-based, potentially with a fuzzy matching fallback.

### 3.3. `Availability_Evaluation_Agent`
- **Purpose**: To retrieve team member allocation data from the database and determine who is available for the given requisition timeframe.
- **Type**: Deterministic Python function. **This is NOT an LLM agent.**

### 3.4. `Matching_Scoring_Agent`
- **Purpose**: To execute the core matching and scoring algorithm based on skills, experience, and other criteria.
- **Type**: Deterministic Python function. **This is NOT an LLM agent.**

### 3.5. `Explanation_Generation_Agent`
- **Purpose**: To generate human-readable text explaining *why* a candidate is a good match, based on the deterministic output of the scoring agent.
- **Type**: LLM-based.

### 3.6. `Result_Aggregation_Agent`
- **Purpose**: To format the final ranked list of candidates and their explanations into the structure required for the API response (FR-2).
- **Type**: Deterministic Python function.

## 4. Edges and State Flow
- The graph is a simple, linear sequence. Each node takes the current graph state as input, performs its function, and mutates the state for the next node.
- The state object is progressively enriched at each step. For example, `JD_Parsing_Agent` adds the structured JD to the state, and `Skill_Normalization_Agent` replaces the raw skill strings in the state with their canonical IDs.
- The `langgraph_checkpoints` table (see Audit Model) will store a snapshot of the state after each node completes, providing full visibility into the process.
