"""
Router Agent - Main Graph Assembly

Assembles the Router Agent graph with all nodes and conditional edges.
This is the factory function that LangGraph Server calls to instantiate the agent.
"""

import uuid
import logging
import asyncio
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from ..models.router_state import RouterState
from ..nodes import (
    validate_request,
    reject_request,
    generate_plan,
    await_approval,
    execute_tasks,
    analyze_results,
    aggregate_results
)
from ..utils import discover_agents_from_langgraph

logger = logging.getLogger(__name__)


def create_router_graph(config: RunnableConfig = None):
    """
    Factory function to create the Router Agent graph

    This function is called by LangGraph Server to instantiate the Router Agent.
    It performs agent discovery at creation time and assembles the state graph.

    Args:
        config: LangGraph runtime configuration (optional)

    Returns:
        Compiled StateGraph ready for execution
    """

    logger.info("Initializing Router Agent...")

    # Note: Agent discovery is now done lazily in the plan node
    # to avoid blocking during graph initialization
    agent_registry = {}
    logger.info("Agent discovery will occur during planning")

    # Create state graph
    graph = StateGraph(RouterState)

    # ========== Add Nodes ==========
    graph.add_node("validate", validate_request)
    graph.add_node("reject", reject_request)
    graph.add_node("plan", generate_plan)
    graph.add_node("approval", await_approval)
    graph.add_node("execute", execute_tasks)
    graph.add_node("analyze", analyze_results)
    graph.add_node("aggregate", aggregate_results)

    # ========== Define Conditional Edges ==========

    def route_after_validation(state: RouterState) -> Literal["plan", "reject"]:
        """Route based on validation result"""
        if state.get("is_valid", False):
            return "plan"
        else:
            return "reject"

    def route_after_planning(state: RouterState) -> Literal["approval", "execute"]:
        """Route based on mode - skip approval in AUTO mode"""
        mode = state.get("mode", "auto")
        if mode == "auto":
            return "execute"
        else:
            return "approval"

    def route_after_approval(state: RouterState) -> Literal["plan", "execute"]:
        """Route based on approval result"""
        if state.get("plan_approved", False):
            return "execute"
        else:
            # User rejected or requested modifications - replan
            return "plan"

    def route_after_analysis(state: RouterState) -> Literal["plan", "aggregate"]:
        """Route based on replan decision"""
        if state.get("need_replan", False):
            return "plan"
        else:
            return "aggregate"

    # ========== Build Graph Flow ==========

    # Entry point
    graph.add_edge(START, "validate")

    # After validation: route to plan or reject
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "plan": "plan",
            "reject": "reject"
        }
    )

    # Rejection path ends
    graph.add_edge("reject", END)

    # After planning: route to approval or execute (based on mode)
    graph.add_conditional_edges(
        "plan",
        route_after_planning,
        {
            "approval": "approval",
            "execute": "execute"
        }
    )

    # After approval: route based on approval result
    graph.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "plan": "plan",      # User rejected - replan
            "execute": "execute"  # User approved - execute
        }
    )

    # After execution: always analyze
    graph.add_edge("execute", "analyze")

    # After analysis: route to replan or aggregate
    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "plan": "plan",         # Need replan
            "aggregate": "aggregate"  # Results sufficient
        }
    )

    # After aggregation: end
    graph.add_edge("aggregate", END)

    # ========== Compile Graph ==========

    # Use MemorySaver for development/testing
    # In production, LangGraph Server provides persistence automatically
    checkpointer = MemorySaver()

    compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval"] if config and config.get("configurable", {}).get("mode") == "interactive" else None
    )

    # Store agent registry in graph config for nodes to access
    # This is a workaround - ideally we'd pass via config in invoke()
    compiled_graph.agent_registry = agent_registry

    logger.info("Router Agent initialized successfully")

    return compiled_graph


def create_initial_state(user_message: str, mode: str = "auto", max_replans: int = 2) -> RouterState:
    """
    Helper function to create initial state for Router Agent

    Args:
        user_message: The user's request
        mode: Execution mode (auto, interactive, review)
        max_replans: Maximum number of replanning attempts

    Returns:
        Initial RouterState
    """

    from langchain_core.messages import HumanMessage

    return {
        "messages": [HumanMessage(content=user_message)],
        "request_id": str(uuid.uuid4()),
        "original_request": user_message,
        "is_valid": False,
        "rejection_reason": None,
        "plan": None,
        "plan_approved": False,
        "current_task_index": 0,
        "need_replan": False,
        "replan_reason": None,
        "task_results": [],
        "final_response": None,
        "mode": mode,
        "max_replans": max_replans,
        "replan_count": 0,
        "status_events": []
    }


# ========== State Diagram Reference ==========
"""
Router Agent State Flow:

    START
      │
      ▼
┌─────────────┐
│  VALIDATE   │ (Guardrails)
└──────┬──────┘
       │
       ├─[valid]────────────────────────┐
       │                                │
       ├─[invalid]───┐                  │
       │             ▼                  ▼
       │        ┌─────────┐        ┌──────────┐
       │        │ REJECT  │        │   PLAN   │ (Task Breakdown)
       │        └────┬────┘        └─────┬────┘
       │             │                   │
       │             ▼                   ├─[auto mode]───────────┐
       │            END                  │                       │
       │                                 ├─[interactive/review]──┤
       │                                 │                       │
       │                                 │                  ┌────▼─────┐
       │                                 │                  │ APPROVAL │ (Human-in-loop)
       │                                 │                  └────┬─────┘
       │                                 │                       │
       │                                 │                       ├─[approved]──┐
       │                                 │                       │             │
       │                                 │◄──[rejected]──────────┘             │
       │                                 │                                     │
       │                                 ▼                                     ▼
       │                            ┌──────────┐                         ┌──────────┐
       │                            │ EXECUTE  │◄────────────────────────┤ (merge)  │
       │                            └────┬─────┘                         └──────────┘
       │                                 │
       │                                 ▼
       │                            ┌──────────┐
       │                            │ ANALYZE  │ (Replan Decision)
       │                            └────┬─────┘
       │                                 │
       │                                 ├─[need replan]───────┐
       │                                 │                     │
       │◄────────────────────────────────┘                     │
       │                                                       │
       │                                 ├─[sufficient]────────┘
       │                                 │
       │                                 ▼
       │                           ┌────────────┐
       │                           │ AGGREGATE  │ (Summarizer)
       │                           └──────┬─────┘
       │                                  │
       │                                  ▼
       └─────────────────────────────────END
"""
