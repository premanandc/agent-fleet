"""
Quick Agent - Test Subordinate Agent

Simulates a fast-running agent for testing the Router.
Represents agents that perform quick analysis or validation tasks.

Examples: syntax checking, quick validation, basic analysis
Runtime: 1-2 seconds
"""

import time
import random
from typing import Annotated
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig


class QuickAgentState(dict):
    """State for Quick Agent - A2A compatible"""
    messages: Annotated[list[BaseMessage], add_messages]


def process_quick_task(state: QuickAgentState) -> dict:
    """
    Simulates a quick task (1-2 seconds)

    Extracts the task from the user message and simulates analysis.
    Returns a structured response with findings.
    """

    # Get the latest user message
    latest_message = state["messages"][-1] if state.get("messages") else None

    if not latest_message:
        return {
            "messages": [AIMessage(content="Error: No task provided")]
        }

    task_description = latest_message.content

    print(f"[QuickAgent] Starting quick task: {task_description[:50]}...")

    # Simulate quick processing (1-2 seconds)
    processing_time = random.uniform(1.0, 2.0)
    time.sleep(processing_time)

    # Generate realistic response based on task keywords
    response = _generate_quick_response(task_description, processing_time)

    print(f"[QuickAgent] Completed in {processing_time:.2f}s")

    return {
        "messages": [AIMessage(content=response)]
    }


def _generate_quick_response(task: str, processing_time: float) -> str:
    """Generate a realistic response based on task content"""

    task_lower = task.lower()

    # Detect task type and generate appropriate response
    if "syntax" in task_lower or "validate" in task_lower or "check" in task_lower:
        issues_found = random.randint(0, 5)
        return f"""## Quick Validation Complete

**Processing Time**: {processing_time:.2f}s

**Summary**: Performed quick syntax and structure validation.

**Findings**:
- Files analyzed: {random.randint(5, 15)}
- Syntax errors found: {issues_found}
- Warnings: {random.randint(0, 10)}

{"**Status**: ✓ All checks passed" if issues_found == 0 else f"**Status**: ⚠ {issues_found} issues require attention"}

**Recommendation**: {"No immediate action needed." if issues_found == 0 else "Review identified issues and consider fixes."}
"""

    elif "analyze" in task_lower or "review" in task_lower:
        complexity_score = random.randint(60, 95)
        return f"""## Quick Analysis Complete

**Processing Time**: {processing_time:.2f}s

**Summary**: Performed quick code analysis.

**Metrics**:
- Code complexity: {complexity_score}/100
- Maintainability: {"Good" if complexity_score > 75 else "Fair"}
- Test coverage: {random.randint(50, 90)}%

**Quick Findings**:
- Well-structured code with clear separation of concerns
- Few quick wins identified for improvement
- Overall quality: {"High" if complexity_score > 80 else "Medium"}

**Next Steps**: Consider deep analysis for comprehensive insights.
"""

    elif "scan" in task_lower or "detect" in task_lower:
        vulnerabilities = random.randint(0, 3)
        return f"""## Quick Security Scan Complete

**Processing Time**: {processing_time:.2f}s

**Summary**: Performed quick security scan.

**Results**:
- Vulnerabilities detected: {vulnerabilities}
- Severity: {"None" if vulnerabilities == 0 else "Low to Medium"}
- Dependencies scanned: {random.randint(10, 30)}

{"**Status**: ✓ No critical issues found" if vulnerabilities == 0 else f"**Status**: ⚠ {vulnerabilities} potential issues detected"}

**Recommendation**: {"System appears secure." if vulnerabilities == 0 else "Review findings and consider deeper security analysis."}
"""

    else:
        # Generic quick task response
        return f"""## Quick Task Complete

**Processing Time**: {processing_time:.2f}s

**Task**: {task[:100]}...

**Summary**: Quick analysis completed successfully.

**Results**:
- Initial assessment: Completed
- Quick checks: Passed
- Confidence: High

**Status**: ✓ Task completed

**Note**: This was a quick analysis. For comprehensive results, consider using a deep analysis agent.
"""


def create_quick_agent_graph(config: RunnableConfig = None):
    """
    Factory function to create Quick Agent graph

    This function is called by LangGraph Server to instantiate the agent.

    Returns:
        Compiled StateGraph ready for A2A invocation
    """

    print("[QuickAgent] Initializing Quick Agent...")

    # Create simple linear graph
    graph = StateGraph(QuickAgentState)

    # Single node - process the task
    graph.add_node("process", process_quick_task)

    # Simple flow: START -> process -> END
    graph.add_edge(START, "process")
    graph.add_edge("process", END)

    # Compile without checkpointer (stateless for simplicity)
    compiled_graph = graph.compile()

    print("[QuickAgent] Quick Agent initialized successfully")

    return compiled_graph


# A2A Agent Card (metadata for Router discovery)
AGENT_CARD = {
    "name": "QuickAgent",
    "version": "1.0.0",
    "description": "Fast analysis agent for quick validation and checks. Optimized for speed over depth.",
    "capabilities": [
        "analysis",
        "quick-check",
        "validation",
        "syntax-checking"
    ],
    "skills": [
        "Analyze code syntax",
        "Quick validation",
        "Fast security scans",
        "Basic code review",
        "Structure analysis"
    ],
    "input_mode": "messages",
    "output_mode": "messages",
    "performance": {
        "typical_runtime": "1-2 seconds",
        "max_runtime": "5 seconds"
    },
    "limitations": [
        "Surface-level analysis only",
        "Not suitable for deep code fixes",
        "Limited to quick checks"
    ],
    "best_for": [
        "Initial assessment",
        "Quick validation before deployment",
        "Fast feedback loops",
        "Syntax and structure checks"
    ]
}
