# Agent Authoring Guide

How to create, configure, and deploy a new agent in the IB Job Skill Mapping System.

## Quick Start — Create a New Agent in 5 Steps

### 1. Create the Agent Class

```python
# src/app/agent_framework/agents/my_new_agent.py

from __future__ import annotations
from typing import Any, AsyncIterator, Dict
from pydantic import BaseModel
from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.registry import AgentRegistry


class MyInput(BaseModel):
    request_id: str
    correlation_id: str
    data: str


class MyOutput(BaseModel):
    request_id: str
    correlation_id: str
    result: str


@AgentRegistry.register
class MyNewAgent(BaseAgent):
    agent_id = "my_new_agent"
    version = "1.0.0"
    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "threshold": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        self._threshold = config.get("threshold", 0.5)
        self._log.info("MyNewAgent ready (threshold=%.2f)", self._threshold)

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()
        inp = MyInput.model_validate(message.payload)

        # Your business logic here
        result = f"Processed: {inp.data}"

        output = MyOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            result=result,
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="my_new_agent.complete",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(self.agent_id, self.version, "Not initialized")
        return HealthStatus.ok(self.agent_id, self.version,
                               uptime_s=round(self.uptime_seconds, 1))

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
```

### 2. Add Config to `agents.yaml`

```yaml
agents:
  - id: my_new_agent
    type: my_new_agent
    enabled: true
    version: ">=1.0.0"
    config:
      threshold: 0.7
    retry:
      max_attempts: 2
      backoff: exponential
      backoff_ms: 500
    timeout_ms: 15000
```

### 3. Add Routing Rules

```yaml
routing:
  # ... existing routes ...
  - from: some_upstream_agent
    to: my_new_agent
  - from: my_new_agent
    to: some_downstream_agent
```

### 4. Import the Module

Add an import in `src/app/agent_framework/agents/__init__.py`:

```python
import app.agent_framework.agents.my_new_agent  # noqa: F401
```

### 5. Write Tests

```python
@pytest.mark.asyncio
async def test_my_agent_handle():
    cls = AgentRegistry.resolve("my_new_agent")
    agent = cls()
    await agent.initialize({"threshold": 0.7})

    msg = Message.create(
        payload={"request_id": "r", "correlation_id": "c", "data": "test"},
        metadata=MessageMetadata(
            source_agent="test", message_type="test.input",
            correlation_id="c", request_id="r",
        ),
    )

    results = []
    async for out in agent.handle(msg):
        results.append(out)

    assert len(results) == 1
    assert results[0].metadata.message_type == "my_new_agent.complete"
    assert results[0].trace_id == msg.trace_id
```

## BaseAgent Contract

Every agent must implement:

| Method | Purpose |
|--------|---------|
| `initialize(config)` | Called once at startup. Receive your scoped config dict. |
| `handle(message)` | Process a message. Yield zero or more output messages. |
| `health_check()` | Return `HealthStatus.ok()`, `.degraded()`, or `.unavailable()`. |
| `shutdown(graceful)` | Clean up resources. |

Required class attributes:

| Attribute | Type | Example |
|-----------|------|---------|
| `agent_id` | `str` | `"my_new_agent"` |
| `version` | `str` | `"1.0.0"` (semver) |
| `config_schema` | `Dict` | JSON Schema for your config block |

## Key Rules

1. **Always propagate `trace_id`**: Pass `trace_id=message.trace_id` to `Message.create()`.
2. **Always call `self._assert_initialized()`** at the top of `handle()`.
3. **Use Pydantic models** for input/output validation.
4. **Yield messages** — `handle()` is an async generator, not a regular function.
5. **Health checks should be fast** — they're called every few seconds.
6. **Config is injected** — never import `settings.py` directly.

## Conditional Routing

Route messages based on `message_type`:

```yaml
routing:
  - from: pii_scrubber
    to: requisition_parsing
    condition: "$.metadata.message_type == 'requisition.scrubbed'"
  - from: pii_scrubber
    to: __dead_letter__
    condition: "$.metadata.message_type == 'requisition.pii_blocked'"
```

## Special Routing Destinations

| Destination | Meaning |
|-------------|---------|
| `__sink__` | End of pipeline — resolves the caller's `process()` Future |
| `__dead_letter__` | Failed message — stored in DLQ, caller Future fails |

## Feature Flags

Disable an agent without removing it:

```yaml
agents:
  - id: my_new_agent
    enabled: false   # Agent won't start; routes to it are skipped
```

Hot-swap at runtime via `HotSwapManager.apply_config_update()`.

## Observability

Your agent automatically gets:
- Prometheus counters: `agent_framework_messages_total{agent_id="my_new_agent", status="success|failure|timeout"}`
- Prometheus histogram: `agent_framework_message_duration_seconds{agent_id="my_new_agent"}`
- OpenTelemetry spans (if OTLP configured): `agent.my_new_agent`
- Structured JSON logs with `trace_id` and `correlation_id`

## Strangler-Fig Migration Pattern

To wrap existing brownfield code:

```python
async def handle(self, message: Message) -> AsyncIterator[Message]:
    self._assert_initialized()
    inp = MyInput.model_validate(message.payload)

    # Build the state dict the brownfield function expects
    state = {"requisition_input": {...}, "error_message": None}

    # Delegate to brownfield (deferred import to avoid circular deps)
    from app.ai.agents.my_old_module import my_old_function
    updated_state = my_old_function(state)

    # Convert brownfield output back to typed Message
    output = MyOutput(...)
    yield Message.create(payload=output.model_dump(), ...)
```

Use deferred imports (`from ... import ...` inside `handle()`) so brownfield modules are only loaded when actually called.
