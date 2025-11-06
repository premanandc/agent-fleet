"""
Validate Request Node (Guardrails)

Validates that incoming requests are on-topic for the ITEP platform.
Uses LLM-based classification to determine if the request is appropriate.
"""

import os
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from ..models.router_state import RouterState
from ..llm.factory import LLMFactory
from ..utils import PromptManager

logger = logging.getLogger(__name__)


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
    logger.info(f"Checking request: {user_request[:100]}...")

    # Get validation prompt from PromptManager
    validation_prompt = PromptManager.get_prompt(
        "validation",
        user_request=user_request
    )

    # Call LLM for classification
    llm = LLMFactory.create(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL"),
        temperature=PromptManager.get_temperature("validation")
    )

    messages = [
        SystemMessage(content=PromptManager.get_system_message("validation")),
        HumanMessage(content=validation_prompt)
    ]

    try:
        response = llm.invoke(messages)

        # Parse response - handle code blocks
        import json
        import re

        content = response.content.strip()

        # Try to extract JSON from code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)

        validation_result = json.loads(content)

        is_valid = validation_result.get("is_valid", False)
        reasoning = validation_result.get("reasoning", "")

        logger.info(f"Result: {'VALID' if is_valid else 'INVALID'} - {reasoning}")

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
        logger.error(f"Error during validation: {e}")
        # Default to rejecting on error
        return {
            "is_valid": False,
            "rejection_reason": f"Validation error: {str(e)}",
            "original_request": user_request
        }
