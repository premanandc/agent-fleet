"""
Router Agent Streaming Test

Demonstrates how to stream intermediate progress updates from the Router Agent
as it executes. Shows real-time feedback for each node and task execution.
"""

import asyncio
from langgraph_sdk import get_client


async def test_streaming_with_progress():
    """
    Test Router Agent with streaming to show intermediate progress

    Uses stream_mode="updates" to receive state updates after each node completes.
    Provides user-friendly progress display with emojis and formatting.
    """

    client = get_client(url="http://localhost:2024")

    print("=" * 70)
    print("Router Agent Streaming Test")
    print("=" * 70)
    print()

    test_request = "Set up a complete stack for a new Express API called 'user-service'"

    print(f"📤 Request: {test_request}")
    print()
    print("🚀 Starting Router Agent...\n")

    try:
        # Accumulate state as we stream
        accumulated_state = {}

        async for chunk in client.runs.stream(
            None,  # Threadless run
            "router",  # Assistant ID
            input={
                "messages": [{
                    "role": "user",
                    "content": test_request
                }]
            },
            stream_mode="debug",  # Debug mode gives access to internal state
            config={
                "configurable": {
                    "mode": "auto"  # Fully autonomous execution
                }
            }
        ):
            if chunk.event == "debug" and chunk.data:
                debug_type = chunk.data.get("type")
                payload = chunk.data.get("payload")

                # Only process task completions
                if debug_type == "task_result" and payload:
                    node_name = payload.get("name")
                    result = payload.get("result")  # State delta from this node
                    error = payload.get("error")

                    if error:
                        print(f"\n❌ {node_name.upper()} FAILED")
                        print(f"   Error: {error}")
                    elif node_name and result and isinstance(result, dict):
                        # Accumulate state updates
                        accumulated_state.update(result)
                        # Display using accumulated state
                        _display_node_progress(node_name, accumulated_state)

        print("\n✅ Router Agent completed successfully!\n")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        print("=" * 70)
        raise


def _display_node_progress(node_name: str, node_data: dict):
    """
    Display progress information for each node

    Args:
        node_name: Name of the node that completed
        node_data: Data returned by the node
    """

    # Node header
    print(f"{'─' * 70}")
    print(f"✓ {node_name.upper()}")
    print(f"{'─' * 70}")

    # Skip transformation nodes (they don't have user-visible output)
    if node_name in ["transform_input", "transform_output"]:
        print("  (Internal transformation)")
        print()
        return

    # Display node-specific information
    if node_name == "validate":
        _display_validation(node_data)

    elif node_name == "reject":
        _display_rejection(node_data)

    elif node_name == "plan":
        _display_plan(node_data)

    elif node_name == "execute":
        _display_execution(node_data)

    elif node_name == "analyze":
        _display_analysis(node_data)

    elif node_name == "aggregate":
        _display_aggregation(node_data)

    print()  # Blank line after each node


def _display_validation(data: dict):
    """Display validation results"""
    is_valid = data.get("is_valid", False)
    rejection_reason = data.get("rejection_reason", "")

    if is_valid:
        print("  ✅ Request validated: ON-TOPIC")
    else:
        print("  ❌ Request rejected: OFF-TOPIC")
        print(f"  Reason: {rejection_reason}")


def _display_rejection(data: dict):
    """Display rejection message"""
    rejection_reason = data.get("rejection_reason", "Unknown")
    print(f"  ❌ {rejection_reason}")


def _display_plan(data: dict):
    """Display execution plan"""
    plan = data.get("plan")
    if not plan:
        print("  ⚠️  No plan generated")
        return

    tasks = plan.get("tasks", [])
    strategy = plan.get("execution_strategy", "sequential")
    analysis = plan.get("analysis", "")

    print(f"  📋 Strategy: {strategy.upper()}")
    print(f"  📝 Analysis: {analysis}")
    print(f"  🎯 Tasks: {len(tasks)}")
    print()

    for idx, task in enumerate(tasks, 1):
        print(f"  {idx}. {task['description']}")
        print(f"     → Agent: {task['agent_name']}")
        print(f"     → Rationale: {task['rationale']}")

        if task.get("dependencies"):
            deps = ", ".join(task["dependencies"])
            print(f"     → Dependencies: {deps}")

        print()


def _display_execution(data: dict):
    """Display execution results"""
    task_results = data.get("task_results", [])

    if not task_results:
        print("  ⚠️  No tasks executed")
        return

    completed = len([r for r in task_results if r["status"] == "completed"])
    failed = len([r for r in task_results if r["status"] == "failed"])
    pending = len([r for r in task_results if r["status"] == "pending"])

    print(f"  📊 Results: {completed} ✅ | {failed} ❌ | {pending} ⏳")
    print()

    for idx, task in enumerate(task_results, 1):
        status_icon = {
            "completed": "✅",
            "failed": "❌",
            "pending": "⏳"
        }.get(task["status"], "❓")

        print(f"  {idx}. {status_icon} {task['description']}")
        print(f"     Agent: {task['agent_name']}")
        print(f"     Status: {task['status']}")

        if task["status"] == "completed":
            result_preview = task.get("result", "")[:100]
            print(f"     Result: {result_preview}...")
        elif task["status"] == "failed":
            error = task.get("error", "Unknown error")
            print(f"     Error: {error}")

        print()


def _display_analysis(data: dict):
    """Display analysis results"""
    need_replan = data.get("need_replan", False)
    replan_reason = data.get("replan_reason")
    replan_count = data.get("replan_count", 0)

    if need_replan:
        print(f"  ⚠️  Replanning needed (attempt #{replan_count})")
        print(f"  Reason: {replan_reason}")
    else:
        print("  ✅ Results are sufficient")
        print("  Proceeding to aggregation...")


def _display_aggregation(data: dict):
    """Display final aggregation"""
    final_response = data.get("final_response", "")

    print(f"  📝 Final response generated ({len(final_response)} characters)")
    print()
    print("  " + "─" * 66)
    print("  FINAL RESPONSE:")
    print("  " + "─" * 66)

    # Display response with indentation
    for line in final_response.split("\n")[:20]:  # First 20 lines
        print(f"  {line}")

    if len(final_response.split("\n")) > 20:
        print("  ...")
        print(f"  (Truncated - total {len(final_response.split())} lines)")


async def test_streaming_simple():
    """
    Simpler streaming test that just shows node names as they complete
    """

    client = get_client(url="http://localhost:2024")

    print("Simple Streaming Test")
    print("=" * 70)

    async for chunk in client.runs.stream(
        None,
        "router",
        input={
            "messages": [{
                "role": "user",
                "content": "Quick syntax check"
            }]
        },
        stream_mode="updates"
    ):
        if chunk.event == "updates" and chunk.data:
            for node_name in chunk.data.keys():
                print(f"✓ {node_name}")

    print("=" * 70)


async def test_streaming_raw():
    """
    Raw streaming test showing all chunk data (for debugging)
    """

    client = get_client(url="http://localhost:2024")

    print("Raw Streaming Test (Debug)")
    print("=" * 70)

    async for chunk in client.runs.stream(
        None,
        "router",
        input={
            "messages": [{
                "role": "user",
                "content": "Test request"
            }]
        },
        stream_mode="updates"
    ):
        print(f"\nEvent: {chunk.event}")
        print(f"Data: {chunk.data}")
        print("-" * 70)

    print("=" * 70)


async def main():
    """Run the streaming tests"""

    # Choose which test to run
    print("Running detailed streaming test with progress display...\n")
    await test_streaming_with_progress()

    # Uncomment to run other tests:
    # await test_streaming_simple()
    # await test_streaming_raw()


if __name__ == "__main__":
    asyncio.run(main())
