"""
Router Agent State Definitions

This module defines the state schema for the Router Agent, including
supporting types for tasks, plans, and agent capabilities.
"""

from typing import TypedDict, Literal, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from datetime import datetime


class AgentCapability(TypedDict):
    """Agent capability information from agent card"""
    agent_id: str
    name: str
    capabilities: list[str]  # What the agent can do
    skills: list[str]        # Specific tasks it excels at
    description: str


class Task(TypedDict):
    """Represents a single task in the execution plan"""
    id: str
    description: str
    agent_id: str           # Which agent should handle this
    agent_name: str         # Friendly name for logging
    status: Literal["pending", "in_progress", "completed", "failed"]
    result: str | None      # Agent's response if completed
    error: str | None       # Error message if failed
    dependencies: list[str] # List of task IDs this depends on
    rationale: str          # Why this agent was chosen


class Plan(TypedDict):
    """Execution plan for handling user request"""
    tasks: list[Task]
    execution_strategy: Literal["sequential", "parallel"]
    created_at: datetime
    analysis: str  # LLM's analysis of the request


class RouterState(TypedDict):
    """
    Main state for Router Agent

    This state flows through all nodes and accumulates information
    as the request is processed.
    """

    # ========== A2A Compatibility (REQUIRED) ==========
    # The messages field is required for A2A protocol compatibility
    # It uses add_messages to accumulate conversation history
    messages: Annotated[list[BaseMessage], add_messages]

    # ========== Request Tracking ==========
    request_id: str
    original_request: str

    # ========== Validation (Guardrails) ==========
    is_valid: bool
    rejection_reason: str | None

    # ========== Planning (Task Breakdown) ==========
    plan: Plan | None
    plan_approved: bool  # For INTERACTIVE/REVIEW modes

    # ========== Execution (Orchestrator) ==========
    current_task_index: int
    need_replan: bool
    replan_reason: str | None

    # ========== Results ==========
    task_results: list[Task]  # Completed tasks with results
    final_response: str | None

    # ========== Configuration ==========
    mode: Literal["auto", "interactive", "review"]
    max_replans: int
    replan_count: int

    # ========== Streaming/Status ==========
    status_events: list[dict]  # For streaming progress updates
