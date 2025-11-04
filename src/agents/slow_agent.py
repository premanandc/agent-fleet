"""
Slow Agent - Test Subordinate Agent

Simulates a long-running agent for testing the Router.
Represents agents that perform deep analysis or complex remediation tasks.

Examples: code fixing, deep analysis, complex refactoring
Runtime: 5-10 seconds
"""

import asyncio
import logging
import random
from typing import Annotated
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class SlowAgentState(dict):
    """State for Slow Agent - A2A compatible"""
    messages: Annotated[list[BaseMessage], add_messages]


async def process_slow_task(state: SlowAgentState) -> dict:
    """
    Simulates a long-running task (5-10 seconds)

    Extracts the task from the user message and simulates deep processing.
    Returns a detailed response with comprehensive findings.
    """

    # Get the latest user message
    latest_message = state["messages"][-1] if state.get("messages") else None

    if not latest_message:
        return {
            "messages": [AIMessage(content="Error: No task provided")]
        }

    task_description = latest_message.content

    logger.info(f"Starting deep task: {task_description[:50]}...")

    # Simulate long processing with progress indicators
    processing_time = random.uniform(5.0, 10.0)

    # Simulate multi-stage processing
    stages = [
        ("Analyzing codebase", 0.2),
        ("Identifying issues", 0.3),
        ("Generating fixes", 0.3),
        ("Validating solutions", 0.2)
    ]

    elapsed = 0
    for stage, proportion in stages:
        stage_time = processing_time * proportion
        logger.info(f"  {stage}... ({stage_time:.1f}s)")
        await asyncio.sleep(stage_time)
        elapsed += stage_time

    # Generate realistic response based on task keywords
    response = _generate_slow_response(task_description, processing_time)

    logger.info(f"Completed in {processing_time:.2f}s")

    return {
        "messages": [AIMessage(content=response)]
    }


def _generate_slow_response(task: str, processing_time: float) -> str:
    """Generate a realistic comprehensive response based on task content"""

    task_lower = task.lower()

    # Detect task type and generate appropriate response
    if "fix" in task_lower or "remediate" in task_lower or "resolve" in task_lower:
        issues_fixed = random.randint(3, 12)
        return f"""## Deep Remediation Complete

**Processing Time**: {processing_time:.2f}s

**Summary**: Performed comprehensive code remediation with automated fixes.

### Issues Addressed

**Critical Issues Fixed**: {random.randint(1, 3)}
- Null pointer vulnerabilities
- Resource leak in database connections
- Unsafe deserialization

**Major Issues Fixed**: {random.randint(2, 5)}
- Code smells and anti-patterns
- Inefficient algorithms
- Deprecated API usage

**Minor Issues Fixed**: {issues_fixed - 3}
- Style violations
- Naming conventions
- Documentation improvements

### Changes Made

**Files Modified**: {random.randint(8, 20)}
**Lines Changed**: {random.randint(150, 500)}
**Tests Updated**: {random.randint(5, 15)}

### Validation Results

✓ All fixes validated with automated tests
✓ Code coverage maintained at {random.randint(75, 95)}%
✓ No regressions detected
✓ Build passes successfully

### Recommendations

1. Review the changes in detail before merging
2. Consider adding integration tests for critical fixes
3. Update documentation to reflect API changes
4. Schedule follow-up security scan

**Status**: ✓ Remediation successful - ready for review
"""

    elif "sonarqube" in task_lower or "quality" in task_lower:
        violations_fixed = random.randint(10, 30)
        return f"""## SonarQube Deep Analysis & Remediation

**Processing Time**: {processing_time:.2f}s

**Summary**: Comprehensive SonarQube violation analysis and automated remediation.

### Violation Analysis

**Total Violations Found**: {violations_fixed}
- Bugs: {random.randint(2, 8)}
- Vulnerabilities: {random.randint(1, 5)}
- Code Smells: {violations_fixed - 8}

**Quality Gate Status**: PASSED

### Remediation Actions

**Automatically Fixed**: {random.randint(violations_fixed - 5, violations_fixed)}
- Removed unused imports and variables
- Fixed potential null pointer exceptions
- Resolved resource leak issues
- Applied proper exception handling
- Refactored complex methods

**Requires Manual Review**: {random.randint(0, 5)}
- Design-level improvements
- Architecture considerations

### Quality Metrics (After Fixes)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Reliability | B | A | ↑ +1 |
| Security | C | A | ↑ +2 |
| Maintainability | C | B | ↑ +1 |
| Coverage | {random.randint(60, 70)}% | {random.randint(75, 85)}% | ↑ |
| Duplication | {random.randint(5, 10)}% | {random.randint(1, 3)}% | ↓ |

### Next Steps

1. ✓ Code analysis complete
2. ✓ Automated fixes applied
3. → Manual review recommended for architectural items
4. → Run full regression test suite
5. → Deploy to staging for validation

**Status**: ✓ {violations_fixed - 5} violations resolved automatically
"""

    elif "refactor" in task_lower or "optimize" in task_lower:
        methods_refactored = random.randint(5, 15)
        return f"""## Deep Code Refactoring Complete

**Processing Time**: {processing_time:.2f}s

**Summary**: Comprehensive code refactoring for improved maintainability and performance.

### Refactoring Summary

**Methods Refactored**: {methods_refactored}
**Classes Restructured**: {random.randint(2, 6)}
**Design Patterns Applied**: {random.randint(1, 3)}

### Key Improvements

**1. Complexity Reduction**
- Reduced cyclomatic complexity from {random.randint(25, 40)} to {random.randint(8, 15)}
- Broke down large methods into smaller, focused functions
- Applied Single Responsibility Principle

**2. Performance Optimization**
- Optimized database queries (reduced N+1 queries)
- Implemented caching for frequently accessed data
- Improved algorithm efficiency (O(n²) → O(n log n))

**3. Code Organization**
- Extracted common logic into reusable utilities
- Applied Strategy pattern for polymorphic behavior
- Improved separation of concerns

**4. Error Handling**
- Implemented consistent exception handling
- Added proper logging and monitoring
- Improved error recovery mechanisms

### Test Results

✓ All {random.randint(50, 100)} tests passing
✓ Code coverage: {random.randint(80, 95)}%
✓ Performance improvement: ~{random.randint(20, 45)}% faster
✓ Memory usage: ~{random.randint(10, 25)}% reduction

### Code Quality Metrics

- Maintainability Index: {random.randint(75, 95)}/100
- Technical Debt Ratio: {random.uniform(3, 8):.1f}%
- Duplication: {random.uniform(1, 3):.1f}%

**Status**: ✓ Refactoring complete - code is cleaner, faster, and more maintainable
"""

    else:
        # Generic deep task response
        return f"""## Deep Analysis Complete

**Processing Time**: {processing_time:.2f}s

**Task**: {task[:100]}...

**Summary**: Comprehensive deep analysis completed with detailed findings.

### Analysis Results

**Scope**: Full codebase analysis
**Depth**: Deep semantic and structural analysis
**Confidence**: Very High

### Key Findings

1. **Architecture Assessment**
   - Overall structure: Well-organized
   - Design patterns: Appropriately applied
   - Scalability: Good foundation

2. **Code Quality**
   - Maintainability: {random.randint(70, 90)}/100
   - Complexity: Managed well
   - Documentation: {random.choice(["Adequate", "Good", "Excellent"])}

3. **Technical Debt**
   - Current debt: {random.randint(5, 15)} person-days
   - Trend: Decreasing
   - Priority items: {random.randint(3, 8)} identified

### Detailed Metrics

- Files analyzed: {random.randint(50, 150)}
- LOC analyzed: {random.randint(5000, 20000):,}
- Methods reviewed: {random.randint(100, 500)}
- Issues found: {random.randint(10, 50)}

### Recommendations

1. Address high-priority technical debt items
2. Consider refactoring complex modules
3. Improve test coverage in critical paths
4. Update outdated dependencies

**Status**: ✓ Deep analysis complete - comprehensive report generated
"""


def create_slow_agent_graph(config: RunnableConfig = None):
    """
    Factory function to create Slow Agent graph

    This function is called by LangGraph Server to instantiate the agent.

    Returns:
        Compiled StateGraph ready for A2A invocation
    """

    logger.info("Initializing Slow Agent...")

    # Create simple linear graph
    graph = StateGraph(SlowAgentState)

    # Single node - process the task
    graph.add_node("process", process_slow_task)

    # Simple flow: START -> process -> END
    graph.add_edge(START, "process")
    graph.add_edge("process", END)

    # Compile without checkpointer (stateless for simplicity)
    compiled_graph = graph.compile()

    logger.info("Slow Agent initialized successfully")

    return compiled_graph


# A2A Agent Card (metadata for Router discovery)
AGENT_CARD = {
    "name": "SlowAgent",
    "version": "1.0.0",
    "description": "Deep analysis and remediation agent for comprehensive code fixes. Optimized for thoroughness over speed.",
    "capabilities": [
        "deep-analysis",
        "remediation",
        "code-fixing",
        "refactoring",
        "sonarqube"
    ],
    "skills": [
        "Fix SonarQube violations",
        "Deep code analysis",
        "Complex refactoring",
        "Automated code remediation",
        "Performance optimization",
        "Security issue resolution"
    ],
    "input_mode": "messages",
    "output_mode": "messages",
    "performance": {
        "typical_runtime": "5-10 seconds",
        "max_runtime": "30 seconds"
    },
    "limitations": [
        "Slower execution time",
        "Not suitable for time-sensitive tasks",
        "Higher resource usage"
    ],
    "best_for": [
        "Comprehensive code fixing",
        "Deep quality analysis",
        "Complex refactoring tasks",
        "SonarQube remediation",
        "Performance optimization"
    ]
}
