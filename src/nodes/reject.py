"""
Reject Request Node

Handles off-topic requests by creating a polite rejection message.
This node is reached when the validation guardrails determine a request
is not appropriate for the ITEP platform.
"""

from langchain_core.messages import AIMessage

from ..models.router_state import RouterState


def reject_request(state: RouterState) -> dict:
    """
    Creates a rejection message for off-topic requests

    Args:
        state: Current router state with rejection_reason populated

    Returns:
        Updated state with final_response and rejection message added to messages
    """

    rejection_reason = state.get("rejection_reason", "Request is not supported")

    print(f"[Reject] Rejecting request: {rejection_reason}")

    # Create polite rejection message
    rejection_message = f"""I apologize, but I'm unable to help with this request.

Reason: {rejection_reason}

I'm specifically designed to assist with IT Engineering Productivity tasks including:
- Software development productivity
- Code quality analysis (SonarQube)
- CI/CD issues (Jenkins, build failures, deployments)
- Issue tracking (JIRA tickets)
- Code repository operations (Git, GitHub, pull requests)
- Development workflow automation

Please rephrase your request to focus on one of these areas, or reach out to the appropriate support channel for your needs.
"""

    # Create AI message with rejection
    ai_message = AIMessage(content=rejection_message)

    return {
        "messages": [ai_message],
        "final_response": rejection_message
    }
