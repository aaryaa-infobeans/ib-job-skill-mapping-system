# LangSmith Tracing & Observability Specification

This document defines the technical standards and operational configuration for LangSmith integration within the JD–Skill Mapping system. LangSmith serves as the centralized observability layer, providing deep visibility into the execution of LLM agents and the LangGraph orchestration pipeline.

## 1. Overview
LangSmith is integrated to provide a production-grade observability stack for the application's AI components. Its primary role is to serve as the system of record for every LLM interaction, enabling:
- **Trace Visibility**: End-to-end mapping of complex agentic workflows.
- **Root Cause Analysis**: Rapid debugging of failed or suboptimal LLM responses.
- **Performance Monitoring**: Real-time tracking of latency and reliability.
- **Cost Management**: Granular observability of token consumption and associated expenditure.

## 2. Tracing Requirements

To maintain high standards of observability, the following tracing requirements are mandatory:

- **Prompt Visibility**  
  Every prompt sent to the LLM must be captured in its entirety. This includes system messages, few-shot examples, and dynamic user inputs. Traces must allow architects to review the exact state of the prompt at the moment of execution.

- **Output Tracing**  
  All responses from the LLM, including those in structured JSON formats, must be recorded. This ensures that parsing logic can be validated against the raw model output.

- **Usage & Cost Tracking**  
  Every LLM interaction must record:
  - Prompt tokens
  - Completion tokens
  - Total tokens
  - Estimated cost (USD) based on defined model pricing.

- **Contextual Correlation**  
  Every trace must be decorated with specific application-level identifiers to allow for cross-referencing with application logs and database records:
  - `correlation_id`: Links the AI trace to a specific job requisition processing lifecycle.
  - `request_id`: Identifies the unique API request that triggered the execution.

- **Global Enablement**  
  The tracing infrastructure must be switchable via environment-level flags. The application must be capable of running in "headless" mode (without LangSmith) for local development or in environments where external tracing is not required.

## 3. LangSmith Integration Design

### 3.1 Automatic Tracing Enablement
The system utilizes LangSmith's **Tracing V2** protocol. Tracing is enabled globally at the runtime level via the `LANGCHAIN_TRACING_V2` environment variable. 
- When enabled, the LangChain library automatically intercepts calls to the LLM and records them as spans within a trace.
- When disabled (or if the API key is missing), the application reverts to local logging only, ensuring no performance penalty or failure occurs due to observability gaps.

### 3.2 Trace Metadata & Tags
Consistent metadata and tagging are critical for filtering and aggregating traces in the LangSmith dashboard.

**Required Metadata Fields:**
- `correlation_id`: The unique ID generated for the requisition processing job.
- `request_id`: The ID of the incoming FastAPI request.
- `model_name`: The specific version or alias of the LLM being invoked (e.g., `gpt-4`, `gpt-4o-mini`).

**Standardized Trace Tags:**
- `requisition_processing`: Applied to the entire high-level workflow.
- `jd_skill_mapping`: Identifies traces related to the core matching feature.
- `matching_engine`: Specifically pins traces to the scoring and ranking stage.

### 3.3 Unified Trace Scope
To ensure a clean observability experience, all LLM calls triggered by a single requisition request must appear under a **Unified Trace Scope**.
- **Context Propagation**: The system uses `tracing_v2_enabled` contexts to wrap background processing tasks.
- **Breadcrumb Structure**: In the LangSmith UI, this results in a parent "Requisition Processing" span, with child spans for each agent node (Parsing, Normalization, Validation, Scoring) and their respective LLM calls.

## 4. Environment Configuration

The following variables manage the LangSmith integration and must be present in the environment for tracing to function:

| Variable | Description | Recommended Value |
| :--- | :--- | :--- |
| `LANGCHAIN_TRACING_V2` | Master switch for tracing enablement. | `true` |
| `LANGCHAIN_API_KEY` | Authentication key for the LangSmith service. | `ls__...` |
| `LANGCHAIN_PROJECT` | The dashboard project where traces are sent. | `jd-skill-mapping-[env]` |
| `LANGCHAIN_ENDPOINT` | The API endpoint for LangSmith. | `https://api.smith.langchain.com` |

### Environment Separation
To avoid data contamination, distinct projects must be used across environments:
- **Development**: `jd-skill-mapping-dev`
- **Staging**: `jd-skill-mapping-staging`
- **Production**: `jd-skill-mapping-prod`

## 5. Security & Privacy Considerations

As LangSmith captures potentially sensitive prompt and output data, the following security measures are required:

- **PII Protection**: Engineers should avoid sending highly sensitive personally identifiable information (PII) in prompts. Where necessary, data should be masked or pseudonymized.
- **Redaction**: Future iterations of the stack should include custom `TraceProcessors` to redact sensitive fields before transmission to the cloud.
- **Access Control**: Access to the LangSmith dashboard is restricted to authorized engineers and architects via SSO or restricted API keys.
- **Project Isolation**: Production API keys must never be used in development environments.

## 6. Operational Guidelines

### Debugging Workflows
- **Trace Inspection**: When a match result is queried, developers should use the `correlation_id` to find the exact trace in LangSmith to verify why a candidate was ranked in a particular way.
- **Latency Analysis**: Use the LangSmith "Monitor" tab to identify which agent node is contributing most to overall latency.

### Incident Analysis
In the event of a system-wide degradation, LangSmith allows for:
- **Model Regression Detection**: Compare traces from different model versions.
- **Failure Clustering**: Identify if errors are occurring in a specific parsing logic or due to LLM rate limits.
- **Cost Auditing**: Reconcile monthly OpenAI invoices against captured usage metrics in LangSmith.
