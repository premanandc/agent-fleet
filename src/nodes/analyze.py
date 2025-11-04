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

    # Build analysis prompt
    analysis_prompt = f"""You are the Result Analyzer for the ITEP Agentic AI Platform.

ORIGINAL USER REQUEST:
{original_request}

TASK EXECUTION RESULTS:
{results_summary}

YOUR TASK:
Evaluate if these results sufficiently address the user's original request.

EVALUATION CRITERIA:
1. Task Success: Did all tasks complete successfully?
2. Completeness: Do the results fully answer the user's question/request?
3. Quality: Are the results actionable and useful?
4. Gaps: Are there obvious follow-up tasks needed?

DECISION:
- If results are sufficient → recommend NO REPLAN
- If critical tasks failed → recommend REPLAN with specific recovery actions
- If results are incomplete → recommend REPLAN with additional tasks
- If there are clear gaps → recommend REPLAN to fill them

IMPORTANT:
- Consider the current replan attempt ({replan_count + 1}/{max_replans})
- If we're near max replans, be more lenient (partial results are okay)
- Focus on whether user's core need is addressed, not perfection

Respond with JSON:
{{
  "is_sufficient": true or false,
  "reasoning": "Detailed explanation of your evaluation",
  "replan_strategy": "If replanning, what should we do differently? (null if sufficient)"
}}
"""

    # Call LLM for analysis
    llm = LLMFactory.create(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL"),
        temperature=0.3  # Lower temperature for consistent evaluation
    )

    messages = [
        SystemMessage(content="You are an expert at evaluating task execution results."),
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
