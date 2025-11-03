"""
Validate Request Node (Guardrails)

Validates that incoming requests are on-topic for the ITEP platform.
Uses LLM-based classification to determine if the request is appropriate.
"""

import os
from langchain_core.messages import SystemMessage, HumanMessage

from ..models.router_state import RouterState
from ..llm.factory import LLMFactory


def validate_request(state: RouterState) -> dict:
    """
    Validates user request using built-in guardrails

    Checks if the request is on-topic for ITEP platform
    (software development productivity, CI/CD, code quality, etc.)

    Args:
        state: Current router state with user messages

    Returns:
        Updated state with validation result
    """

    # Extract user request from messages
    latest_message = state["messages"][-1] if state.get("messages") else None

    if not latest_message:
        return {
            "is_valid": False,
            "rejection_reason": "No user message provided",
            "original_request": ""
        }

    user_request = latest_message.content
    print(f"[Validate] Checking request: {user_request[:100]}...")

    # Build validation prompt
    validation_prompt = f"""You are a guardrail system for the ITEP (IT Engineering Productivity) Agentic AI Platform.

USER REQUEST:
{user_request}

YOUR TASK:
Determine if this request is on-topic for the ITEP platform.

ITEP handles:
- Software development productivity
- Code quality (SonarQube, code review)
- CI/CD issues (Jenkins, build failures, deployment)
- Issue tracking (JIRA tickets)
- Code repository operations (Git, GitHub, pull requests)
- Development workflow automation

ITEP does NOT handle:
- General knowledge questions
- Weather, news, or entertainment
- Personal advice
- Non-technical topics
- Requests outside software development

Respond with JSON:
{{
  "is_valid": true or false,
  "reasoning": "Brief explanation of your decision"
}}
"""

    # Call LLM for classification
    llm = LLMFactory.create(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL"),
        temperature=0.3  # Lower temperature for consistent classification
    )

    messages = [
        SystemMessage(content="You are an expert at classifying software development requests."),
        HumanMessage(content=validation_prompt)
    ]

    try:
        response = llm.invoke(messages)

        # Parse response
        import json
        validation_result = json.loads(response.content)

        is_valid = validation_result.get("is_valid", False)
        reasoning = validation_result.get("reasoning", "")

        print(f"[Validate] Result: {'VALID' if is_valid else 'INVALID'} - {reasoning}")

        if is_valid:
            return {
                "is_valid": True,
                "rejection_reason": None,
                "original_request": user_request
            }
        else:
            return {
                "is_valid": False,
                "rejection_reason": f"Off-topic request: {reasoning}",
                "original_request": user_request
            }

    except Exception as e:
        print(f"[Validate] Error during validation: {e}")
        # Default to rejecting on error
        return {
            "is_valid": False,
            "rejection_reason": f"Validation error: {str(e)}",
            "original_request": user_request
        }
