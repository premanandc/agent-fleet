"""
Execute Tasks Node (Orchestrator)

Executes the approved plan by invoking subordinate agents via A2A protocol.
Handles both parallel and sequential execution strategies, tracks task status,
and manages dependencies.
"""

import os
import asyncio
import httpx
from typing import Dict, List
from langchain_core.runnables import RunnableConfig

from ..models.router_state import RouterState, Task


async def execute_tasks(state: RouterState, config: RunnableConfig) -> dict:
    """
    Executes tasks from the plan by invoking subordinate agents

    Execution flow:
    1. Get approved plan from state
    2. Determine execution strategy (parallel vs sequential)
    3. For each task:
       - Check dependencies are completed
       - Invoke agent via A2A protocol (POST /a2a/{agent_id})
       - Track results and status
    4. Return updated task results

    Args:
        state: Current router state with approved plan
        config: LangGraph config containing agent_registry

    Returns:
        Updated state with task_results populated
    """

    plan = state.get("plan")
    if not plan:
        print("[Execute] Error: No plan to execute")
        return {
            "task_results": [],
            "current_task_index": 0
        }

    tasks = plan["tasks"]
    execution_strategy = plan["execution_strategy"]
    original_request = state.get("original_request", "")

    print(f"[Execute] Starting execution of {len(tasks)} tasks ({execution_strategy} mode)")

    # Get LangGraph server URL from config
    langgraph_url = os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:2024")

    # Track completed tasks (from previous executions if replanning)
    completed_tasks = {task["id"]: task for task in state.get("task_results", [])}

    # Execute tasks based on strategy
    if execution_strategy == "parallel":
        results = await _execute_parallel(tasks, completed_tasks, original_request, langgraph_url)
    else:  # sequential
        results = await _execute_sequential(tasks, completed_tasks, original_request, langgraph_url)

    # Merge results with any previous results
    all_results = list(completed_tasks.values()) + results

    print(f"[Execute] Completed {len(results)} tasks")
    for task in results:
        status_icon = "✓" if task["status"] == "completed" else "✗"
        print(f"  {status_icon} {task['description']} - {task['status']}")

    return {
        "task_results": all_results,
        "current_task_index": len(all_results)
    }


async def _execute_parallel(
    tasks: List[Task],
    completed_tasks: Dict[str, Task],
    original_request: str,
    langgraph_url: str
) -> List[Task]:
    """
    Execute tasks in parallel using asyncio

    Only executes tasks whose dependencies are already completed.
    Tasks with unmet dependencies are skipped.
    """

    print("[Execute] Using parallel execution strategy")

    results = []

    # Find tasks ready to execute (dependencies met)
    ready_tasks = [
        task for task in tasks
        if task["id"] not in completed_tasks and
        _are_dependencies_met(task, completed_tasks)
    ]

    if not ready_tasks:
        print("[Execute] No tasks ready to execute (all completed or dependencies unmet)")
        return results

    print(f"[Execute] Executing {len(ready_tasks)} tasks in parallel")

    # Execute ready tasks in parallel using asyncio.gather
    async with httpx.AsyncClient() as client:
        task_coroutines = [
            _invoke_agent(task, original_request, completed_tasks, langgraph_url, client)
            for task in ready_tasks
        ]

        # Gather all results
        task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)

        # Process results
        for i, result in enumerate(task_results):
            task = ready_tasks[i]
            if isinstance(result, Exception):
                print(f"[Execute] Error executing task {task['id']}: {result}")
                # Mark task as failed
                failed_task = task.copy()
                failed_task["status"] = "failed"
                failed_task["error"] = str(result)
                results.append(failed_task)
            else:
                results.append(result)
                completed_tasks[result["id"]] = result

    return results


async def _execute_sequential(
    tasks: List[Task],
    completed_tasks: Dict[str, Task],
    original_request: str,
    langgraph_url: str
) -> List[Task]:
    """
    Execute tasks sequentially in order

    Each task is executed only if its dependencies are met.
    Stops execution if a critical task fails (optional enhancement).
    """

    print("[Execute] Using sequential execution strategy")

    results = []

    async with httpx.AsyncClient() as client:
        for task in tasks:
            # Skip already completed tasks
            if task["id"] in completed_tasks:
                print(f"[Execute] Skipping already completed task: {task['description']}")
                continue

            # Check dependencies
            if not _are_dependencies_met(task, completed_tasks):
                print(f"[Execute] Skipping task with unmet dependencies: {task['description']}")
                # Mark as failed due to unmet dependencies
                failed_task = task.copy()
                failed_task["status"] = "failed"
                failed_task["error"] = "Dependencies not met"
                results.append(failed_task)
                continue

            # Execute task
            print(f"[Execute] Executing task: {task['description']}")
            try:
                result = await _invoke_agent(task, original_request, completed_tasks, langgraph_url, client)
                results.append(result)
                completed_tasks[result["id"]] = result

                # Optional: Stop on first failure (can be configured)
                # if result["status"] == "failed":
                #     print("[Execute] Task failed, stopping sequential execution")
                #     break

            except Exception as e:
                print(f"[Execute] Error executing task {task['id']}: {e}")
                failed_task = task.copy()
                failed_task["status"] = "failed"
                failed_task["error"] = str(e)
                results.append(failed_task)
                completed_tasks[failed_task["id"]] = failed_task

    return results


def _are_dependencies_met(task: Task, completed_tasks: Dict[str, Task]) -> bool:
    """
    Check if all task dependencies are completed successfully
    """

    if not task.get("dependencies"):
        return True

    for dep_id in task["dependencies"]:
        if dep_id not in completed_tasks:
            return False
        if completed_tasks[dep_id]["status"] != "completed":
            return False

    return True


async def _invoke_agent(
    task: Task,
    original_request: str,
    completed_tasks: Dict[str, Task],
    langgraph_url: str,
    client: httpx.AsyncClient
) -> Task:
    """
    Invoke a subordinate agent via A2A protocol

    Makes HTTP POST to /a2a/{agent_id} with:
    - Original user request
    - Task-specific instructions
    - Context from completed dependencies

    Returns updated Task with result or error
    """

    agent_id = task["agent_id"]
    task_description = task["description"]

    print(f"[Execute] Invoking agent {task['agent_name']} for: {task_description}")

    # Build context from dependencies
    dependency_context = ""
    if task.get("dependencies"):
        dependency_context = "\n\nContext from previous tasks:\n"
        for dep_id in task["dependencies"]:
            if dep_id in completed_tasks:
                dep_task = completed_tasks[dep_id]
                dependency_context += f"- {dep_task['description']}: {dep_task.get('result', 'N/A')}\n"

    # Build message for subordinate agent
    agent_message = f"""Original user request: {original_request}

Your specific task: {task_description}
{dependency_context}

Please complete this task and provide your findings.
"""

    # Prepare A2A request
    a2a_request = {
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": agent_message
                }
            ]
        },
        "config": {
            "configurable": {
                "thread_id": f"router_task_{task['id']}"
            }
        },
        "stream_mode": "values"
    }

    try:
        # Invoke agent via A2A
        response = await client.post(
            f"{langgraph_url}/a2a/{agent_id}",
            json=a2a_request,
            timeout=300.0  # 5 minute timeout for agent execution
        )

        response.raise_for_status()

        # Parse response
        # A2A returns streaming values, get the last one
        response_data = response.json()

        # Extract final message from agent
        # Response format: {"messages": [...], ...}
        agent_result = "No response from agent"
        if isinstance(response_data, dict):
            messages = response_data.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, dict):
                    agent_result = last_message.get("content", str(last_message))
                else:
                    agent_result = str(last_message)

        print(f"[Execute] Agent {task['agent_name']} completed: {agent_result[:100]}...")

        # Update task with result
        completed_task = task.copy()
        completed_task["status"] = "completed"
        completed_task["result"] = agent_result
        completed_task["error"] = None

        return completed_task

    except httpx.TimeoutException:
        print(f"[Execute] Agent {task['agent_name']} timed out")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = "Agent execution timed out (5 minutes)"
        failed_task["result"] = None
        return failed_task

    except httpx.HTTPStatusError as e:
        print(f"[Execute] HTTP error invoking agent {task['agent_name']}: {e}")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = f"HTTP {e.response.status_code}: {e.response.text}"
        failed_task["result"] = None
        return failed_task

    except Exception as e:
        print(f"[Execute] Error invoking agent {task['agent_name']}: {e}")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = str(e)
        failed_task["result"] = None
        return failed_task
