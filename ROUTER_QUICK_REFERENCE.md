# Router Agent Quick Reference

## TL;DR

The Router Agent is an intelligent orchestrator that discovers agents, breaks down requests, executes tasks via A2A, and synthesizes results.

**Key Files:**
- Graph: `src/agents/router_agent.py`
- Nodes: `src/nodes/*.py` (7 nodes)
- State: `src/models/router_state.py`
- Config: `langgraph.json`

## Quick Start

```bash
# 1. Set environment
export ANTHROPIC_API_KEY=sk-ant-...
export LANGGRAPH_SERVER_URL=http://localhost:2024

# 2. Test locally
python3 test_router_local.py

# 3. Start LangGraph Server
langgraph dev

# 4. Invoke Router
curl -X POST http://localhost:2024/a2a/{assistant_id} \
  -d '{"input": {"messages": [{"role": "user", "content": "Fix SonarQube issues"}]}}'
```

## Graph Flow

```
START → validate → [valid?]
                    ├─ yes → plan → [mode?]
                    │                ├─ auto → execute
                    │                └─ interactive → approval → [approved?]
                    │                                             ├─ yes → execute
                    │                                             └─ no → plan (replan)
                    │        execute → analyze → [sufficient?]
                    │                             ├─ yes → aggregate → END
                    │                             └─ no → plan (replan)
                    └─ no → reject → END
```

## Nodes

| Node | Purpose | LLM? |
|------|---------|------|
| `validate_request` | Check if on-topic | ✓ |
| `reject_request` | Format rejection | ✗ |
| `generate_plan` | Break into tasks | ✓ |
| `await_approval` | Human approval | ✗ |
| `execute_tasks` | A2A invocation | ✗ |
| `analyze_results` | Check sufficiency | ✓ |
| `aggregate_results` | Synthesize response | ✓ |

## Execution Modes

```python
# AUTO mode (fully autonomous)
state = create_initial_state("Fix bugs", mode="auto")

# INTERACTIVE mode (pause for approval)
state = create_initial_state("Fix bugs", mode="interactive")

# REVIEW mode (show plan, auto-approve)
state = create_initial_state("Fix bugs", mode="review")
```

## State Fields

```python
RouterState = {
    # A2A Required
    "messages": list[BaseMessage],

    # Request
    "request_id": str,
    "original_request": str,

    # Validation
    "is_valid": bool,
    "rejection_reason": str | None,

    # Planning
    "plan": Plan | None,
    "plan_approved": bool,

    # Execution
    "current_task_index": int,
    "task_results": list[Task],

    # Replanning
    "need_replan": bool,
    "replan_reason": str | None,
    "replan_count": int,
    "max_replans": int,

    # Result
    "final_response": str | None,

    # Config
    "mode": "auto" | "interactive" | "review"
}
```

## Agent Discovery

Router discovers agents at startup:

```python
# Automatic via create_router_graph()
graph = create_router_graph()
# Calls: POST /assistants/search
# Fetches: GET /a2a/{id}/card for each
# Builds: agent_registry = {agent_id: AgentCapability}
```

Agent cards must have:
```json
{
  "name": "Coda",
  "capabilities": ["code-quality", "sonarqube"],
  "skills": ["Fix SonarQube violations"],
  "description": "SonarQube remediation specialist"
}
```

## Task Execution

Tasks execute via A2A:

```python
# Router builds message for subordinate
POST /a2a/{agent_id}
{
  "input": {
    "messages": [{
      "role": "user",
      "content": "Original request: {user_request}\n\n
                 Your task: {task_description}\n\n
                 Context: {dependency_results}"
    }]
  }
}
```

## Replanning

Triggered when results insufficient:

```python
# analyze_results evaluates sufficiency
if not sufficient and replan_count < max_replans:
    # Loop back to generate_plan with context:
    # - Previous task results
    # - Replan reason from analysis
    # - Original request

    # New plan can:
    # - Add follow-up tasks
    # - Try different agents
    # - Adjust decomposition
```

## Testing

```bash
# Unit tests (18 tests)
pytest tests/unit/test_router_nodes.py -v

# Integration tests (4 tests)
pytest tests/integration/test_router_graph.py -v

# All tests
pytest -v

# Local verification
python3 test_router_local.py
```

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (with defaults)
LLM_PROVIDER=anthropic          # or "openai"
LLM_MODEL=claude-3-5-sonnet-20241022
LANGGRAPH_SERVER_URL=http://localhost:2024
```

## Common Issues

### "No agents available"
- Check LangGraph Server is running
- Verify other agents are deployed
- Check agent cards have capabilities/skills

### "Validation error"
- LLM failed to parse response as JSON
- Check ANTHROPIC_API_KEY is valid
- Review validation prompt in validate.py

### "Agent timeout"
- Default: 5 minutes per task
- Increase in execute.py if needed
- Check subordinate agent is responding

### "Max replans reached"
- Default: 2 replans
- Increase max_replans if needed
- Check if tasks are failing repeatedly

## Architecture Docs

- **Complete Architecture**: `docs/router-agent.md`
- **C4 Diagrams**: System Context, Container, Component
- **Structurizr DSL**: `docs/router-agent.dsl`
- **Usage Guide**: `README_ROUTER.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`

## Key Insights

1. **Capability-Driven**: Tasks matched to agents via capabilities, not hardcoding
2. **LLM Decision Points**: Validation, planning, analysis, aggregation all use LLM
3. **Deterministic Flow**: Nodes (not tools) for predictable execution
4. **A2A Native**: Full protocol compatibility for agent ecosystem
5. **Human-Friendly**: Interactive mode for transparency and control

## Next Steps

1. Set `ANTHROPIC_API_KEY` in `.env`
2. Deploy subordinate agents (Coda, AskCody)
3. Start LangGraph Server: `langgraph dev`
4. Test with real requests
5. Monitor and iterate on prompts

## Contact

For questions or issues, see:
- Architecture: `docs/router-agent.md`
- Usage: `README_ROUTER.md`
- Implementation: `IMPLEMENTATION_SUMMARY.md`
