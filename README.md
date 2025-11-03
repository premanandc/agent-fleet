# Agent Fleet

A multi-agent orchestration system for the ITEP (IT Engineering Productivity) platform, featuring a Router Agent that intelligently delegates tasks to specialized subordinate agents.

## Features

- **Router Agent**: Orchestrates and delegates tasks based on capabilities
- **Multi-Agent Architecture**: QuickAgent for fast tasks, SlowAgent for deep analysis
- **A2A Protocol**: Full Agent-to-Agent protocol support via LangGraph Server
- **Capability-Driven Routing**: Automatic agent selection based on skills and requirements
- **LLM Provider Agnostic**: Supports both OpenAI and Anthropic models
- **Execution Modes**: Auto, interactive, and review modes for different workflows

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
│       └── slow_agent.py           # Deep analysis agent (5-10s)
├── test_router_simple.py           # Simple Router test
├── test_router_complete.py         # Complete test suite
├── langgraph.json                  # LangGraph Server configuration
├── pyproject.toml                  # Dependencies
└── .env                            # API keys
```

## Setup

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

**Important**: Use the `--allow-blocking` flag for development:

```bash
uv run langgraph dev --no-browser --allow-blocking
```

The server will start on `http://localhost:2024` with:
- API Documentation: `http://localhost:2024/docs`
- A2A endpoints: `http://localhost:2024/a2a/{assistant_id}`
- Health check: `http://localhost:2024/ok`

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

## Router Agent Architecture

The Router uses a 7-node workflow:

```
[Start] → [Validate] → [Plan] → [Approval] → [Execute] → [Analyze] → [Aggregate] → [End]
            ↓                                                   ↓
          [Reject]                                         [Re-plan if needed]
```

### Nodes

1. **Validate**: Guards against off-topic requests using LLM classification
2. **Reject**: Handles rejected requests with helpful explanations
3. **Plan**: Decomposes requests and matches tasks to agent capabilities
4. **Approval**: Optional human-in-the-loop (interactive mode only)
5. **Execute**: Delegates tasks to subordinate agents via A2A protocol
6. **Analyze**: Evaluates if results are sufficient or need replanning
7. **Aggregate**: Combines results into final response

## Execution Modes

Configure via `config.configurable.mode`:

- **`auto`** (default): Fully autonomous, no approval needed
- **`interactive`**: Pauses for plan approval before execution
- **`review`**: Shows plan but auto-approves (transparency without blocking)

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

### SlowAgent (`slow_agent`)
- **Purpose**: Deep analysis (SonarQube fixes, comprehensive reviews)
- **Capabilities**: `deep-analysis`, `remediation`, `sonarqube`
- **Response time**: 5-10 seconds

### Task Breakdown Agent (`task_breakdown`)
- **Purpose**: Legacy task decomposition agent
- **Note**: Functionality absorbed into Router

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

## Version Compatibility

**Important**: The project is currently pinned to compatible versions:

- `langgraph-api==0.4.46` (not 0.5.x due to incompatibility issues)
- `langgraph-runtime-inmem==0.14.1`
- `langgraph-cli==0.4.6`

These versions are tested and working together. Do not upgrade to 0.5.x until the `FF_RICH_THREADS` compatibility issue is resolved upstream.

## Configuration

### LLM Models

Default model is `claude-sonnet-4-20250514`. You can customize in `src/llm/factory.py` or via environment variables:

```bash
LLM_PROVIDER=anthropic  # or "openai"
LLM_MODEL=claude-sonnet-4-20250514  # Optional override
```

### Blocking Calls

The current implementation uses synchronous `requests` library for HTTP calls. For development, use:

```bash
uv run langgraph dev --allow-blocking
```

For production, consider refactoring to use async HTTP libraries (`aiohttp`, `httpx`).

## Troubleshooting

### Server won't start
- Ensure port 2024 is not in use: `lsof -i :2024`
- Check API keys are set in `.env`
- Verify versions: `uv pip list | grep langgraph`

### "FF_RICH_THREADS" error
- You're using incompatible versions (0.5.x)
- Downgrade: `uv pip install 'langgraph-api==0.4.46'`
- Update `pyproject.toml` to pin the version

### "BlockingError" in logs
- Restart server with: `uv run langgraph dev --allow-blocking`

### JSON parsing errors in validation
- Check server logs to see LLM responses
- The code handles both raw JSON and code-block wrapped JSON

## Production Deployment

For production deployment to LangSmith Cloud:

```bash
langgraph deploy
```

Make sure to:
1. Set `BG_JOB_ISOLATED_LOOPS=true` environment variable
2. Use async HTTP calls instead of `requests`
3. Configure proper checkpointing (PostgreSQL)

## Dependencies

Core dependencies:
- `langchain-core>=1.0.3` - LangChain abstractions
- `langchain-anthropic>=1.0.1` - Anthropic integration
- `langgraph>=1.0.2` - State machine framework
- `langgraph-cli>=0.4.6` - CLI tools
- `requests>=2.32.5` - HTTP client (TODO: migrate to async)

Development dependencies:
- `langgraph-api==0.4.46` - LangGraph dev server
- `langgraph-sdk>=0.2.9` - Python SDK for testing
- `pytest>=8.4.2` - Testing framework

## License

[Your license here]

## Contributing

[Your contributing guidelines here]
