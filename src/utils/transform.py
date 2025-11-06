"""
Common transformation utilities for agents

Provides reusable functions for converting between external and internal state.
"""

import uuid
import logging
from typing import TypedDict, Any

logger = logging.getLogger(__name__)


def extract_user_message(input_data: TypedDict) -> str:
    """
    Extract user's message content from A2A message list

    Args:
        input_data: Input with messages field

    Returns:
        User message content as string
    """
    user_message = ""

    if input_data.get("messages"):
        last_msg = input_data["messages"][-1]
        if hasattr(last_msg, 'content'):
            user_message = last_msg.content
        elif isinstance(last_msg, dict):
            user_message = last_msg.get('content', '')

    return user_message


def create_base_state(
    input_data: TypedDict,
    agent_name: str,
    additional_fields: dict[str, Any] = None
) -> dict[str, Any]:
    """
    Create base internal state from external input

    Provides common initialization logic for all agents:
    - Extracts messages
    - Generates request_id
    - Extracts original_request
    - Sets initial validation/status flags

    Args:
        input_data: External input (e.g., GitHubInput, JenkinsInput)
        agent_name: Name of the agent for logging
        additional_fields: Optional additional fields to include in state

    Returns:
        Base internal state dictionary
    """
    user_message = extract_user_message(input_data)

    logger.info(f"{agent_name}: {user_message[:100]}...")

    state = {
        "messages": input_data["messages"],
        "request_id": str(uuid.uuid4()),
        "original_request": user_message,
        "is_valid": False,
        "status": "pending"
    }

    # Merge any additional fields
    if additional_fields:
        state.update(additional_fields)

    return state
