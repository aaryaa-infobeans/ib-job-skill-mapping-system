# AI & LangGraph Overview

## 1. Purpose
This document provides a high-level overview of the AI-driven components of the system and the use of LangGraph as the orchestration framework.

## 2. Role of AI
The system leverages AI, specifically Large Language Models (LLMs) via a series of coordinated agents, to perform tasks that require natural language understanding. The primary goal is to transform unstructured job requisition text into a structured format that can be used for deterministic matching against a database of team member profiles.

## 3. LangGraph Orchestration
- **Why LangGraph?**: LangGraph is chosen as the framework to build the AI agentic pipeline because it provides:
  - **State Management**: It maintains a persistent state across multiple steps, allowing agents to build upon each other's work.
  - **Graph Topology**: It allows for the definition of a clear, directed graph of operations, making the process transparent and debuggable.
  - **Resilience**: It supports checkpoints, which are crucial for auditing (FR-6.2) and for potential resumption of failed or long-running processes.
  - **Flexibility**: It allows for the integration of both LLM-based nodes and standard Python function nodes, enabling deterministic logic to be mixed with language-based tasks.

## 4. Core Principle: Deterministic Logic over LLM Judgement
- A fundamental principle of this system is that LLMs are used for **language tasks only** (parsing, summarization, normalization, explanation).
- LLMs **MUST NOT** be used for:
  - Mathematical calculations (e.g., calculating experience).
  - Scoring or ranking of candidates.
  - Evaluating availability.
- All core matching and scoring logic is implemented in deterministic, auditable code that operates on the structured data produced by the initial AI parsing stages. This ensures fairness, repeatability, and explainability of the final results.
