"""
Execute Tasks Node (Orchestrator)

Executes the approved plan by invoking subordinate agents via A2A protocol.
Handles both parallel and sequential execution strategies, tracks task status,
and manages dependencies.
"""

import os
import logging
import asyncio
import httpx
from typing import Dict, List
from uuid import uuid4
from langchain_core.runnables import RunnableConfig

from a2a.client import A2AClient, A2AClientHTTPError, A2AClientJSONError
from a2a.types import SendMessageRequest, MessageSendParams, AgentCard, SendMessageSuccessResponse, Message

from ..models.router_state import RouterState, Task

logger = logging.getLogger(__name__)


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
        logger.error("No plan to execute")
        return {
            "task_results": [],
            "current_task_index": 0
        }

    tasks = plan["tasks"]
    execution_strategy = plan["execution_strategy"]
    original_request = state.get("original_request", "")

    logger.info(f"Starting execution of {len(tasks)} tasks ({execution_strategy} mode)")

    # Get LangGraph server URL from config
    langgraph_url = os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:2024")

    # Track completed tasks (from previous executions if replanning)
    completed_tasks = {task["id"]: task for task in state.get("task_results", [])}

    # Execute tasks based on strategy
    if execution_strategy == "parallel":
        results = await _execute_parallel(tasks, completed_tasks, original_request, langgraph_url)
    else:  # sequential
        results = await _execute_sequential(tasks, completed_tasks, original_request, langgraph_url)

    # completed_tasks dict was mutated during execution to include new results
    # Return all tasks (both previously completed and newly executed)
    all_results = list(completed_tasks.values())

    logger.info(f"Executed {len(results)} new tasks (total: {len(all_results)})")
    for task in results:
        status_icon = "✓" if task["status"] == "completed" else "✗"
        logger.info(f"  {status_icon} {task['description']} - {task['status']}")

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

    logger.info("Using parallel execution strategy")

    results = []

    # Find tasks ready to execute (dependencies met)
    ready_tasks = [
        task for task in tasks
        if task["id"] not in completed_tasks and
        _are_dependencies_met(task, completed_tasks)
    ]

    if not ready_tasks:
        logger.info("No tasks ready to execute (all completed or dependencies unmet)")
        return results

    logger.info(f"Executing {len(ready_tasks)} tasks in parallel")

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
                logger.error(f"Error executing task {task['id']}: {result}")
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

    logger.info("Using sequential execution strategy")

    results = []

    async with httpx.AsyncClient() as client:
        for task in tasks:
            # Skip already completed tasks
            if task["id"] in completed_tasks:
                logger.info(f"Skipping already completed task: {task['description']}")
                continue

            # Check dependencies
            if not _are_dependencies_met(task, completed_tasks):
                logger.info(f"Skipping task with unmet dependencies: {task['description']}")
                # Mark as failed due to unmet dependencies
                failed_task = task.copy()
                failed_task["status"] = "failed"
                failed_task["error"] = "Dependencies not met"
                results.append(failed_task)
                continue

            # Execute task
            logger.info(f"Executing task: {task['description']}")
            try:
                result = await _invoke_agent(task, original_request, completed_tasks, langgraph_url, client)
                results.append(result)
                completed_tasks[result["id"]] = result

                # Optional: Stop on first failure (can be configured)
                # if result["status"] == "failed":
                #     print("[Execute] Task failed, stopping sequential execution")
                #     break

            except Exception as e:
                logger.error(f"Error executing task {task['id']}: {e}")
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
    Invoke a subordinate agent via A2A protocol using the A2A SDK

    Uses the official a2a-sdk to:
    - Resolve agent card from /.well-known/agent-card.json
    - Create A2AClient with proper JSON-RPC handling
    - Send message with automatic protocol formatting
    - Parse response with built-in error handling

    Returns updated Task with result or error
    """

    agent_id = task["agent_id"]
    task_description = task["description"]

    logger.info(f"Invoking agent {task['agent_name']} for: {task_description}")

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

    try:
        # Fetch agent card directly (LangGraph uses query params, not path-based cards)
        # Format: GET /.well-known/agent-card.json?assistant_id={agent_id}
        card_response = await client.get(
            f"{langgraph_url}/.well-known/agent-card.json",
            params={"assistant_id": agent_id},
            timeout=10.0
        )
        card_response.raise_for_status()
        agent_card_data = card_response.json()

        # Parse the JSON response into an AgentCard Pydantic model
        agent_card = AgentCard(**agent_card_data)

        # Create A2A client with the parsed agent card
        a2a_client = A2AClient(
            httpx_client=client,
            agent_card=agent_card,
            url=f"{langgraph_url}/a2a/{agent_id}"
        )

        # Prepare message payload
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': agent_message}
                ],
                'messageId': f"msg_{task['id']}",
            },
            'thread': {
                'threadId': f"router_task_{task['id']}"
            }
        }

        # Create send message request
        request = SendMessageRequest(
            id=task['id'],
            params=MessageSendParams(**send_message_payload)
        )

        # Send message via A2A SDK (handles JSON-RPC automatically)
        response = await a2a_client.send_message(
            request,
            http_kwargs={'timeout': 300.0}  # 5 minute timeout
        )

        # Extract result from response
        # SendMessageResponse is a RootModel that wraps either error or success response
        agent_result = "No response from agent"

        # Check if response is a success (not an error)
        if isinstance(response.root, SendMessageSuccessResponse):
            success_response = response.root

            # The result can be either a Task or a Message
            result = success_response.result

            if isinstance(result, Message):
                # Extract text from message parts
                if hasattr(result, 'parts') and result.parts:
                    text_parts = []
                    for part in result.parts:
                        if hasattr(part, 'kind') and part.kind == 'text' and hasattr(part, 'text'):
                            text_parts.append(part.text)

                    if text_parts:
                        agent_result = "\n".join(text_parts)
                    else:
                        agent_result = str(result)
                else:
                    agent_result = str(result)
            else:
                # Result is a Task object
                agent_result = str(result)
        else:
            # This is an error response
            error_response = response.root
            error_msg = getattr(error_response, 'error', {}).get('message', 'Unknown error')
            raise Exception(f"A2A agent returned error: {error_msg}")

        logger.info(f"Agent {task['agent_name']} completed: {agent_result[:100]}...")

        # Update task with result
        completed_task = task.copy()
        completed_task["status"] = "completed"
        completed_task["result"] = agent_result
        completed_task["error"] = None

        return completed_task

    except httpx.TimeoutException:
        logger.error(f"Agent {task['agent_name']} timed out")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = "Agent execution timed out (5 minutes)"
        failed_task["result"] = None
        return failed_task

    except A2AClientHTTPError as e:
        logger.error(f"A2A HTTP error invoking agent {task['agent_name']}: {e}")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = f"A2A HTTP error: {str(e)}"
        failed_task["result"] = None
        return failed_task

    except A2AClientJSONError as e:
        logger.error(f"A2A JSON error invoking agent {task['agent_name']}: {e}")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = f"A2A JSON error: {str(e)}"
        failed_task["result"] = None
        return failed_task

    except Exception as e:
        logger.error(f"Error invoking agent {task['agent_name']}: {e}")
        failed_task = task.copy()
        failed_task["status"] = "failed"
        failed_task["error"] = str(e)
        failed_task["result"] = None
        return failed_task
