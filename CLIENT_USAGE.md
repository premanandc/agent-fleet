# Router Agent Client Usage

## Prerequisites

Make sure LangGraph Server is running:
```bash
uv run langgraph dev --no-browser
```

You should see:
```
[info] Registering graph with id 'router'
[info] Registering graph with id 'quick_agent'
[info] Registering graph with id 'slow_agent'
```

## Option 1: Automated Test Suite

Run all test scenarios:

```bash
python test_client.py
```

This will:
1. Discover the Router agent
2. List all available agents
3. Run 3 test scenarios:
   - Quick validation (→ QuickAgent)
   - Deep fixing (→ SlowAgent)
   - Parallel execution (→ Both agents)

**Expected Output:**
```
======================================================================
Router Agent Test Client
======================================================================

📋 Available Agents:
----------------------------------------------------------------------
  • router              → fe01234...
  • quick_agent         → fe05678...
  • slow_agent          → fe09012...
----------------------------------------------------------------------

🔍 Discovering Router agent...
✓ Found Router: fe01234...

======================================================================
Test Scenarios
======================================================================

🧪 TEST 1: Quick Validation (should use QuickAgent)
----------------------------------------------------------------------
💬 User Request: Can you quickly validate the syntax of my code?
⚙️  Mode: auto
----------------------------------------------------------------------
⏳ Invoking Router (synchronous)...

======================================================================
📊 RESULT
======================================================================

# Validation Results

Quick syntax validation completed successfully. No critical issues found.

----------------------------------------------------------------------
⏱️  Execution time: 3.45s
✅ Tasks completed: 1
   ✓ Task 1: Perform quick syntax validation on code (QuickAgent)
======================================================================
```

## Option 2: Interactive Chat

Start an interactive session:

```bash
# Basic usage
python chat_with_router.py

# With streaming
python chat_with_router.py --stream

# Interactive mode (with plan approval)
python chat_with_router.py --mode interactive
```

**Example Session:**
```
======================================================================
Interactive Chat with Router Agent
======================================================================

🔍 Discovering Router agent...
✓ Connected to Router: fe01234...
⚙️  Mode: auto
📡 Streaming: disabled

======================================================================
Type your requests below (or 'quit' to exit)
======================================================================

💡 Example requests:
  • Quick check my code
  • Fix SonarQube violations
  • Validate my code and fix any issues

👤 You: Quick check my code

🤖 Router:
## Quick Validation Complete

**Processing Time**: 1.45s

**Summary**: Performed quick syntax and structure validation.

**Findings**:
- Files analyzed: 8
- Syntax errors found: 0
- Warnings: 2

**Status**: ✓ All checks passed

**Recommendation**: No immediate action needed.

👤 You: Fix SonarQube violations

🤖 Router:
## Deep Remediation Complete

**Processing Time**: 7.32s

**Summary**: Performed comprehensive code remediation...

👤 You: quit

👋 Goodbye!
```

## Option 3: Direct API Calls

### Using curl

**1. Discover Router:**
```bash
curl -X POST http://localhost:2024/assistants/search \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

**2. Invoke Router (Replace `{ASSISTANT_ID}` with actual ID):**
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
    },
    "config": {
      "configurable": {
        "mode": "auto"
      }
    },
    "stream_mode": "values"
  }' | python3 -m json.tool
```

**3. Streaming (with SSE):**
```bash
curl -X POST http://localhost:2024/threads/{ASSISTANT_ID}/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {
          "role": "user",
          "content": "Validate and fix my code"
        }
      ]
    },
    "stream_mode": "values"
  }'
```

### Using Python requests

```python
import requests

# Discover Router
response = requests.post("http://localhost:2024/assistants/search", json={})
assistants = response.json()
router = next(a for a in assistants if a["graph_id"] == "router")
assistant_id = router["assistant_id"]

# Invoke Router
response = requests.post(
    f"http://localhost:2024/threads/{assistant_id}/runs",
    json={
        "input": {
            "messages": [
                {"role": "user", "content": "Quick check my code"}
            ]
        },
        "config": {
            "configurable": {"mode": "auto"}
        }
    }
)

result = response.json()
print(result["final_response"])
```

## Execution Modes

### AUTO Mode (Default)
```bash
python chat_with_router.py --mode auto
```
- Fully autonomous
- No human approval needed
- Router decides everything

### INTERACTIVE Mode
```bash
python chat_with_router.py --mode interactive
```
- Pauses for plan approval
- User can approve/reject/modify
- Good for learning how Router works

### REVIEW Mode
```bash
python chat_with_router.py --mode review
```
- Shows plan but auto-approves
- Transparency without blocking
- Good for monitoring

## What to Expect

### Quick Tasks (QuickAgent)
**Triggers:**
- "quick check"
- "validate syntax"
- "fast scan"

**Behavior:**
- Executes in 1-2 seconds
- Returns validation/analysis reports
- Good for initial assessments

### Deep Tasks (SlowAgent)
**Triggers:**
- "fix violations"
- "remediate issues"
- "refactor code"
- "SonarQube"

**Behavior:**
- Executes in 5-10 seconds
- Returns comprehensive remediation reports
- Shows multi-stage processing

### Parallel Execution
**Triggers:**
- "validate and fix"
- "check and remediate"
- Multiple independent tasks

**Behavior:**
- Router creates parallel plan
- Both agents run simultaneously
- Results aggregated
- Total time ≈ slowest agent

## Troubleshooting

### "Router agent not found"
**Fix:** Make sure LangGraph Server is running
```bash
uv run langgraph dev --no-browser
```

### "Cannot connect to server"
**Fix:** Check server is running on port 2024
```bash
curl http://localhost:2024/ok
```
Should return: `ok`

### "Connection timeout"
**Fix:** Increase timeout in client or check server logs

### Tasks not executing
**Fix:** Check server logs for errors:
```bash
# Server will show:
[Execute] Invoking agent QuickAgent for: ...
[QuickAgent] Starting quick task: ...
```

## API Endpoints Reference

- `POST /assistants/search` - List all agents
- `GET /assistants/{id}` - Get agent details
- `POST /threads/{id}/runs` - Invoke agent (sync)
- `POST /threads/{id}/runs/stream` - Invoke agent (streaming)
- `GET /ok` - Health check

## Client Features

### test_client.py
- ✅ Automated test scenarios
- ✅ Shows Router workflow
- ✅ Demonstrates parallel execution
- ✅ Good for CI/CD testing

### chat_with_router.py
- ✅ Interactive REPL
- ✅ Natural conversation
- ✅ Streaming support
- ✅ Good for experimentation

## Next Steps

1. **Try the test suite:** `python test_client.py`
2. **Chat interactively:** `python chat_with_router.py --stream`
3. **Experiment with requests** - See how Router delegates tasks
4. **Monitor server logs** - Watch agent coordination in real-time
5. **Try different modes** - Compare auto/interactive/review

Happy testing! 🚀
