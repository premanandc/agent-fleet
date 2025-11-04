"""
Generate Plan Node (Task Breakdown)

Uses LLM to analyze user requests and create execution plans.
Performs capability-driven task decomposition by matching request
requirements to available agent capabilities.
"""

import os
import logging
import json
import uuid
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..models.router_state import RouterState, Plan, Task
from ..llm.factory import LLMFactory
from ..utils.discovery import discover_agents_from_langgraph

logger = logging.getLogger(__name__)


async def generate_plan(state: RouterState, config: RunnableConfig) -> dict:
    """
    Generates execution plan by breaking down request into tasks

    Uses LLM to:
    1. Analyze the user request
    2. Identify required capabilities
    3. Match capabilities to available agents
    4. Create ordered task list with dependencies
    5. Determine execution strategy (parallel vs sequential)

    Args:
        state: Current router state with validated request
        config: LangGraph config containing agent_registry

    Returns:
        Updated state with plan populated
    """

    user_request = state.get("original_request", "")
    logger.info(f"Generating plan for: {user_request[:100]}...")

    # Discover agents dynamically
    logger.info("Discovering available agents...")
    agent_registry = await discover_agents_from_langgraph()

    if not agent_registry:
        logger.warning("No agents available in registry")
        # Return a plan that indicates no agents available
        return {
            "plan": Plan(
                tasks=[],
                execution_strategy="sequential",
                created_at=datetime.now(),
                analysis="No agents available to handle this request"
            ),
            "need_replan": False
        }

    # Build agent capabilities summary for LLM
    agent_summary = "\n".join([
        f"- {cap['name']} (ID: {agent_id}):\n"
        f"  Capabilities: {', '.join(cap['capabilities'])}\n"
        f"  Skills: {', '.join(cap['skills'])}\n"
        f"  Description: {cap['description']}"
        for agent_id, cap in agent_registry.items()
    ])

    # Check if this is a replan
    replan_context = ""
    if state.get("replan_count", 0) > 0:
        previous_results = state.get("task_results", [])
        replan_reason = state.get("replan_reason", "Previous plan was insufficient")

        results_summary = "\n".join([
            f"- Task: {task['description']}\n"
            f"  Agent: {task['agent_name']}\n"
            f"  Status: {task['status']}\n"
            f"  Result: {task.get('result', 'N/A')}"
            for task in previous_results
        ])

        replan_context = f"""
IMPORTANT - THIS IS A REPLAN (Attempt #{state['replan_count'] + 1}):
Reason for replanning: {replan_reason}

Previous attempt results:
{results_summary}

Consider these results when creating the new plan. You may need to:
- Add follow-up tasks based on previous results
- Try different agents if previous ones failed
- Adjust task decomposition based on what we learned
"""

    # Build planning prompt
    planning_prompt = f"""You are the Task Breakdown system for the ITEP Agentic AI Platform.

USER REQUEST:
{user_request}

AVAILABLE AGENTS:
{agent_summary}
{replan_context}

YOUR TASK:
Create an execution plan to fulfill this request by:
1. Analyzing what needs to be done
2. Breaking it into specific, actionable tasks
3. Assigning each task to the most capable agent
4. Identifying task dependencies
5. Determining if tasks can run in parallel or must be sequential

GUIDELINES:
- Each task should be atomic and focused
- Match tasks to agent capabilities precisely
- Prefer parallel execution when tasks are independent
- Use sequential execution when tasks depend on each other
- Provide clear rationale for each agent selection
- If multiple agents could handle a task, choose the most specialized one

Respond with JSON in this exact format:
{{
  "analysis": "Brief analysis of the request and approach",
  "execution_strategy": "parallel" or "sequential",
  "tasks": [
    {{
      "description": "Clear description of what this task accomplishes",
      "agent_id": "exact agent ID from available agents",
      "agent_name": "agent name for logging",
      "dependencies": ["task_id_1", "task_id_2"],  // empty list if no dependencies
      "rationale": "Why this agent was chosen for this task"
    }}
  ]
}}

IMPORTANT:
- Use exact agent IDs from the available agents list
- Dependencies should reference task IDs (will be auto-generated)
- For parallel strategy, ensure tasks have no circular dependencies
- For sequential strategy, tasks will execute in the order listed
"""

    # Call LLM for planning
    llm = LLMFactory.create(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL"),
        temperature=0.5  # Moderate temperature for creative but consistent planning
    )

    messages = [
        SystemMessage(content="You are an expert at task decomposition and agent orchestration."),
        HumanMessage(content=planning_prompt)
    ]

    try:
        response = await llm.ainvoke(messages)

        # Parse response
        plan_data = json.loads(response.content)

        analysis = plan_data.get("analysis", "")
        execution_strategy = plan_data.get("execution_strategy", "sequential")
        raw_tasks = plan_data.get("tasks", [])

        logger.info(f"Analysis: {analysis}")
        logger.info(f"Strategy: {execution_strategy}")
        logger.info(f"Tasks: {len(raw_tasks)}")

        # Build Task objects with generated IDs
        tasks = []
        task_id_map = {}  # Map temp IDs to real IDs for dependency resolution

        for idx, raw_task in enumerate(raw_tasks):
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            task_id_map[idx] = task_id

            agent_id = raw_task.get("agent_id")
            agent_name = raw_task.get("agent_name", agent_id)

            # Validate agent exists
            if agent_id not in agent_registry:
                logger.warning(f"Agent {agent_id} not found in registry, skipping task")
                continue

            task = Task(
                id=task_id,
                description=raw_task.get("description", ""),
                agent_id=agent_id,
                agent_name=agent_name,
                status="pending",
                result=None,
                error=None,
                dependencies=raw_task.get("dependencies", []),  # Will be resolved below
                rationale=raw_task.get("rationale", "")
            )

            tasks.append(task)

        # Resolve dependencies (convert indices to real IDs if needed)
        # For now, keep dependencies as-is since LLM should provide task IDs
        # If LLM provides indices, we'd need to map them here

        # Create Plan object
        plan = Plan(
            tasks=tasks,
            execution_strategy=execution_strategy,
            created_at=datetime.now(),
            analysis=analysis
        )

        logger.info(f"Generated plan with {len(tasks)} tasks")
        for task in tasks:
            logger.info(f"  - {task['description']} → {task['agent_name']}")

        return {
            "plan": plan,
            "need_replan": False
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {response.content}")

        # Return empty plan on error
        return {
            "plan": Plan(
                tasks=[],
                execution_strategy="sequential",
                created_at=datetime.now(),
                analysis=f"Planning failed: Invalid JSON response from LLM"
            ),
            "need_replan": False
        }

    except Exception as e:
        logger.error(f"Error during planning: {e}")

        return {
            "plan": Plan(
                tasks=[],
                execution_strategy="sequential",
                created_at=datetime.now(),
                analysis=f"Planning failed: {str(e)}"
            ),
            "need_replan": False
        }
