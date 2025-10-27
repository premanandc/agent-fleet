"""State definitions for the task breakdown agent."""

from typing import TypedDict


class AgentState(TypedDict):
    """State for the task breakdown agent.

    Attributes:
        task: The original complex task to be broken down
        steps: List of simple steps the task has been broken into
        analysis: The LLM's reasoning about why and how the task was broken down
        needs_breakdown: Whether the task needs to be broken down into steps
    """

    task: str
    steps: list[str]
    analysis: str
    needs_breakdown: bool
