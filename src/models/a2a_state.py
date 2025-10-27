"""A2A-compatible state definitions for the task breakdown agent."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class A2AAgentState(TypedDict):
    """A2A-compatible state for the task breakdown agent.

    The `messages` key is required for A2A protocol compatibility.

    Attributes:
        messages: List of messages exchanged (required for A2A)
        steps: List of simple steps the task has been broken into
        analysis: The LLM's reasoning about why and how the task was broken down
        needs_breakdown: Whether the task needs to be broken down into steps
    """

    messages: Annotated[list[BaseMessage], add_messages]
    steps: list[str]
    analysis: str
    needs_breakdown: bool
