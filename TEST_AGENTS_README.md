# Test Subordinate Agents

## Overview

Two simple A2A agents created for testing the Router Agent:

1. **QuickAgent** - Simulates fast operations (1-2 seconds)
2. **SlowAgent** - Simulates slow operations (5-10 seconds)

Both agents are fully A2A-compatible and can be discovered and invoked by the Router.

## QuickAgent

**File**: `src/agents/quick_agent.py`

### Capabilities
- `analysis`
- `quick-check`
- `validation`
- `syntax-checking`

### Skills
- Analyze code syntax
- Quick validation
- Fast security scans
- Basic code review
- Structure analysis

### Runtime
- Typical: 1-2 seconds
- Max: 5 seconds

### Use Cases
- Initial assessment
- Quick validation before deployment
- Fast feedback loops
- Syntax and structure checks

### Sample Output

```markdown
## Quick Validation Complete

**Processing Time**: 1.78s

**Summary**: Performed quick syntax and structure validation.

**Findings**:
- Files analyzed: 12
- Syntax errors found: 2
- Warnings: 5

**Status**: ⚠ 2 issues require attention

**Recommendation**: Review identified issues and consider fixes.
```

## SlowAgent

**File**: `src/agents/slow_agent.py`

### Capabilities
- `deep-analysis`
- `remediation`
- `code-fixing`
- `refactoring`
- `sonarqube`

### Skills
- Fix SonarQube violations
- Deep code analysis
- Complex refactoring
- Automated code remediation
- Performance optimization
- Security issue resolution

### Runtime
- Typical: 5-10 seconds
- Max: 30 seconds

### Use Cases
- Comprehensive code fixing
- Deep quality analysis
- Complex refactoring tasks
- SonarQube remediation
- Performance optimization

### Sample Output

```markdown
## Deep Remediation Complete

**Processing Time**: 9.65s

**Summary**: Performed comprehensive code remediation with automated fixes.

### Issues Addressed

**Critical Issues Fixed**: 2
- Null pointer vulnerabilities
- Resource leak in database connections

**Major Issues Fixed**: 4
- Code smells and anti-patterns
- Inefficient algorithms

**Minor Issues Fixed**: 8
- Style violations
- Naming conventions

### Changes Made

**Files Modified**: 15
**Lines Changed**: 287
**Tests Updated**: 8

**Status**: ✓ Remediation successful - ready for review
```

## Agent Cards

Both agents have A2A agent cards that the Router can discover:

```python
# QuickAgent Card
{
    "name": "QuickAgent",
    "capabilities": ["analysis", "quick-check", "validation", "syntax-checking"],
    "skills": ["Analyze code syntax", "Quick validation", ...],
    "performance": {
        "typical_runtime": "1-2 seconds",
        "max_runtime": "5 seconds"
    }
}

# SlowAgent Card
{
    "name": "SlowAgent",
    "capabilities": ["deep-analysis", "remediation", "code-fixing", "refactoring", "sonarqube"],
    "skills": ["Fix SonarQube violations", "Deep code analysis", ...],
    "performance": {
        "typical_runtime": "5-10 seconds",
        "max_runtime": "30 seconds"
    }
}
```

## Configuration

Both agents are registered in `langgraph.json`:

```json
{
  "graphs": {
    "router": "./src/agents/router_agent.py:create_router_graph",
    "quick_agent": "./src/agents/quick_agent.py:create_quick_agent_graph",
    "slow_agent": "./src/agents/slow_agent.py:create_slow_agent_graph"
  }
}
```

## Testing

### Local Test

```bash
python3 test_router_with_subordinates.py
```

This test demonstrates:
- ✅ Router discovering both agents
- ✅ Sequential execution (QuickAgent only)
- ✅ Parallel execution (QuickAgent + SlowAgent)
- ✅ Task delegation based on capabilities
- ✅ Result aggregation

### Test Output

```
TEST 1: Router with Quick Task (Validation)
----------------------------------------------------------------------
✓ Router discovered 2 agents
✓ Validated user request
✓ Generated sequential plan
✓ Executed QuickAgent task (1.78s)
✓ Aggregated results

TEST 2: Router with Parallel Tasks (Quick Check + Deep Fix)
----------------------------------------------------------------------
✓ Router discovered 2 agents
✓ Generated parallel plan
✓ Executed QuickAgent task (1.25s)
✓ Executed SlowAgent task (9.65s)
✓ Both tasks ran in parallel
✓ Aggregated combined results

✓ ALL TESTS PASSED!
```

## With LangGraph Server

1. **Start Server**:
```bash
langgraph dev
```

2. **Discover Agents**:
```bash
curl http://localhost:2024/assistants/search | jq '.'
```

3. **Get Agent Card**:
```bash
curl http://localhost:2024/a2a/{quick_agent_id}/card | jq '.'
```

4. **Invoke QuickAgent Directly**:
```bash
curl -X POST http://localhost:2024/a2a/{quick_agent_id} \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {"role": "user", "content": "Validate my code syntax"}
      ]
    },
    "config": {
      "configurable": {"thread_id": "test-123"}
    }
  }'
```

5. **Invoke via Router**:
```bash
curl -X POST http://localhost:2024/a2a/{router_id} \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {"role": "user", "content": "Quick check my code and fix any SonarQube issues"}
      ]
    },
    "config": {
      "configurable": {"thread_id": "test-123", "mode": "auto"}
    }
  }'
```

The Router will:
1. Discover QuickAgent and SlowAgent
2. Analyze the request
3. Plan: "Quick check" → QuickAgent, "fix SonarQube" → SlowAgent
4. Execute both in parallel
5. Aggregate and return results

## Implementation Details

### QuickAgent Structure

```python
def process_quick_task(state):
    """Simulates 1-2 second task"""
    time.sleep(random.uniform(1.0, 2.0))
    return {"messages": [AIMessage(content=response)]}

graph = StateGraph(QuickAgentState)
graph.add_node("process", process_quick_task)
graph.add_edge(START, "process")
graph.add_edge("process", END)
```

### SlowAgent Structure

```python
def process_slow_task(state):
    """Simulates 5-10 second task with multi-stage processing"""
    # Stage 1: Analyzing (20% of time)
    # Stage 2: Identifying (30% of time)
    # Stage 3: Generating (30% of time)
    # Stage 4: Validating (20% of time)
    time.sleep(random.uniform(5.0, 10.0))
    return {"messages": [AIMessage(content=response)]}

graph = StateGraph(SlowAgentState)
graph.add_node("process", process_slow_task)
graph.add_edge(START, "process")
graph.add_edge("process", END)
```

## Realistic Behavior

Both agents generate context-aware responses based on keywords:

- **"validate"** → Quick Validation report
- **"analyze"** → Analysis report with metrics
- **"scan"** → Security scan results
- **"fix" / "remediate"** → Remediation report with changes
- **"sonarqube"** → SonarQube-specific analysis
- **"refactor"** → Refactoring report with improvements

This makes the test agents behave realistically and helps validate the Router's orchestration logic.

## Benefits for Testing

1. **No External Dependencies**: Test Router without needing real agents
2. **Controllable Timing**: Predictable execution times for testing
3. **Realistic Responses**: Context-aware outputs that look like real agent results
4. **Capability Testing**: Validates Router's capability-driven routing
5. **Parallel Execution Testing**: Different speeds help test parallel orchestration
6. **A2A Protocol Validation**: Full A2A compatibility testing

## Next Steps

1. Use these as templates for real specialized agents
2. Replace QuickAgent with real AskCody agent
3. Replace SlowAgent with real Coda agent
4. Keep test agents for CI/CD testing
5. Add more test agents for edge cases (timeout simulation, error simulation, etc.)
