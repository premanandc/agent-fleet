# Agent Fleet

A multi-agent orchestration system for the ITEP (IT Engineering Productivity) platform, featuring a Router Agent that intelligently delegates tasks to specialized subordinate agents using the A2A (Agent-to-Agent) protocol.

## Features

- **Router Agent**: Orchestrates and delegates tasks based on capabilities
- **Multi-Agent Architecture**: QuickAgent for fast tasks, SlowAgent for deep analysis
- **A2A Protocol**: Full Agent-to-Agent protocol support via LangGraph Server
- **Dynamic Discovery**: Automatic agent detection via A2A agent cards
- **Capability-Driven Routing**: Automatic agent selection based on skills and requirements
- **LLM Provider Agnostic**: Supports both OpenAI and Anthropic models
- **Execution Modes**: Auto, interactive, and review modes for different workflows
- **Task Dependencies**: Support for sequential and parallel task execution
- **Human-in-the-Loop**: Optional approval workflows for interactive mode

## Quick Start

### 1. Install Dependencies

```bash
uv sync --all-groups
```

### 2. Configure API Keys

Create a `.env` file with your API keys:

```bash
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional
```

You need at least `ANTHROPIC_API_KEY` for the default configuration.

### 3. Start the LangGraph Server

```bash
uv run langgraph dev --no-browser
```

The server will start on `http://localhost:2024` with:
- API Documentation: `http://localhost:2024/docs`
- A2A endpoints: `http://localhost:2024/a2a/{assistant_id}`
- Health check: `http://localhost:2024/ok`

### 4. Test the Router

```bash
python test_router_simple.py       # Quick test
python test_router_complete.py     # Complete test suite
```

## Project Structure

```
agent-fleet/
├── src/
│   ├── llm/
│   │   └── factory.py              # LLM provider factory
│   ├── models/
│   │   └── router_state.py         # State definitions
│   ├── utils/
│   │   └── discovery.py            # Agent discovery utilities
│   ├── nodes/
│   │   ├── validate.py             # Request validation (guardrails)
│   │   ├── reject.py               # Rejection handler
│   │   ├── plan.py                 # Task planning and decomposition
│   │   ├── approval.py             # Human-in-the-loop approval
│   │   ├── execute.py              # Task execution via A2A
│   │   ├── analyze.py              # Result sufficiency analysis
│   │   └── aggregate.py            # Final response aggregation
│   └── agents/
│       ├── router_agent.py         # Main Router Agent
│       ├── quick_agent.py          # Fast task agent (1-2s)
│       ├── slow_agent.py           # Deep analysis agent (5-10s)
│       └── cards.py                # Agent card registry
├── test_router_simple.py           # Simple Router test
├── test_router_complete.py         # Complete test suite
├── test_client.py                  # Manual client for testing
├── langgraph.json                  # LangGraph Server configuration
├── pyproject.toml                  # Dependencies
└── .env                            # API keys
```

## Available Agents

The system includes these agents (registered in `langgraph.json`):

### Router Agent (`router`)
- **Purpose**: Orchestrates and delegates tasks
- **Capabilities**: Task planning, agent coordination, result aggregation
- **Response time**: Depends on delegated agents

### QuickAgent (`quick_agent`)
- **Purpose**: Fast operations (syntax checks, quick validation)
- **Capabilities**: `analysis`, `quick-check`, `validation`
- **Response time**: 1-2 seconds
- **A2A Endpoint**: `/a2a/{assistant_id}`

### SlowAgent (`slow_agent`)
- **Purpose**: Deep analysis (SonarQube fixes, comprehensive reviews)
- **Capabilities**: `deep-analysis`, `remediation`, `sonarqube`
- **Response time**: 5-10 seconds
- **A2A Endpoint**: `/a2a/{assistant_id}`

## Execution Modes

Configure via `config.configurable.mode`:

- **`auto`** (default): Fully autonomous, no approval needed
- **`interactive`**: Pauses for plan approval before execution
- **`review`**: Shows plan but auto-approves (transparency without blocking)

## Usage Examples

### Using the SDK

```python
import asyncio
from langgraph_sdk import get_client

async def test_router():
    client = get_client(url="http://localhost:2024")

    result = await client.runs.wait(
        None,  # Threadless run
        "router",  # Assistant ID
        input={
            "messages": [{
                "role": "user",
                "content": "Quick check my code for syntax errors"
            }]
        },
        config={
            "configurable": {
                "mode": "auto"  # or "interactive", "review"
            }
        }
    )

    print(result["final_response"])

asyncio.run(test_router())
```

### Using curl

```bash
curl -X POST http://localhost:2024/runs/wait \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "router",
    "input": {
      "messages": [
        {"role": "user", "content": "Fix SonarQube violations"}
      ]
    },
    "config": {
      "configurable": {"mode": "auto"}
    }
  }'
```

### Streaming Results

```python
from langgraph_sdk import get_client

async def stream_test():
    client = get_client(url="http://localhost:2024")

    async for chunk in client.runs.stream(
        None,
        "router",
        input={"messages": [{"role": "user", "content": "Analyze my code"}]},
        stream_mode=["values"]
    ):
        if chunk.event == "values":
            print(f"Update: {chunk.data.get('status', 'processing')}")
```

See `docs/STREAMING.md` for detailed streaming examples.

## Testing the Router Agent

### Quick Test

```bash
python test_router_simple.py
```

This runs a single test to verify the Router is working.

### Complete Test Suite

```bash
python test_router_complete.py
```

This runs three test scenarios:
1. **Quick validation task** - Should delegate to QuickAgent
2. **Deep analysis task** - Should delegate to SlowAgent
3. **Off-topic request** - Should be rejected by validation

### Expected Behavior

- ✅ **On-topic requests** are validated and processed
- ✅ **Off-topic requests** are rejected with explanations
- ✅ **Tasks are delegated** to appropriate subordinate agents based on capabilities
- ✅ **Results are aggregated** into coherent final responses

### Manual Testing

Use the interactive client:

```bash
python test_client.py
```

This provides a menu-driven interface to test different scenarios.

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
OPENAI_API_KEY=sk-...
LANGGRAPH_SERVER_URL=http://localhost:2024  # Default
LLM_PROVIDER=anthropic  # or "openai"
LLM_MODEL=claude-sonnet-4-20250514  # Optional override
```

### LLM Models

Default model is `claude-sonnet-4-20250514`. You can customize in `src/llm/factory.py` or via environment variables.

### Agent Discovery

The Router dynamically discovers subordinate agents at planning time via LangGraph Server's A2A protocol:

1. **Automatic Discovery**: Calls `/assistants/search` to find all available agents
2. **A2A Card Retrieval**: Fetches each agent's card via `/.well-known/agent-card.json?assistant_id={id}`
3. **Filtering**: Automatically skips the router itself (no self-delegation)
4. **Dynamic Support**: Can discover and use new agents added to the system without code changes

All agent metadata (name, description, capabilities, skills) is extracted from A2A agent cards with no hardcoded fallbacks.

## Version Compatibility

Current versions (tested and working together):

- `langgraph==1.0.2`
- `langgraph-api==0.5.4`
- `langgraph-cli==0.4.7`
- `langgraph-sdk==0.2.9`
- `a2a-sdk>=0.3.10`

These versions have been tested and verified to work correctly together. All packages are at their latest stable releases.

## Troubleshooting

### Server won't start
- Ensure port 2024 is not in use: `lsof -i :2024`
- Check API keys are set in `.env`
- Verify versions: `uv pip list | grep langgraph`

### Agent discovery fails
- Verify LangGraph server is running: `curl http://localhost:2024/ok`
- Check server logs for `/assistants/search` calls
- Ensure agents have A2A agent cards defined

### "BlockingError" in logs
- This should not occur (code uses async HTTP with httpx)
- If you see this, ensure you've pulled the latest code with async refactoring

### JSON parsing errors in validation
- Check server logs to see LLM responses
- The code handles both raw JSON and code-block wrapped JSON

### Tasks not executing
- Check that agents are discovered: look for "Registered agent:" in logs
- Verify agent IDs match between plan and discovery
- Ensure A2A endpoints are accessible: `curl http://localhost:2024/a2a/{assistant_id}`

## Architecture

See `architecture.md` for detailed technical documentation including:
- System context and container diagrams
- Router workflow and node details
- A2A protocol implementation
- Planning system internals
- State model and execution flow

## Dependencies

Core dependencies:
- `langchain-core>=1.0.3` - LangChain abstractions
- `langchain-anthropic>=1.0.1` - Anthropic integration
- `langgraph>=1.0.2` - State machine framework
- `langgraph-cli>=0.4.7` - CLI tools
- `httpx>=0.27.0` - Async HTTP client
- `a2a-sdk>=0.3.10` - A2A protocol SDK

Development dependencies:
- `langgraph-api==0.5.4` - LangGraph dev server
- `langgraph-sdk>=0.2.9` - Python SDK for testing
- `pytest>=8.4.2` - Testing framework

## Production Deployment

For production deployment to LangSmith Cloud:

```bash
langgraph deploy
```

Make sure to:
1. Configure proper checkpointing (PostgreSQL instead of MemorySaver)
2. Set appropriate timeout values for production workloads
3. Configure monitoring and logging
4. Set up authentication and authorization
5. Use environment-specific API keys

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

[Your license here]
