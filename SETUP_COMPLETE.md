# ✅ Setup Complete - Router Agent Fleet

## What Was Fixed

### Issue
LangGraph Server was failing with:
```
ImportError: attempted relative import with no known parent package
```

### Solution Applied

**1. Installed package in editable mode:**
```bash
uv pip install -e .
```

**2. Updated `langgraph.json` to use absolute imports:**

Changed from:
```json
{
  "graphs": {
    "router": "./src/agents/router_agent.py:create_router_graph",
    ...
  }
}
```

To:
```json
{
  "graphs": {
    "router": "src.agents.router_agent:create_router_graph",
    "quick_agent": "src.agents.quick_agent:create_quick_agent_graph",
    "slow_agent": "src.agents.slow_agent:create_slow_agent_graph",
    "task_breakdown": "src.agents.task_breakdown_a2a:create_task_breakdown_graph"
  }
}
```

**Why This Works:**
- File paths (`./src/...`) cause LangGraph to load modules directly, which doesn't support relative imports
- Module paths (`src.agents...`) use Python's import system, which works with the installed package

## Current Status

✅ **All 4 agents are registered and ready:**
1. **Router** - Intelligent orchestrator
2. **QuickAgent** - Fast task simulator (1-2s)
3. **SlowAgent** - Slow task simulator (5-10s)
4. **Task Breakdown** - Original experimental agent

## How to Use

### 1. Start LangGraph Server

```bash
uv run langgraph dev --no-browser
```

You should see:
```
[info] Registering graph with id 'router'
[info] Registering graph with id 'quick_agent'
[info] Registering graph with id 'slow_agent'
[info] Registering graph with id 'task_breakdown'
```

### 2. Verify Setup (Optional)

In a new terminal:
```bash
./verify_server.sh
```

### 3. List Available Agents

```bash
curl -X POST http://localhost:2024/assistants/search \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 4. Invoke Router Agent

First, get the Router's assistant ID:
```bash
curl -X POST http://localhost:2024/assistants/search -d '{}' | python3 -m json.tool
```

Then invoke it:
```bash
curl -X POST http://localhost:2024/threads/{ASSISTANT_ID}/runs \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Quick check my code and fix any issues"
        }
      ]
    }
  }'
```

Or use the streaming endpoint:
```bash
curl -X POST http://localhost:2024/threads/{ASSISTANT_ID}/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Validate my code quickly and fix SonarQube violations"
        }
      ]
    },
    "config": {
      "configurable": {
        "mode": "auto"
      }
    }
  }'
```

## What Happens When You Invoke Router

1. **Discovery**: Router discovers QuickAgent and SlowAgent at startup
2. **Validation**: Checks if request is on-topic for ITEP
3. **Planning**: Breaks request into tasks, matches to agent capabilities
   - "Quick check" → QuickAgent
   - "Fix violations" → SlowAgent
4. **Execution**: Runs tasks (parallel if independent)
5. **Aggregation**: Combines results into final response

## Testing Locally (Without Server)

```bash
# Run integration tests
python3 test_router_with_subordinates.py
```

This tests the full Router workflow with mocked agents.

## Agent Capabilities

### Router
- Orchestration
- Task breakdown
- Multi-agent coordination
- Request validation

### QuickAgent (1-2 seconds)
- Analysis
- Quick validation
- Syntax checking
- Fast security scans

### SlowAgent (5-10 seconds)
- Deep analysis
- Code remediation
- Refactoring
- SonarQube fixes

## Expected Behavior

**Example Request:**
> "Please validate my code quickly and then fix any SonarQube violations"

**Router's Actions:**
1. Validates request (on-topic ✓)
2. Generates plan:
   ```
   Task 1: Quick validation → QuickAgent
   Task 2: Fix SonarQube violations → SlowAgent
   Strategy: Parallel (tasks independent)
   ```
3. Executes both tasks in parallel:
   - QuickAgent completes in ~1.5s
   - SlowAgent completes in ~8s
4. Aggregates results into comprehensive response

## Troubleshooting

### Server Won't Start

**Check package is installed:**
```bash
uv pip list | grep agent-fleet
```

If not listed:
```bash
uv pip install -e .
```

### Import Errors

**Verify langgraph.json uses module paths:**
```bash
cat langgraph.json | grep "src.agents"
```

Should show `src.agents.router_agent` (not `./src/agents/router_agent.py`)

### Agents Not Discovered

**Check logs when Router starts:**
```
[Router] Initializing Router Agent...
[Discovery] Found 2 assistants
[Discovery] Registered agent: QuickAgent (quick-agent-id)
[Discovery] Registered agent: SlowAgent (slow-agent-id)
```

If you don't see this, QuickAgent and SlowAgent may not be running.

### Can't Connect to Server

**Verify server is running:**
```bash
curl http://localhost:2024/ok
```

Should return: `ok`

## Files Reference

### Configuration
- `langgraph.json` - Agent registration
- `pyproject.toml` - Package definition
- `.env` - Environment variables (create if needed)

### Router Agent
- `src/agents/router_agent.py` - Main orchestrator
- `src/models/router_state.py` - State definitions
- `src/nodes/*.py` - Router workflow nodes (7 nodes)
- `src/utils/discovery.py` - Agent discovery

### Test Agents
- `src/agents/quick_agent.py` - Fast task simulator
- `src/agents/slow_agent.py` - Slow task simulator
- `src/agents/cards.py` - Agent metadata

### Documentation
- `README_ROUTER.md` - Router usage guide
- `TEST_AGENTS_README.md` - Test agents guide
- `IMPLEMENTATION_SUMMARY.md` - What was built
- `ROUTER_QUICK_REFERENCE.md` - Quick reference

### Tests
- `test_router_local.py` - Simple Router test
- `test_router_with_subordinates.py` - Full integration test
- `tests/unit/` - Unit tests (18 tests)
- `tests/integration/` - Integration tests (4 tests)

## Next Steps

1. ✅ **Server is running** - You can now test the Router!

2. **Try Example Requests:**
   - "Quick check my code"
   - "Fix SonarQube violations"
   - "Analyze my code and fix any issues"

3. **View in LangSmith Studio:**
   - Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
   - See live graph execution
   - Debug workflows visually

4. **Add Real Agents:**
   - Replace QuickAgent with real AskCody
   - Replace SlowAgent with real Coda
   - Keep test agents for CI/CD

5. **Customize:**
   - Adjust prompts in `src/nodes/*.py`
   - Tune LLM temperatures
   - Add more capabilities
   - Implement additional nodes

## Success Indicators

✅ Server starts without errors
✅ All 4 graphs registered
✅ Router can be invoked
✅ Subordinate agents discovered
✅ Tasks execute successfully
✅ Results aggregated properly

**Your Router Agent Fleet is ready! 🚀**
