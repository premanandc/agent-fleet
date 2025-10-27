"""Task breakdown agent using LangGraph."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from src.llm.factory import LLMFactory, LLMProvider
from src.models.state import AgentState


class TaskBreakdownAgent:
    """Agent that breaks down complex tasks into simple steps using LangGraph."""

    def __init__(
        self,
        provider: LLMProvider = "anthropic",
        model: str | None = None,
        temperature: float = 0.7,
    ):
        """
        Initialize the task breakdown agent.

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
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze", self._analyze_task)
        workflow.add_node("breakdown", self._breakdown_task)

        # Set entry point
        workflow.set_entry_point("analyze")

        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze",
            self._should_breakdown,
            {
                "breakdown": "breakdown",
                "end": END,
            },
        )

        # Add edge from breakdown to end
        workflow.add_edge("breakdown", END)

        return workflow.compile()

    def _analyze_task(self, state: AgentState) -> AgentState:
        """
        Analyze if the task needs to be broken down.

        Args:
            state: Current agent state

        Returns:
            Updated state with analysis and needs_breakdown flag
        """
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
            HumanMessage(content=f"Task: {state['task']}"),
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

    def _breakdown_task(self, state: AgentState) -> AgentState:
        """
        Break down the task into simple steps.

        Args:
            state: Current agent state

        Returns:
            Updated state with broken down steps
        """
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
            HumanMessage(content=f"Task: {state['task']}"),
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

    def _should_breakdown(self, state: AgentState) -> str:
        """
        Decide whether to breakdown the task or end.

        Args:
            state: Current agent state

        Returns:
            Next node to execute ("breakdown" or "end")
        """
        return "breakdown" if state["needs_breakdown"] else "end"

    def run(self, task: str) -> dict:
        """
        Run the agent on a given task.

        Args:
            task: The task to analyze and potentially break down

        Returns:
            Dictionary containing:
                - task: Original task
                - needs_breakdown: Whether breakdown was needed
                - analysis: LLM's reasoning
                - steps: List of steps (empty if no breakdown needed)
        """
        initial_state: AgentState = {
            "task": task,
            "steps": [],
            "analysis": "",
            "needs_breakdown": False,
        }

        result = self.graph.invoke(initial_state)

        return {
            "task": result["task"],
            "needs_breakdown": result["needs_breakdown"],
            "analysis": result["analysis"],
            "steps": result["steps"],
        }
