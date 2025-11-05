"""
Router Agent Public Interface

Defines the external API surface for the Router Agent.
These types are used for A2A and MCP protocol interfaces.

The Router's internal state (RouterState) is not exposed externally.
Clients only see RouterInput (what to send) and RouterOutput (what to receive).
"""

from typing import TypedDict, NotRequired, Literal, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RouterInput(TypedDict):
    """
    Public API for invoking the Router Agent

    This is the external interface visible to:
    - A2A clients (other agents)
    - MCP clients (Claude Desktop, IDEs, etc.)

    All internal state (validation, planning, execution) is hidden.
    """

    # Required: User's request as A2A-compatible messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Optional: Execution mode (defaults to "auto")
    # - auto: Fully autonomous, no approval needed
    # - interactive: Pauses for plan approval (requires session support)
    # - review: Shows plan but auto-approves (transparency mode)
    mode: NotRequired[Literal["auto", "interactive", "review"]]


class RouterOutput(TypedDict):
    """
    Public API for Router Agent results

    This is what external clients receive after the Router completes.

    Minimal, focused output that answers the user's request without
    exposing internal orchestration details.
    """

    # Always returned: The final answer to the user's request
    final_response: str

    # Optional: Which agents were used (for transparency)
    agents_used: NotRequired[list[str]]

    # Optional: How work was organized (for transparency)
    execution_strategy: NotRequired[Literal["parallel", "sequential"]]
