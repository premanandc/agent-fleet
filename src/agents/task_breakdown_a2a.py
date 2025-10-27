"""A2A-compatible task breakdown agent using LangGraph."""

import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from src.llm.factory import LLMFactory, LLMProvider
from src.models.a2a_state import A2AAgentState


class TaskBreakdownA2AAgent:
    """A2A-compatible agent that breaks down complex tasks into simple steps."""

    def __init__(
        self,
        provider: LLMProvider = "anthropic",
        model: str | None = None,
        temperature: float = 0.7,
    ):
        """
        Initialize the A2A-compatible task breakdown agent.

        Args:
            provider: LLM provider to use ("openai" or "anthropic")
            model: Optional specific model name
            temperature: Temperature for LLM generation
        """
        self.llm: BaseChatModel = LLMFactory.create(
            provider=provider,
            model=model,
            temperature=temperature,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine for task breakdown."""
        workflow = StateGraph(A2AAgentState)

        # Add nodes
        workflow.add_node("analyze", self._analyze_task)
        workflow.add_node("breakdown", self._breakdown_task)
        workflow.add_node("respond", self._respond)

        # Set entry point
        workflow.set_entry_point("analyze")

        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze",
            self._should_breakdown,
            {
                "breakdown": "breakdown",
                "respond": "respond",
            },
        )

        # Add edges to respond node
        workflow.add_edge("breakdown", "respond")
        workflow.add_edge("respond", END)

        return workflow.compile()

    def _extract_task_from_messages(self, messages: list) -> str:
        """Extract the task from the messages list."""
        # Get the last human message as the task
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
        return ""

    def _analyze_task(self, state: A2AAgentState) -> A2AAgentState:
        """
        Analyze if the task needs to be broken down.

        Args:
            state: Current agent state

        Returns:
            Updated state with analysis and needs_breakdown flag
        """
        task = self._extract_task_from_messages(state["messages"])

        system_prompt = """You are a task analysis expert. Your job is to determine if a given task is simple enough to be executed as-is, or if it needs to be broken down into smaller steps.

A task needs breakdown if it:
- Contains multiple distinct actions or phases
- Requires coordination between different components or systems
- Involves complex decision-making or multiple dependencies
- Would take significant time or effort to complete in one go

A task does NOT need breakdown if it:
- Is a single, atomic action
- Can be completed in one straightforward step
- Is already clear and specific

Respond with:
1. Your reasoning about the task complexity
2. A clear YES or NO on whether it needs breakdown"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Task: {task}"),
        ]

        response = self.llm.invoke(messages)
        analysis = response.content

        # Simple heuristic: look for YES/NO in response
        needs_breakdown = "YES" in analysis.upper() and "NO" not in analysis.upper().split("YES")[0]

        return {
            **state,
            "analysis": analysis,
            "needs_breakdown": needs_breakdown,
        }

    def _breakdown_task(self, state: A2AAgentState) -> A2AAgentState:
        """
        Break down the task into simple steps.

        Args:
            state: Current agent state

        Returns:
            Updated state with broken down steps
        """
        task = self._extract_task_from_messages(state["messages"])

        system_prompt = """You are a task planning expert. Break down the given complex task into clear, actionable steps.

Guidelines:
- Each step should be specific and actionable
- Steps should be ordered logically
- Keep steps simple and focused on one action each
- Number each step (1., 2., 3., etc.)
- Aim for 3-7 steps for most tasks

Output ONLY the numbered list of steps, nothing else."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Task: {task}"),
        ]

        response = self.llm.invoke(messages)
        steps_text = response.content

        # Parse numbered steps
        steps = []
        for line in steps_text.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering/bullets and clean up
                step = line.lstrip("0123456789.-) ").strip()
                if step:
                    steps.append(step)

        return {
            **state,
            "steps": steps,
        }

    def _respond(self, state: A2AAgentState) -> A2AAgentState:
        """
        Create response message based on analysis and breakdown.

        Args:
            state: Current agent state

        Returns:
            Updated state with response message added
        """
        task = self._extract_task_from_messages(state["messages"])

        if state["needs_breakdown"] and state["steps"]:
            response = f"I've analyzed your task and broken it down into {len(state['steps'])} steps:\n\n"
            for i, step in enumerate(state["steps"], 1):
                response += f"{i}. {step}\n"
        else:
            response = f"This task is simple enough to execute as-is: {task}"

        return {
            **state,
            "messages": [AIMessage(content=response)],
        }

    def _should_breakdown(self, state: A2AAgentState) -> str:
        """
        Decide whether to breakdown the task or respond directly.

        Args:
            state: Current agent state

        Returns:
            Next node to execute ("breakdown" or "respond")
        """
        return "breakdown" if state["needs_breakdown"] else "respond"


def create_task_breakdown_graph(config: RunnableConfig):
    """
    Create and return a compiled A2A-compatible task breakdown graph.

    This is the entry point for LangGraph Server deployment.

    Args:
        config: RunnableConfig containing configuration and environment variables

    Returns:
        Compiled StateGraph ready for deployment
    """
    # Extract configuration from environment or config
    # You can customize provider via environment variable
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("LLM_MODEL", None)
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    agent = TaskBreakdownA2AAgent(
        provider=provider,
        model=model,
        temperature=temperature,
    )
    return agent.graph
