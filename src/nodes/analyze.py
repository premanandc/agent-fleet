"""
Analyze Results Node (Replan Decision)

Evaluates task execution results to determine if they sufficiently
answer the user's original request. Triggers replanning if results
are incomplete or if tasks failed.
"""

import os
import logging
import json
from langchain_core.messages import SystemMessage, HumanMessage

from ..models.router_state import RouterState
from ..llm.factory import LLMFactory
from ..utils import PromptManager

logger = logging.getLogger(__name__)


def analyze_results(state: RouterState) -> dict:
    """
    Analyzes task results and decides if replanning is needed

    Uses LLM to evaluate:
    1. Did all tasks complete successfully?
    2. Do the results collectively answer the user's request?
    3. Are there gaps or follow-up actions needed?

    Decision logic:
    - If any critical tasks failed → replan
    - If results are incomplete → replan
    - If user request not fully addressed → replan
    - If max replans reached → proceed to aggregation
    - Otherwise → proceed to aggregation

    Args:
        state: Current router state with task_results

    Returns:
        Updated state with need_replan flag and replan_reason
    """

    original_request = state.get("original_request", "")
    task_results = state.get("task_results", [])
    replan_count = state.get("replan_count", 0)
    max_replans = state.get("max_replans", 2)

    logger.info(f"Evaluating {len(task_results)} task results (replan count: {replan_count}/{max_replans})")

    # Check if max replans reached
    if replan_count >= max_replans:
        logger.info("Max replans reached, proceeding to aggregation")
        return {
            "need_replan": False,
            "replan_reason": None
        }

    # Quick check: Any failed tasks?
    failed_tasks = [task for task in task_results if task["status"] == "failed"]
    if failed_tasks:
        logger.info(f"Found {len(failed_tasks)} failed tasks")

    # Build results summary for LLM
    results_summary = "\n".join([
        f"Task {idx + 1}: {task['description']}\n"
        f"  Agent: {task['agent_name']}\n"
        f"  Status: {task['status']}\n"
        f"  Result: {task.get('result', 'N/A')}\n"
        f"  Error: {task.get('error', 'N/A')}"
        for idx, task in enumerate(task_results)
    ])

    # Get analysis prompt from PromptManager
    analysis_prompt = PromptManager.get_prompt(
        "analysis",
        original_request=original_request,
        results_summary=results_summary,
        replan_attempt=replan_count + 1,
        max_replans=max_replans
    )

    # Call LLM for analysis
    llm = LLMFactory.create(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL"),
        temperature=PromptManager.get_temperature("analysis")
    )

    messages = [
        SystemMessage(content=PromptManager.get_system_message("analysis")),
        HumanMessage(content=analysis_prompt)
    ]

    try:
        response = llm.invoke(messages)

        # Parse response
        analysis_result = json.loads(response.content)

        is_sufficient = analysis_result.get("is_sufficient", True)
        reasoning = analysis_result.get("reasoning", "")
        replan_strategy = analysis_result.get("replan_strategy")

        logger.info(f"Sufficiency: {'YES' if is_sufficient else 'NO'}")
        logger.info(f"Reasoning: {reasoning}")

        if is_sufficient:
            return {
                "need_replan": False,
                "replan_reason": None
            }
        else:
            logger.info(f"Triggering replan: {replan_strategy}")
            return {
                "need_replan": True,
                "replan_reason": replan_strategy or reasoning,
                "replan_count": replan_count + 1
            }

    except json.JSONDecodeError as e:
        logger.info(f"Error: Failed to parse LLM response: {e}")
        # On error, assume results are sufficient and proceed
        return {
            "need_replan": False,
            "replan_reason": None
        }

    except Exception as e:
        logger.info(f"Error during analysis: {e}")
        # On error, assume results are sufficient and proceed
        return {
            "need_replan": False,
            "replan_reason": None
        }
