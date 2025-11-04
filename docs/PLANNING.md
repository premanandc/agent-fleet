# Router Agent Planning System

This document explains how the planning node works and how to troubleshoot common issues.

## Overview

The planning node (`src/nodes/plan.py`) is responsible for:

1. **Discovering available agents** via A2A protocol
2. **Analyzing the user request** to understand what needs to be done
3. **Decomposing the request** into specific, actionable tasks
4. **Matching tasks to agents** based on capabilities and skills
5. **Creating an execution plan** with task ordering and dependencies

## How Planning Works

### Step 1: Agent Discovery

```python
agent_registry = await discover_agents_from_langgraph()
```

The planner first discovers what subordinate agents are available:
- Calls `/assistants/search` to find all agents
- Fetches A2A cards via `/.well-known/agent-card.json`
- Filters out router itself and task_breakdown
- Builds a registry of agent capabilities

**Example Registry:**
```python
{
    "8dc97659-9c90-5a08-b493-8b99583b8333": {
        "name": "QuickAgent",
        "capabilities": ["analysis", "quick-check", "validation"],
        "skills": ["Analyze code syntax", "Quick validation", ...],
        "description": "Fast analysis agent for quick validation..."
    },
    "d64f349d-bdc0-5361-9fb3-a61d5a3c4e10": {
        "name": "SlowAgent",
        "capabilities": ["deep-analysis", "remediation", "sonarqube"],
        "skills": ["Fix SonarQube violations", "Deep code analysis", ...],
        "description": "Deep analysis agent for comprehensive review..."
    }
}
```

### Step 2: Building the Prompt

The planner creates a detailed prompt for the LLM:

```
USER REQUEST:
Fix all SonarQube violations in my codebase

AVAILABLE AGENTS:
- QuickAgent (ID: 8dc97659-9c90-5a08-b493-8b99583b8333):
  Capabilities: analysis, quick-check, validation
  Skills: Analyze code syntax, Quick validation, ...
  Description: Fast analysis agent...

- SlowAgent (ID: d64f349d-bdc0-5361-9fb3-a61d5a3c4e10):
  Capabilities: deep-analysis, remediation, sonarqube
  Skills: Fix SonarQube violations, Deep code analysis, ...
  Description: Deep analysis agent...

YOUR TASK:
Create an execution plan...

Respond with JSON in this exact format:
{
  "analysis": "Brief analysis of the request and approach",
  "execution_strategy": "parallel" or "sequential",
  "tasks": [
    {
      "description": "Clear description",
      "agent_id": "exact agent ID from available agents",
      "agent_name": "agent name for logging",
      "dependencies": [],
      "rationale": "Why this agent was chosen"
    }
  ]
}
```

### Step 3: LLM Response

The LLM analyzes the request and available agents, then returns a JSON plan.

**Expected Response Format:**
```json
{
  "analysis": "The request requires fixing SonarQube violations, which needs deep analysis and remediation capabilities",
  "execution_strategy": "sequential",
  "tasks": [
    {
      "description": "Analyze and fix SonarQube violations in codebase",
      "agent_id": "d64f349d-bdc0-5361-9fb3-a61d5a3c4e10",
      "agent_name": "SlowAgent",
      "dependencies": [],
      "rationale": "SlowAgent has deep-analysis and remediation capabilities needed for SonarQube fixes"
    }
  ]
}
```

### Step 4: Task Creation

The planner processes the LLM response:

```python
plan_data = json.loads(response.content)  # Parse JSON

for idx, raw_task in enumerate(plan_data["tasks"]):
    task_id = f"task_{uuid.uuid4().hex[:8]}"  # Generate unique ID

    # Validate agent exists
    if agent_id not in agent_registry:
        logger.warning(f"Agent {agent_id} not found, skipping task")
        continue

    # Create Task object
    task = Task(
        id=task_id,
        description=raw_task["description"],
        agent_id=raw_task["agent_id"],
        agent_name=raw_task["agent_name"],
        status="pending",
        dependencies=raw_task.get("dependencies", []),
        rationale=raw_task["rationale"]
    )

    tasks.append(task)
```

### Step 5: Plan Assembly

```python
plan = Plan(
    tasks=tasks,
    execution_strategy=execution_strategy,
    created_at=datetime.now(),
    analysis=analysis
)

return {"plan": plan, "need_replan": False}
```

## Common Issues

### Issue #1: "Invalid JSON response from LLM"

**Problem:** The LLM returns JSON wrapped in markdown code blocks:

```
```json
{
  "analysis": "...",
  "tasks": [...]
}
```
```

Instead of pure JSON:
```json
{
  "analysis": "...",
  "tasks": [...]
}
```

**Root Cause:** Claude (and other LLMs) often wrap JSON in markdown fences for better readability.

**Solution:** We need to strip markdown code blocks before parsing. Here's the fix:

```python
# In src/nodes/plan.py, line 160
response = await llm.ainvoke(messages)

# Strip markdown code blocks if present
response_content = response.content.strip()

# Remove ```json and ``` if present
if response_content.startswith("```"):
    # Find the first newline (after ```json or ```)
    first_newline = response_content.find('\n')
    # Find the last ```
    last_fence = response_content.rfind('```')
    # Extract content between fences
    response_content = response_content[first_newline + 1:last_fence].strip()

# Parse JSON
plan_data = json.loads(response_content)
```

### Issue #2: Zero Tasks Generated

**Problem:** Plan has 0 tasks even though LLM returned tasks.

**Possible Causes:**

1. **Agent ID mismatch:** LLM returns agent IDs that don't exist in the registry
   ```python
   # Line 185: This validation skips tasks with invalid agent IDs
   if agent_id not in agent_registry:
       logger.warning(f"Agent {agent_id} not found in registry, skipping task")
       continue  # Task is skipped!
   ```

2. **Empty agent registry:** No agents discovered
   ```python
   # Line 50: If no agents, returns empty plan
   if not agent_registry:
       logger.warning("No agents available in registry")
       return {"plan": Plan(tasks=[], ...)}
   ```

3. **LLM returns tasks array as empty:** `"tasks": []`

**Debug Steps:**

1. Check logs for agent discovery:
   ```
   INFO:src.utils.discovery:Found 4 assistants
   INFO:src.utils.discovery:Registered agent: QuickAgent (8dc9...)
   INFO:src.utils.discovery:Registered agent: SlowAgent (d64f...)
   ```

2. Check logs for LLM response parsing:
   ```
   ERROR:src.nodes.plan:Failed to parse LLM response as JSON: ...
   ERROR:src.nodes.plan:Raw response: <actual LLM response>
   ```

3. Check logs for agent validation:
   ```
   WARNING:src.nodes.plan:Agent xyz not found in registry, skipping task
   ```

### Issue #3: LLM Doesn't Follow JSON Format

**Problem:** LLM returns text explanation instead of JSON.

**Example Bad Response:**
```
Based on the request, I'll create a plan with two tasks:

First, we should use QuickAgent to do a quick scan...
Then, SlowAgent can provide deep analysis...
```

**Solution:** Improve the prompt to be more explicit about JSON-only output:

```python
planning_prompt = f"""...

CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown, just pure JSON.

Do NOT wrap in code blocks. Do NOT add any text before or after the JSON.

Your response should start with {{ and end with }}

JSON format:
{{
  "analysis": "...",
  "execution_strategy": "parallel" or "sequential",
  "tasks": [...]
}}
"""
```

## Debugging Planning Issues

### Enable Detailed Logging

The planning node already logs extensively. Check the server logs:

```bash
# Look for these log messages
INFO:src.nodes.plan:Generating plan for: <request>
INFO:src.nodes.plan:Discovering available agents...
INFO:src.utils.discovery:Found X assistants
INFO:src.utils.discovery:Registered agent: <name> (<id>)
INFO:src.nodes.plan:Analysis: <analysis>
INFO:src.nodes.plan:Strategy: <strategy>
INFO:src.nodes.plan:Tasks: X
INFO:src.nodes.plan:Generated plan with X tasks
```

### Check LLM Response

Add temporary debugging to see the raw LLM response:

```python
# After line 160
response = await llm.ainvoke(messages)

# Add this temporarily
logger.info(f"=== RAW LLM RESPONSE ===")
logger.info(response.content)
logger.info(f"=== END RESPONSE ===")

# Parse response
plan_data = json.loads(response.content)
```

### Verify Agent Discovery

Test agent discovery independently:

```python
import asyncio
from src.utils.discovery import discover_agents_from_langgraph

async def test():
    agents = await discover_agents_from_langgraph()
    print(f"Found {len(agents)} agents:")
    for agent_id, cap in agents.items():
        print(f"  {cap['name']} ({agent_id})")
        print(f"    Capabilities: {cap['capabilities']}")

asyncio.run(test())
```

### Test with Simple Request

Try a very simple request that clearly maps to one agent:

```python
# Should clearly map to QuickAgent
"Quick syntax check on my code"

# Should clearly map to SlowAgent
"Fix all SonarQube violations"
```

## Improving Planning Reliability

### 1. Make Prompt More Explicit

Add examples to the prompt:

```python
planning_prompt = f"""...

EXAMPLE RESPONSE:
{{
  "analysis": "User wants quick validation, which matches QuickAgent capabilities",
  "execution_strategy": "sequential",
  "tasks": [
    {{
      "description": "Perform quick syntax validation on codebase",
      "agent_id": "{list(agent_registry.keys())[0]}",
      "agent_name": "QuickAgent",
      "dependencies": [],
      "rationale": "QuickAgent is optimized for fast validation tasks"
    }}
  ]
}}

NOW CREATE YOUR RESPONSE:
"""
```

### 2. Use Structured Output (Advanced)

For Anthropic models, use tool calling to enforce JSON structure:

```python
from langchain_core.tools import tool

@tool
def create_plan(
    analysis: str,
    execution_strategy: str,
    tasks: List[dict]
) -> dict:
    """Create an execution plan"""
    return {
        "analysis": analysis,
        "execution_strategy": execution_strategy,
        "tasks": tasks
    }

llm_with_tools = llm.bind_tools([create_plan])
response = await llm_with_tools.ainvoke(messages)
```

### 3. Add Retry Logic

Retry with a simpler prompt if JSON parsing fails:

```python
try:
    plan_data = json.loads(response.content)
except json.JSONDecodeError:
    # Retry with simpler prompt
    logger.warning("JSON parse failed, retrying with simpler prompt")

    simple_prompt = f"""Create ONE task to handle: {user_request}

    Agent options:
    {agent_summary}

    Respond ONLY with JSON:
    {{"tasks": [{{"description": "...", "agent_id": "...", "agent_name": "...", "dependencies": [], "rationale": "..."}}]}}
    """

    response = await llm.ainvoke([HumanMessage(content=simple_prompt)])
    plan_data = json.loads(response.content)
```

## Summary

**Planning Flow:**
1. Discover agents → 2. Build prompt → 3. LLM generates plan → 4. Parse JSON → 5. Create tasks

**Common Failures:**
- ❌ LLM wraps JSON in markdown → Strip code blocks
- ❌ Agent IDs don't match registry → Validate and skip
- ❌ No agents discovered → Check server connectivity
- ❌ LLM doesn't return JSON → Improve prompt clarity

**Best Practices:**
- ✅ Log raw LLM responses during debugging
- ✅ Strip markdown code blocks before parsing
- ✅ Validate agent IDs against registry
- ✅ Provide clear examples in prompts
- ✅ Add retry logic for robustness

Would you like me to implement the markdown stripping fix right now?
