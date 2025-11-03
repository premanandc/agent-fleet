# Router Agent

The Router Agent is an intelligent orchestrator for the ITEP (IT Engineering Productivity) Agentic AI Platform. It receives complex user requests, breaks them into tasks, and coordinates specialized agents to handle them.

## Architecture

The Router Agent implements a capability-driven architecture with the following components:

1. **Guardrails** - Validates requests are on-topic for ITEP
2. **Task Breakdown** - Decomposes requests into actionable tasks
3. **Orchestrator** - Executes tasks via A2A protocol (parallel or sequential)
4. **Summarizer** - Aggregates results into coherent responses
5. **Agent Registry** - Discovers available agents and their capabilities

See [docs/router-agent.md](docs/router-agent.md) for complete architecture documentation.

## Components

### State Model (`src/models/router_state.py`)

Defines the state schema that flows through all nodes:

- `RouterState` - Main state with A2A-compatible `messages` field
- `Task` - Individual task with agent assignment, status, and results
- `Plan` - Execution plan with tasks and strategy
- `AgentCapability` - Agent metadata from agent cards

### Nodes (`src/nodes/`)

Seven nodes implement the Router's workflow:

1. **validate_request** - LLM-based validation against ITEP scope
2. **reject_request** - Formats rejection message for off-topic requests
3. **generate_plan** - LLM-based task decomposition with capability matching
4. **await_approval** - Human-in-the-loop plan approval (interactive/review modes)
5. **execute_tasks** - A2A invocation with parallel/sequential execution
6. **analyze_results** - LLM-based evaluation of result sufficiency
7. **aggregate_results** - LLM-based synthesis of final response

### Graph Assembly (`src/agents/router_agent.py`)

The `create_router_graph()` factory function:

- Discovers agents from LangGraph Server at startup
- Assembles StateGraph with conditional edges
- Configures interrupts for interactive mode
- Returns compiled graph with persistence

## Usage

### Running with LangGraph Server

1. **Start LangGraph Server:**

```bash
langgraph dev
```

2. **Access the Router Agent:**

The Router is automatically exposed as an A2A-compatible assistant at:
- Graph ID: `router`
- A2A endpoint: `http://localhost:2024/a2a/{assistant_id}`

3. **Invoke via API:**

```bash
curl -X POST http://localhost:2024/a2a/{assistant_id} \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {"role": "user", "content": "Fix the SonarQube violations in my code"}
      ]
    },
    "config": {
      "configurable": {
        "thread_id": "user-session-123",
        "mode": "auto"
      }
    }
  }'
```

### Execution Modes

The Router supports three execution modes:

- **`auto`** (default): Fully autonomous - validates, plans, executes, aggregates
- **`interactive`**: Pauses for user approval before execution using LangGraph interrupts
- **`review`**: Shows plan but auto-approves (for transparency without blocking)

Specify mode in config:

```python
config = {
    "configurable": {
        "mode": "interactive",  # or "auto", "review"
        "thread_id": "session-123"
    }
}
```

### Programmatic Usage

```python
from src.agents.router_agent import create_router_graph, create_initial_state

# Create graph
graph = create_router_graph()

# Create initial state
state = create_initial_state(
    "Fix the SonarQube violations in my code",
    mode="auto",
    max_replans=2
)

# Execute
result = graph.invoke(
    state,
    config={
        "configurable": {
            "agent_registry": graph.agent_registry,
            "thread_id": "session-123"
        }
    }
)

# Access final response
print(result["final_response"])
```

## Agent Discovery

The Router discovers available agents at startup by:

1. Calling `POST /assistants/search` to list all assistants
2. Fetching each agent's card via `GET /a2a/{agent_id}/card`
3. Building a registry of `agent_id → AgentCapability`

Agent cards must declare:
- `capabilities`: High-level domains (e.g., "code-quality", "ci-cd")
- `skills`: Specific tasks (e.g., "Fix SonarQube violations")
- `description`: Agent purpose

## Configuration

### Environment Variables

```bash
# LLM Configuration
LLM_PROVIDER=anthropic          # or "openai"
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-...

# LangGraph Server
LANGGRAPH_SERVER_URL=http://localhost:2024
```

### LangGraph Configuration (`langgraph.json`)

```json
{
  "dependencies": ["."],
  "graphs": {
    "router": "./src/agents/router_agent.py:create_router_graph"
  },
  "env": ".env"
}
```

## Testing

### Run Unit Tests

```bash
pytest tests/unit/ -v
```

Tests individual nodes with mocked dependencies.

### Run Integration Tests

```bash
pytest tests/integration/ -v
```

Tests complete graph flows with mocked LLM and A2A calls.

### Run All Tests

```bash
pytest -v
```

## Key Features

### Capability-Driven Routing

Tasks are matched to agents based on declared capabilities, not hardcoded logic:

```python
# LLM analyzes user request and agent capabilities
# Selects best-fit agent for each task
plan = {
    "tasks": [
        {
            "description": "Fix SonarQube violations",
            "agent_id": "coda-agent",
            "rationale": "Coda specializes in SonarQube remediation"
        }
    ]
}
```

### Automatic Replanning

If task results are insufficient, the Router can replan:

1. Analyze results with LLM
2. If insufficient, trigger replan (max 2 attempts by default)
3. Generate new plan with additional/different tasks
4. Execute and re-evaluate

### Parallel Execution

Tasks without dependencies execute in parallel:

```python
plan = {
    "execution_strategy": "parallel",
    "tasks": [
        {"id": "task-1", "dependencies": []},    # Runs immediately
        {"id": "task-2", "dependencies": []},    # Runs in parallel
        {"id": "task-3", "dependencies": ["task-1", "task-2"]}  # Waits
    ]
}
```

### Human-in-the-Loop

Interactive mode pauses for approval:

```python
# Configure interactive mode
state = create_initial_state("Fix bugs", mode="interactive")

# Graph pauses at await_approval node
# User can approve, reject, or request modifications
# Execution resumes based on response
```

## Troubleshooting

### No Agents Discovered

**Symptom:** Empty plan with "No agents available"

**Solutions:**
- Ensure LangGraph Server is running
- Check `LANGGRAPH_SERVER_URL` is correct
- Verify other agents are deployed and have A2A cards

### Tasks Fail with Timeout

**Symptom:** Tasks marked as "failed" with timeout error

**Solutions:**
- Increase timeout in `execute.py` (default: 5 minutes)
- Check subordinate agent is responding
- Verify A2A endpoint is accessible

### Validation Rejects Valid Requests

**Symptom:** On-topic requests marked as invalid

**Solutions:**
- Review validation prompt in `validate.py`
- Adjust ITEP scope definition
- Check LLM temperature (should be low ~0.3)

## Next Steps

1. **Deploy Additional Agents** - Coda, AskCody, etc.
2. **Configure Agent Cards** - Ensure accurate capability declarations
3. **Test End-to-End** - With live LangGraph Server and real subordinates
4. **Monitor Performance** - Track task success rates, replanning frequency
5. **Iterate on Prompts** - Refine planning, analysis, aggregation prompts

## Architecture Documentation

For complete architecture details, C4 diagrams, and design decisions, see:

- [Router Agent Architecture](docs/router-agent.md)
- [Structurizr DSL](docs/router-agent.dsl)
