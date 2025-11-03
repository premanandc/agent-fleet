"""
Await Approval Node (Human-in-the-loop)

Handles plan approval workflow for interactive and review modes.
Uses LangGraph's interrupt mechanism to pause execution and wait
for human approval before proceeding with task execution.
"""

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from ..models.router_state import RouterState


def await_approval(state: RouterState) -> dict:
    """
    Presents plan to user and waits for approval

    In INTERACTIVE/REVIEW modes:
    - Displays the generated plan to the user
    - Uses LangGraph interrupt to pause execution
    - Waits for user to approve/reject/modify the plan
    - Resumes execution based on user decision

    In AUTO mode:
    - This node is skipped entirely via conditional edge

    Args:
        state: Current router state with generated plan

    Returns:
        Updated state with plan_approved flag and user message
    """

    mode = state.get("mode", "auto")
    plan = state.get("plan")

    if not plan:
        print("[Approval] Warning: No plan to approve")
        return {
            "plan_approved": False,
            "messages": [AIMessage(content="Error: No plan was generated to approve")]
        }

    # Build plan summary for user
    plan_summary = f"""I've created the following execution plan:

**Analysis:** {plan['analysis']}

**Strategy:** {plan['execution_strategy'].upper()}

**Tasks:**
"""

    for idx, task in enumerate(plan['tasks'], 1):
        deps = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
        plan_summary += f"\n{idx}. **{task['description']}**\n"
        plan_summary += f"   - Agent: {task['agent_name']}\n"
        plan_summary += f"   - Rationale: {task['rationale']}{deps}\n"

    if mode == "review":
        # REVIEW mode: Show plan, auto-approve after display
        print("[Approval] REVIEW mode: Displaying plan for review")
        print(plan_summary)

        return {
            "plan_approved": True,
            "messages": [AIMessage(content=plan_summary + "\n\n✓ Plan approved (review mode)")]
        }

    elif mode == "interactive":
        # INTERACTIVE mode: Show plan and wait for explicit approval
        print("[Approval] INTERACTIVE mode: Waiting for user approval")

        # Present plan to user
        approval_message = AIMessage(content=plan_summary + "\n\nDo you approve this plan? (yes/no/modify)")

        # Use LangGraph interrupt to pause execution
        # User response will be captured and execution will resume
        user_response = interrupt(approval_message.content)

        # Process user response
        if user_response is None:
            # First time interrupt is called, return state with message
            return {
                "messages": [approval_message],
                "plan_approved": False
            }

        # User has responded, process their answer
        response_lower = str(user_response).lower().strip()

        if response_lower in ["yes", "y", "approve", "approved"]:
            print("[Approval] Plan approved by user")
            return {
                "plan_approved": True,
                "messages": [AIMessage(content="✓ Plan approved. Proceeding with execution...")]
            }

        elif response_lower in ["no", "n", "reject", "rejected"]:
            print("[Approval] Plan rejected by user")
            return {
                "plan_approved": False,
                "need_replan": True,
                "replan_reason": "User rejected the plan",
                "messages": [AIMessage(content="✗ Plan rejected. I'll create a new plan...")]
            }

        else:
            # User wants to modify - trigger replan with their feedback
            print(f"[Approval] User requested modifications: {user_response}")
            return {
                "plan_approved": False,
                "need_replan": True,
                "replan_reason": f"User requested modifications: {user_response}",
                "messages": [AIMessage(content=f"✓ Understood. I'll revise the plan based on your feedback: {user_response}")]
            }

    else:
        # AUTO mode - should never reach here due to conditional edge
        # But handle it gracefully just in case
        print("[Approval] AUTO mode: Auto-approving plan")
        return {
            "plan_approved": True,
            "messages": [AIMessage(content="✓ Plan auto-approved (auto mode)")]
        }
