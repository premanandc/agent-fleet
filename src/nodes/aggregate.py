"""
Aggregate Results Node (Summarizer)

Synthesizes task execution results into a coherent, comprehensive
response for the user. This is the final node before returning to the user.
"""

import os
import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..models.router_state import RouterState
from ..llm.factory import LLMFactory

logger = logging.getLogger(__name__)


def aggregate_results(state: RouterState) -> dict:
    """
    Aggregates task results into a final user-facing response

    Uses LLM to:
    1. Synthesize results from all completed tasks
    2. Organize information coherently
    3. Highlight key findings and recommendations
    4. Note any limitations or failed tasks
    5. Provide actionable next steps

    Args:
        state: Current router state with task_results

    Returns:
        Updated state with final_response and AI message
    """

    original_request = state.get("original_request", "")
    task_results = state.get("task_results", [])
    plan = state.get("plan")

    logger.info(f"Synthesizing {len(task_results)} task results into final response")

    # Build task results summary
    results_summary = ""
    for idx, task in enumerate(task_results, 1):
        status_icon = "✓" if task["status"] == "completed" else "✗"
        results_summary += f"\n{idx}. {status_icon} {task['description']}\n"
        results_summary += f"   Agent: {task['agent_name']}\n"

        if task["status"] == "completed":
            results_summary += f"   Result: {task.get('result', 'No result')}\n"
        else:
            results_summary += f"   Error: {task.get('error', 'Unknown error')}\n"

    # Count successes and failures
    completed_count = sum(1 for task in task_results if task["status"] == "completed")
    failed_count = sum(1 for task in task_results if task["status"] == "failed")

    # Build aggregation prompt
    aggregation_prompt = f"""You are the Response Synthesizer for the ITEP Agentic AI Platform.

ORIGINAL USER REQUEST:
{original_request}

EXECUTION SUMMARY:
- Total tasks: {len(task_results)}
- Completed: {completed_count}
- Failed: {failed_count}

DETAILED TASK RESULTS:
{results_summary}

YOUR TASK:
Create a comprehensive, user-friendly response that:

1. DIRECTLY ANSWERS the user's original request
2. SYNTHESIZES findings from all task results into a coherent narrative
3. ORGANIZES information logically (not just task-by-task repetition)
4. HIGHLIGHTS key insights, recommendations, or action items
5. ACKNOWLEDGES any limitations or failed tasks (if applicable)
6. PROVIDES next steps or follow-up recommendations

GUIDELINES:
- Write in a clear, professional tone
- Focus on what the user needs to know, not implementation details
- Use markdown formatting for readability (headers, lists, code blocks)
- Be concise but comprehensive
- If tasks failed, explain what was attempted and suggest alternatives
- Don't mention "agents" or "tasks" - user doesn't need to know internal orchestration

IMPORTANT:
- This is the final response the user will see
- Make it actionable and valuable
- Integrate results seamlessly, don't just list them

Generate the final response:
"""

    # Call LLM for aggregation
    llm = LLMFactory.create(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL"),
        temperature=0.7  # Higher temperature for more natural summarization
    )

    messages = [
        SystemMessage(content="You are an expert at synthesizing technical information into clear, actionable responses."),
        HumanMessage(content=aggregation_prompt)
    ]

    try:
        response = llm.invoke(messages)
        final_response = response.content

        logger.info(f"Generated final response ({len(final_response)} chars)")

        # Add execution summary footer if there were failures
        if failed_count > 0:
            final_response += f"\n\n---\n*Note: {failed_count} of {len(task_results)} tasks encountered errors. The response above reflects available information.*"

        # Create AI message with final response
        ai_message = AIMessage(content=final_response)

        return {
            "final_response": final_response,
            "messages": [ai_message]
        }

    except Exception as e:
        logger.error(f"Error during aggregation: {e}")

        # Fallback: Create simple concatenation of results
        fallback_response = f"# Results for: {original_request}\n\n"

        for idx, task in enumerate(task_results, 1):
            fallback_response += f"## {idx}. {task['description']}\n\n"
            if task["status"] == "completed":
                fallback_response += f"{task.get('result', 'No result')}\n\n"
            else:
                fallback_response += f"*This task failed: {task.get('error', 'Unknown error')}*\n\n"

        fallback_response += f"\n---\n*Response generated with {completed_count}/{len(task_results)} successful tasks*"

        ai_message = AIMessage(content=fallback_response)

        return {
            "final_response": fallback_response,
            "messages": [ai_message]
        }
