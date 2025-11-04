# Streaming Guide for Router Agent

This guide explains how to stream intermediate progress updates from the Router Agent as it executes.

## Overview

Streaming allows you to receive real-time updates as the Router Agent progresses through its workflow:
- **Validation** → **Planning** → **Execution** → **Analysis** → **Aggregation**

This provides better UX by showing users what's happening instead of waiting for final results.

## Quick Start

### Basic Streaming Example

```python
from langgraph_sdk import get_client
import asyncio

async def stream_router():
    client = get_client(url="http://localhost:2024")

    async for chunk in client.runs.stream(
        None,  # Threadless run
        "router",
        input={
            "messages": [{"role": "user", "content": "Your request here"}]
        },
        stream_mode="updates"  # Get updates after each node
    ):
        # Process updates
        if chunk.event == "updates":
            for node_name, node_data in chunk.data.items():
                print(f"✓ {node_name} completed")

asyncio.run(stream_router())
```

## Stream Modes

LangGraph supports several streaming modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| `updates` | State updates after each node | **Recommended** - Track Router progress |
| `values` | Full state after each step | When you need complete state |
| `messages` | LLM tokens as they generate | Real-time LLM output |
| `debug` | Detailed execution info | Debugging |
| `custom` | Custom data from nodes | Advanced progress tracking |

## Stream Mode: `updates` (Recommended)

This mode provides the cleanest way to track Router Agent progress.

### What You Get

After each node completes, you receive:
- Node name (e.g., "validate", "plan", "execute")
- State updates from that node
- Task results (during execution)
- Plan details (after planning)

### Example with Progress Display

```python
async for chunk in client.runs.stream(
    None,
    "router",
    input={"messages": [{"role": "user", "content": "Fix bugs"}]},
    stream_mode="updates"
):
    if chunk.event == "updates":
        for node_name, node_data in chunk.data.items():

            if node_name == "validate":
                is_valid = node_data.get("is_valid")
                print(f"✓ Validation: {'PASS' if is_valid else 'FAIL'}")

            elif node_name == "plan":
                tasks = node_data.get("plan", {}).get("tasks", [])
                print(f"✓ Plan created with {len(tasks)} tasks")

            elif node_name == "execute":
                results = node_data.get("task_results", [])
                completed = len([r for r in results if r["status"] == "completed"])
                print(f"✓ Execution: {completed}/{len(results)} tasks done")

            elif node_name == "aggregate":
                response = node_data.get("final_response", "")
                print(f"✓ Response ready ({len(response)} chars)")
```

## Stream Mode: `values`

Get the complete Router state after each super-step.

```python
async for chunk in client.runs.stream(
    None,
    "router",
    input={...},
    stream_mode="values"
):
    state = chunk.data

    # Access full state
    if "plan" in state:
        print(f"Current plan: {state['plan']}")

    if "task_results" in state:
        print(f"Task results: {state['task_results']}")
```

## Stream Mode: `custom` (Advanced)

For fine-grained progress tracking, emit custom updates from within nodes.

### 1. Add Custom Updates to Nodes

```python
from langchain_core.runnables import RunnableConfig

async def execute_tasks(state: RouterState, config: RunnableConfig) -> dict:
    # Get stream writer
    writer = config.get("configurable", {}).get("__stream_writer")

    for idx, task in enumerate(tasks):
        # Emit custom progress
        if writer:
            writer({
                "type": "task_start",
                "task": task["description"],
                "progress": f"{idx + 1}/{len(tasks)}"
            })

        # Execute task...
        result = await _invoke_agent(task, ...)

        # Emit completion
        if writer:
            writer({
                "type": "task_complete",
                "task": task["description"],
                "status": result["status"]
            })

    return {"task_results": results}
```

### 2. Stream with Custom Mode

```python
async for chunk in client.runs.stream(
    None,
    "router",
    input={...},
    stream_mode=["updates", "custom"]  # Combine modes
):
    if chunk.event == "custom":
        data = chunk.data
        if data.get("type") == "task_start":
            print(f"Starting: {data['task']} ({data['progress']})")
        elif data.get("type") == "task_complete":
            print(f"Completed: {data['task']} - {data['status']}")
```

## Combining Multiple Stream Modes

You can combine modes to get different types of updates:

```python
async for chunk in client.runs.stream(
    None,
    "router",
    input={...},
    stream_mode=["updates", "messages", "custom"]
):
    if chunk.event == "updates":
        # Node completion updates
        print(f"Node: {chunk.data}")

    elif chunk.event == "messages":
        # LLM token streaming
        print(f"Token: {chunk.data}")

    elif chunk.event == "custom":
        # Your custom progress
        print(f"Custom: {chunk.data}")
```

## Running the Test

We've provided a comprehensive streaming test:

```bash
python test_router_streaming.py
```

This will show:
- ✅ Real-time progress as each node completes
- 📋 Plan details with tasks and agent assignments
- 📊 Task execution progress
- 📝 Final response preview

## Expected Output

```
======================================================================
Router Agent Streaming Test
======================================================================

📤 Request: Analyze my code for security vulnerabilities and provide fixes

🚀 Starting Router Agent...

──────────────────────────────────────────────────────────────────────
✓ VALIDATE
──────────────────────────────────────────────────────────────────────
  ✅ Request validated: ON-TOPIC

──────────────────────────────────────────────────────────────────────
✓ PLAN
──────────────────────────────────────────────────────────────────────
  📋 Strategy: SEQUENTIAL
  📝 Analysis: Security analysis requires both scanning and remediation
  🎯 Tasks: 2

  1. Scan codebase for security vulnerabilities
     → Agent: QuickAgent
     → Rationale: Fast initial scan for common issues

  2. Generate security fixes for identified issues
     → Agent: SlowAgent
     → Rationale: Deep analysis needed for proper remediation

──────────────────────────────────────────────────────────────────────
✓ EXECUTE
──────────────────────────────────────────────────────────────────────
  📊 Results: 2 ✅ | 0 ❌ | 0 ⏳

  1. ✅ Scan codebase for security vulnerabilities
     Agent: QuickAgent
     Status: completed
     Result: ## Quick Security Scan Complete...

  2. ✅ Generate security fixes for identified issues
     Agent: SlowAgent
     Status: completed
     Result: ## Deep Analysis Complete...

──────────────────────────────────────────────────────────────────────
✓ ANALYZE
──────────────────────────────────────────────────────────────────────
  ✅ Results are sufficient
  Proceeding to aggregation...

──────────────────────────────────────────────────────────────────────
✓ AGGREGATE
──────────────────────────────────────────────────────────────────────
  📝 Final response generated (1547 characters)
  ──────────────────────────────────────────────────────────────────
  FINAL RESPONSE:
  ──────────────────────────────────────────────────────────────────
  # Security Analysis Results

  Based on comprehensive analysis of your codebase...

✅ Router Agent completed successfully!

======================================================================
```

## Integration Tips

### 1. Web Applications

For web apps, convert stream chunks to Server-Sent Events (SSE):

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(request: dict):
    client = get_client(url="http://localhost:2024")

    async def event_stream():
        async for chunk in client.runs.stream(
            None,
            "router",
            input=request,
            stream_mode="updates"
        ):
            # Convert to SSE format
            yield f"data: {json.dumps(chunk.data)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### 2. CLI Applications

For command-line tools, use rich progress bars:

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

async def run_with_progress():
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Router Agent", total=None)

        async for chunk in client.runs.stream(...):
            if chunk.event == "updates":
                for node_name in chunk.data.keys():
                    progress.update(task, description=f"Running {node_name}...")
```

### 3. React Applications

Use the `useStream()` hook (see LangGraph React docs):

```typescript
import { useStream } from "@langgraph/react";

function ChatComponent() {
  const stream = useStream({
    apiUrl: "http://localhost:2024",
    assistantId: "router",
    messagesKey: "messages"
  });

  // stream.messages, stream.isLoading, etc.
}
```

## Best Practices

1. ✅ **Use `updates` mode** for most use cases - it's clean and efficient
2. ✅ **Handle errors gracefully** - wrap streaming in try/catch
3. ✅ **Show meaningful progress** - translate node names to user-friendly messages
4. ✅ **Consider latency** - streaming adds small overhead but greatly improves UX
5. ✅ **Test thoroughly** - ensure your UI handles all node types

## Troubleshooting

### Issue: No chunks received

**Solution**: Make sure you're using `async for` and awaiting the stream:
```python
async for chunk in client.runs.stream(...):  # ✅ Correct
    ...

for chunk in client.runs.stream(...):  # ❌ Wrong - won't work
    ...
```

### Issue: Getting entire state when only updates needed

**Solution**: Use `stream_mode="updates"` instead of `stream_mode="values"`

### Issue: Missing intermediate steps

**Solution**: Each node must return state updates. Check that all nodes return dictionaries with state changes.

## Additional Resources

- [LangGraph Streaming Docs](https://docs.langchain.com/oss/python/langgraph/streaming)
- [LangGraph Server Streaming](https://docs.langchain.com/langsmith/streaming)
- [React Integration](https://docs.langchain.com/langsmith/use-stream-react)

## Summary

Streaming provides real-time feedback during Router Agent execution:
- 🎯 Use `stream_mode="updates"` for clean node-by-node progress
- 🎯 Process chunks in `async for` loops
- 🎯 Display user-friendly progress based on node names
- 🎯 Run `test_router_streaming.py` to see it in action

Happy streaming! 🚀
