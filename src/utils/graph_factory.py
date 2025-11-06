"""
Graph Factory Utilities

Provides reusable graph construction patterns for agents.
"""

import logging
from typing import TypedDict, Type, Callable
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


def create_simple_provisioner_graph(
    agent_name: str,
    state_class: Type[TypedDict],
    input_class: Type[TypedDict],
    output_class: Type[TypedDict],
    transform_input_fn: Callable,
    validate_fn: Callable,
    provision_fn: Callable,
    transform_output_fn: Callable,
    config: RunnableConfig = None
):
    """
    Create a simple linear provisioner graph

    This pattern is common for provisioner agents that follow:
    START → transform_input → validate → provision → transform_output → END

    Args:
        agent_name: Name of the agent (for logging)
        state_class: Internal state TypedDict class
        input_class: External input TypedDict class
        output_class: External output TypedDict class
        transform_input_fn: Function to transform input
        validate_fn: Function to validate request
        provision_fn: Function to provision resource
        transform_output_fn: Function to transform output
        config: Optional LangGraph runtime configuration

    Returns:
        Compiled StateGraph ready for execution
    """

    logger.info(f"Initializing {agent_name}...")

    # Create state graph with explicit input/output schemas
    graph = StateGraph(
        state_class,      # Internal state
        input=input_class,    # External input
        output=output_class   # External output
    )

    # Add nodes
    graph.add_node("transform_input", transform_input_fn)
    graph.add_node("validate", validate_fn)
    graph.add_node("provision", provision_fn)
    graph.add_node("transform_output", transform_output_fn)

    # Build linear flow
    graph.add_edge(START, "transform_input")
    graph.add_edge("transform_input", "validate")
    graph.add_edge("validate", "provision")
    graph.add_edge("provision", "transform_output")
    graph.add_edge("transform_output", END)

    # Compile
    checkpointer = MemorySaver()
    compiled_graph = graph.compile(checkpointer=checkpointer)

    logger.info(f"{agent_name} initialized successfully")

    return compiled_graph
