# Agent Fleet Architecture

This document provides comprehensive technical documentation for the Agent Fleet system, detailing the Router Agent's internal architecture, A2A protocol implementation, and execution flow.

## Table of Contents

1. [System Overview](#system-overview)
2. [Router Agent Workflow](#router-agent-workflow)
3. [Node Descriptions](#node-descriptions)
4. [State Model](#state-model)
5. [Agent Discovery](#agent-discovery)
6. [A2A Protocol Implementation](#a2a-protocol-implementation)
7. [Planning System](#planning-system)
8. [Task Execution](#task-execution)
9. [Dependency Management](#dependency-management)

## System Overview

The Agent Fleet is a multi-agent orchestration system built on LangGraph, using the A2A (Agent-to-Agent) protocol for inter-agent communication. The Router Agent acts as an intelligent orchestrator that:

1. Validates incoming requests against ITEP platform scope
2. Dynamically discovers available agents via A2A protocol
3. Decomposes complex requests into tasks based on agent capabilities
4. Coordinates task execution (parallel or sequential)
5. Aggregates results into coherent responses

### Key Architectural Principles

- **Capability-Driven**: Task assignment based on agent capabilities, not hardcoded rules
- **Dynamic Discovery**: Agents are discovered at runtime via A2A agent cards
- **Protocol-Based Communication**: All inter-agent communication uses A2A (JSON-RPC over HTTP)
- **Async-First**: Non-blocking I/O throughout using httpx
- **Stateful Workflows**: LangGraph state machine with checkpointing support

## Router Agent Workflow

The Router Agent implements a 7-node workflow using LangGraph's StateGraph:

```
[Start] → [Validate] → [Plan] → [Approval] → [Execute] → [Analyze] → [Aggregate] → [End]
            ↓                                                   ↓
          [Reject]                                         [Replan if needed]
```

### Workflow Flow

1. **Start**: User submits request with messages
2. **Validate**: Check if request is on-topic for ITEP platform
   - ✅ Valid → Continue to Plan
   - ❌ Invalid → Route to Reject
3. **Reject**: Generate helpful rejection message and end
4. **Plan**: Discover agents, decompose request, create execution plan
5. **Approval**: (Interactive mode only) Pause for human approval
6. **Execute**: Invoke subordinate agents via A2A protocol
7. **Analyze**: Evaluate if results are sufficient
   - ✅ Sufficient → Continue to Aggregate
   - ❌ Insufficient → Replan (set `need_replan=True`)
8. **Aggregate**: Synthesize final response from all results
9. **End**: Return final response to user

### Execution Modes

**Auto Mode (default)**:
```
Validate → Plan → Execute → Analyze → Aggregate
```

**Interactive Mode**:
```
Validate → Plan → Approval → Execute → Analyze → Aggregate
                     ↓
              [User approves/rejects]
```

**Review Mode**:
```
Validate → Plan → Approval → Execute → Analyze → Aggregate
                     ↓
              [Auto-approve, log for transparency]
```

## Node Descriptions

### 1. Validate Node (`src/nodes/validate.py`)

**Purpose**: Guardrails to filter out-of-scope requests

**Implementation**:
- Uses LLM to classify requests as "valid" or "invalid"
- Checks against ITEP platform scope (CI/CD, code quality, DevOps, testing)
- Returns validation decision with reasoning

**Input**: `RouterState` with user messages
**Output**: Updates `is_valid` and `validation_message`

**Example Prompts**:
- ✅ Valid: "Fix SonarQube violations in my code"
- ❌ Invalid: "What's the weather today?"

### 2. Reject Node (`src/nodes/reject.py`)

**Purpose**: Handle rejected requests gracefully

**Implementation**:
- Generates polite rejection message
- Explains why request was out of scope
- Suggests rephrasing or clarifying intent

**Input**: `RouterState` with `is_valid=False`
**Output**: Updates `final_response` with rejection message

### 3. Plan Node (`src/nodes/plan.py`)

**Purpose**: Discover agents and create execution plan

**Implementation**:
1. **Discover Agents**: Call `discover_agents_from_langgraph()`
   - Queries `/assistants/search`
   - Fetches A2A agent cards
   - Builds capability registry
2. **Analyze Request**: Use LLM to understand user intent
3. **Decompose**: Break into specific, actionable tasks
4. **Match**: Assign tasks to agents based on capabilities
5. **Order**: Determine execution strategy (parallel/sequential)

**Input**: `RouterState` with validated request
**Output**: Updates `plan` with tasks, strategy, and analysis

**LLM Prompt Structure**:
```
USER REQUEST: <user message>

AVAILABLE AGENTS:
- AgentName (ID: xxx):
  Capabilities: [list]
  Skills: [list]
  Description: <description>

Create an execution plan in JSON format:
{
  "analysis": "...",
  "execution_strategy": "parallel|sequential",
  "tasks": [
    {
      "description": "...",
      "agent_id": "...",
      "agent_name": "...",
      "dependencies": [],
      "rationale": "..."
    }
  ]
}
```

### 4. Approval Node (`src/nodes/approval.py`)

**Purpose**: Human-in-the-loop approval (interactive mode only)

**Implementation**:
- Uses LangGraph's `interrupt()` to pause execution
- Presents plan to user for review
- Waits for approval/rejection
- Resumes or cancels based on user decision

**Input**: `RouterState` with `plan`
**Output**: Pauses execution, waits for resume signal

**Modes**:
- **auto**: Skipped entirely
- **interactive**: Pauses for user approval
- **review**: Logs plan but auto-approves

### 5. Execute Node (`src/nodes/execute.py`)

**Purpose**: Execute tasks by invoking subordinate agents via A2A

**Implementation**:
1. **Dependency Resolution**: Determine which tasks can run
2. **Parallel Execution**: Execute independent tasks concurrently
3. **A2A Invocation**: Call agents using A2A SDK
4. **Result Collection**: Gather and store task results
5. **Iteration**: Repeat until all tasks complete

**Input**: `RouterState` with `plan`
**Output**: Updates `task_results` with completed tasks

**Key Features**:
- Respects task dependencies
- Executes independent tasks in parallel
- Handles multiple execution rounds for sequential dependencies
- Includes dependency context in agent messages

### 6. Analyze Node (`src/nodes/analyze.py`)

**Purpose**: Evaluate if results are sufficient

**Implementation**:
- Uses LLM to assess result quality
- Compares results against original request
- Determines if replanning is needed

**Input**: `RouterState` with `task_results`
**Output**: Updates `need_replan` flag

**Decision Criteria**:
- Are all tasks completed successfully?
- Do results answer the user's question?
- Is additional information needed?

### 7. Aggregate Node (`src/nodes/aggregate.py`)

**Purpose**: Synthesize final response from all task results

**Implementation**:
- Collects all task results
- Uses LLM to create coherent summary
- Combines insights from multiple agents
- Generates user-friendly final response

**Input**: `RouterState` with `task_results`
**Output**: Updates `final_response`

**LLM Prompt Structure**:
```
Original request: <user message>

Task results:
- Task: <description>
  Agent: <name>
  Result: <agent response>

Synthesize a coherent final response that:
1. Directly answers the user's request
2. Integrates insights from all agents
3. Is clear and actionable
```

## State Model

The Router Agent uses a typed state model defined in `src/models/router_state.py`:

```python
class Task(TypedDict):
    """Individual task to be executed"""
    id: str                      # Unique task identifier
    description: str             # What needs to be done
    agent_id: str                # Which agent to use
    agent_name: str              # Agent name for logging
    status: Literal["pending", "in_progress", "completed", "failed"]
    result: Optional[str]        # Agent response
    dependencies: List[str]      # Task IDs that must complete first
    rationale: str               # Why this agent was chosen

class Plan(TypedDict):
    """Execution plan with tasks"""
    tasks: List[Task]
    execution_strategy: Literal["parallel", "sequential"]
    created_at: datetime
    analysis: str                # LLM's analysis of the request

class AgentCapability(TypedDict):
    """Agent metadata from A2A card"""
    agent_id: str
    name: str
    capabilities: List[str]
    skills: List[str]
    description: str

class RouterState(TypedDict):
    """Main state flowing through the graph"""
    messages: Annotated[List[BaseMessage], add_messages]  # A2A compatible
    is_valid: bool
    validation_message: str
    plan: Optional[Plan]
    task_results: List[Task]
    need_replan: bool
    final_response: str
```

### State Flow

1. **Initial State**: `messages` from user
2. **After Validate**: `is_valid`, `validation_message` set
3. **After Plan**: `plan` created with tasks
4. **After Execute**: `task_results` populated
5. **After Analyze**: `need_replan` determined
6. **After Aggregate**: `final_response` created

## Agent Discovery

The Router dynamically discovers subordinate agents at planning time using the A2A protocol.

### Discovery Process (`src/utils/discovery.py`)

```python
async def discover_agents_from_langgraph() -> Dict[str, AgentCapability]:
    """
    1. GET /assistants/search - Find all assistants
    2. Filter - Remove router itself
    3. GET /.well-known/agent-card.json?assistant_id={id} - Fetch agent cards
    4. Extract - Parse capabilities and skills from cards
    5. Build - Create registry mapping agent_id -> AgentCapability
    """
```

### Helper Functions

**`_get_langgraph_url()`**: Extract server URL from environment

**`_is_subordinate_agent(graph_id)`**: Filter out router itself

**`_extract_capabilities_from_card(card, graph_id, assistant_id)`**: Parse A2A card JSON into `AgentCapability`

**`_fetch_all_assistants(client, url)`**: HTTP GET to `/assistants/search`

**`_fetch_agent_card(client, url, assistant_id, graph_id)`**: HTTP GET to agent card endpoint with error handling

**`_build_agent_registry(client, url, assistants)`**: Iterate through assistants and build registry

### Agent Card Format

```json
{
  "name": "QuickAgent",
  "description": "Fast analysis agent for quick validation tasks",
  "skills": [
    {"name": "Analyze code syntax"},
    {"name": "Quick validation"},
    {"name": "Check code style"}
  ],
  "capabilities": ["analysis", "quick-check", "validation"]
}
```

### Registry Example

```python
{
  "8dc97659-9c90-5a08-b493-8b99583b8333": {
    "agent_id": "8dc97659-9c90-5a08-b493-8b99583b8333",
    "name": "QuickAgent",
    "capabilities": ["analysis", "quick-check", "validation"],
    "skills": ["Analyze code syntax", "Quick validation", ...],
    "description": "Fast analysis agent..."
  },
  "d64f349d-bdc0-5361-9fb3-a61d5a3c4e10": {
    "agent_id": "d64f349d-bdc0-5361-9fb3-a61d5a3c4e10",
    "name": "SlowAgent",
    "capabilities": ["deep-analysis", "remediation", "sonarqube"],
    "skills": ["Fix SonarQube violations", ...],
    "description": "Deep analysis agent..."
  }
}
```

## A2A Protocol Implementation

The Router uses the official `a2a-sdk` package for agent communication.

### SDK Usage (`src/nodes/execute.py`)

```python
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams, AgentCard

async def invoke_agent(agent_id: str, message: str):
    async with httpx.AsyncClient() as client:
        # 1. Fetch agent card
        card_response = await client.get(
            f"{langgraph_url}/.well-known/agent-card.json",
            params={"assistant_id": agent_id}
        )
        agent_card_data = card_response.json()

        # 2. Parse into Pydantic model
        agent_card = AgentCard(**agent_card_data)

        # 3. Create A2A client
        a2a_client = A2AClient(
            httpx_client=client,
            agent_card=agent_card,
            url=f"{langgraph_url}/a2a/{agent_id}"
        )

        # 4. Prepare message
        request = SendMessageRequest(
            id=task_id,
            params=MessageSendParams(
                message={
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': message}],
                    'messageId': f"msg_{task_id}"
                },
                thread={'threadId': f"thread_{task_id}"}
            )
        )

        # 5. Send message (JSON-RPC handled by SDK)
        response = await a2a_client.send_message(request)

        # 6. Extract result from response.root
        if isinstance(response.root, SendMessageSuccessResponse):
            result = response.root.result  # Task or Message
            if isinstance(result, Message):
                text_parts = [p.text for p in result.parts if p.kind == 'text']
                return "\n".join(text_parts)
```

### Key Points

**LangGraph-Specific Behavior**:
- Agent cards use query parameters: `?assistant_id={id}`
- Not path-based like standard A2A spec

**Pydantic Models**:
- `AgentCard`: Must parse JSON into object, not use dict
- `SendMessageResponse`: RootModel, access via `.root`

**Error Handling**:
- Check `isinstance(response.root, SendMessageSuccessResponse)`
- Handle both `Message` and `Task` result types
- Extract text from message parts

## Planning System

The planning system is the brain of the Router Agent.

### Planning Flow

1. **Discover Agents**: Build registry of available capabilities
2. **Build Prompt**: Create detailed prompt with request and agent registry
3. **LLM Analysis**: Get plan as JSON from LLM
4. **Parse JSON**: Handle markdown code blocks if present
5. **Validate**: Check agent IDs exist in registry
6. **Create Tasks**: Build `Task` objects with unique IDs

### JSON Response Format

```json
{
  "analysis": "Request requires deep analysis and SonarQube expertise",
  "execution_strategy": "sequential",
  "tasks": [
    {
      "description": "Analyze and fix SonarQube violations",
      "agent_id": "d64f349d-bdc0-5361-9fb3-a61d5a3c4e10",
      "agent_name": "SlowAgent",
      "dependencies": [],
      "rationale": "SlowAgent has deep-analysis and remediation capabilities"
    }
  ]
}
```

### Common Issues

**Markdown Wrapped JSON**:
- LLMs often return: ` ```json\n{...}\n``` `
- Solution: Strip code blocks before parsing

**Agent ID Mismatch**:
- LLM returns IDs not in registry
- Solution: Validate and skip invalid tasks

**Empty Task List**:
- No agents discovered or all tasks skipped
- Solution: Check discovery logs and agent IDs

## Task Execution

Task execution handles dependencies and parallel execution.

### Dependency Resolution

```python
def _are_dependencies_met(task: Task, completed_tasks: Dict[str, Task]) -> bool:
    """Check if all task dependencies are completed successfully"""
    if not task.get("dependencies"):
        return True

    for dep_id in task["dependencies"]:
        if dep_id not in completed_tasks:
            return False
        if completed_tasks[dep_id]["status"] != "completed":
            return False

    return True
```

### Execution Rounds

Tasks execute in multiple rounds until all complete:

```python
completed_tasks = {}
max_rounds = 10

for round_num in range(max_rounds):
    # Find executable tasks
    executable = [
        t for t in pending_tasks
        if _are_dependencies_met(t, completed_tasks)
    ]

    if not executable:
        break  # All done or deadlock

    # Execute in parallel
    results = await asyncio.gather(*[
        _invoke_agent(task) for task in executable
    ])

    # Update completed tasks
    for task, result in zip(executable, results):
        task["status"] = "completed"
        task["result"] = result
        completed_tasks[task["id"]] = task
```

### Dependency Context

Tasks include results from dependencies in their messages:

```python
# Build context from dependencies
dependency_context = ""
if task.get("dependencies"):
    dependency_context = "\n\nContext from previous tasks:\n"
    for dep_id in task["dependencies"]:
        if dep_id in completed_tasks:
            dep_task = completed_tasks[dep_id]
            dependency_context += f"- {dep_task['description']}: {dep_task.get('result', 'N/A')}\n"

# Build message
agent_message = f"""Original user request: {original_request}

Your specific task: {task_description}
{dependency_context}

Please complete this task and provide your findings.
"""
```

## Dependency Management

### Execution Patterns

**Independent Tasks (Parallel)**:
```
Task A (no deps) ─┐
Task B (no deps) ─┼─> Round 1: Execute A, B, C in parallel
Task C (no deps) ─┘
```

**Sequential Dependencies**:
```
Task A (no deps) ───> Round 1: Execute A
  ↓
Task B (deps: [A]) ──> Round 2: Execute B after A completes
  ↓
Task C (deps: [B]) ──> Round 3: Execute C after B completes
```

**Fan-out/Fan-in**:
```
Task A (no deps) ───────> Round 1: Execute A
  ↓
  ├─> Task B (deps: [A]) ┐
  └─> Task C (deps: [A]) ┼> Round 2: Execute B, C in parallel
                         ↓
Task D (deps: [B, C]) ───> Round 3: Execute D after B and C
```

### Example Scenarios

**Scenario 1: Quick validation**
```json
{
  "execution_strategy": "sequential",
  "tasks": [
    {
      "id": "task_001",
      "description": "Quick syntax check",
      "agent_id": "quick_agent_id",
      "dependencies": []
    }
  ]
}
```

**Scenario 2: Multi-step analysis**
```json
{
  "execution_strategy": "sequential",
  "tasks": [
    {
      "id": "task_001",
      "description": "Quick scan for obvious issues",
      "agent_id": "quick_agent_id",
      "dependencies": []
    },
    {
      "id": "task_002",
      "description": "Deep analysis and remediation",
      "agent_id": "slow_agent_id",
      "dependencies": ["task_001"]
    }
  ]
}
```

## Performance Considerations

### Async Operations

All I/O is non-blocking:
- Agent discovery uses `httpx.AsyncClient`
- Agent invocation uses async A2A SDK
- Multiple tasks execute concurrently with `asyncio.gather`

### Caching

Currently no caching, but future enhancements:
- Cache agent registry for short periods
- Cache LLM responses for identical requests
- Cache agent card fetches

### Timeouts

Configurable timeouts at each level:
- HTTP requests: 10s for discovery, 300s for execution
- LLM calls: Default timeout from provider
- Overall workflow: Managed by LangGraph

### Error Handling

Graceful degradation:
- Agent discovery failure → log warning, continue with available agents
- Agent invocation failure → mark task as failed, continue other tasks
- JSON parsing failure → log error, return empty plan
- Dependency deadlock → detect and fail gracefully

## Summary

The Agent Fleet architecture provides a robust, scalable foundation for multi-agent orchestration using industry-standard protocols (A2A) and modern async Python patterns. The capability-driven approach enables dynamic agent discovery and flexible task assignment without hardcoded assumptions, making the system extensible and maintainable.
