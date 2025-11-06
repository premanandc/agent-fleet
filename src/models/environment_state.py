"""
Environment Provisioner Agent State Models

Defines the state and interface for the Environment Provisioner agent.
"""

from typing import TypedDict, NotRequired, Annotated, Dict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class EnvironmentInput(TypedDict):
    """
    External API for Environment Provisioner Agent

    Clients send messages describing the environments to create.
    Example: "Provision dev, test, and staging environments for https://github.com/org/my-api"
    """

    # Required: User's request as A2A-compatible messages
    messages: Annotated[list[BaseMessage], add_messages]


class EnvironmentOutput(TypedDict):
    """
    External API for Environment Provisioner Agent results

    Returns environment URLs and configuration after provisioning.
    """

    # Environment URLs (e.g., {"dev": "https://app-dev.example.com", ...})
    environments: Dict[str, str]

    # Operation status
    status: str  # "success" or "failed"

    # Platform used (e.g., "kubernetes", "docker-compose")
    platform: str

    # Namespace or resource group
    namespace: NotRequired[str]

    # Error message if failed
    error: NotRequired[str]


class EnvironmentState(TypedDict):
    """
    Internal state for Environment Provisioner Agent

    Hidden from external clients. Used for orchestration logic.
    """

    # From external input
    messages: Annotated[list[BaseMessage], add_messages]

    # Request tracking
    request_id: str
    original_request: str

    # Extracted parameters
    github_repo_url: NotRequired[str]
    app_name: NotRequired[str]
    environment_types: NotRequired[list[str]]  # e.g., ["dev", "test", "staging"]
    platform: NotRequired[str]  # e.g., "kubernetes", "docker-compose"

    # Validation
    is_valid: bool
    validation_error: NotRequired[str]

    # Execution results
    environments: NotRequired[Dict[str, str]]  # env_name -> URL mapping
    namespace: NotRequired[str]
    resource_ids: NotRequired[Dict[str, str]]  # env_name -> resource ID mapping
    status: str
    error: NotRequired[str]
