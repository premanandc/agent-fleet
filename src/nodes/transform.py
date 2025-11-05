"""
Transformation Nodes

These nodes convert between external API interfaces and internal state:
- transform_input: RouterInput (2 fields) → RouterState (23 fields)
- transform_output: RouterState (23 fields) → RouterOutput (1-3 fields)

This allows the Router to have a clean external API while maintaining
rich internal state for orchestration.
"""

import uuid
import logging
from ..models.router_interface import RouterInput, RouterOutput
from ..models.router_state import RouterState

logger = logging.getLogger(__name__)


def transform_input(input_data: RouterInput) -> RouterState:
    """
    Transform external API input to internal state

    Expands minimal RouterInput (2 fields) into full RouterState (23 fields).
    Called at the start of the graph before any processing begins.

    Args:
        input_data: External input from A2A/MCP client

    Returns:
        Full internal state initialized for processing
    """

    # Extract user's latest message for tracking
    user_message = ""
    if input_data.get("messages"):
        last_msg = input_data["messages"][-1]
        if hasattr(last_msg, 'content'):
            user_message = last_msg.content
        elif isinstance(last_msg, dict):
            user_message = last_msg.get('content', '')

    # Get mode from input, default to "auto"
    mode = input_data.get("mode", "auto")

    logger.info(f"Transforming input: mode={mode}, message_length={len(user_message)}")

    # Initialize full internal state from minimal input
    state: RouterState = {
        # ========== From External Input ==========
        "messages": input_data["messages"],
        "mode": mode,

        # ========== Request Tracking ==========
        "request_id": str(uuid.uuid4()),
        "original_request": user_message,

        # ========== Validation (Guardrails) ==========
        "is_valid": False,
        "rejection_reason": None,

        # ========== Planning (Task Breakdown) ==========
        "plan": None,
        "plan_approved": False,

        # ========== Execution (Orchestrator) ==========
        "current_task_index": 0,
        "need_replan": False,
        "replan_reason": None,

        # ========== Results ==========
        "task_results": [],
        "final_response": None,

        # ========== Configuration ==========
        "max_replans": 3,
        "replan_count": 0,

        # ========== Streaming/Status ==========
        "status_events": []
    }

    return state


def transform_output(state: RouterState) -> RouterOutput:
    """
    Transform internal state to external API output

    Reduces full RouterState (23 fields) to minimal RouterOutput (1-3 fields).
    Called at the end of the graph after all processing is complete.

    Args:
        state: Full internal state after processing

    Returns:
        Minimal external output for A2A/MCP client
    """

    # Always include final response
    output: RouterOutput = {
        "final_response": state.get("final_response", "No response generated")
    }

    # Add optional metadata for transparency
    task_results = state.get("task_results", [])

    if task_results:
        # Extract unique agent names from completed tasks
        agents_used = list(set(
            task["agent_name"]
            for task in task_results
            if task.get("status") == "completed"
        ))

        if agents_used:
            output["agents_used"] = sorted(agents_used)  # Sort for consistency

    # Add execution strategy if plan exists
    if state.get("plan"):
        output["execution_strategy"] = state["plan"]["execution_strategy"]

    logger.info(
        f"Transforming output: response_length={len(output['final_response'])}, "
        f"agents={output.get('agents_used', [])}"
    )

    return output
