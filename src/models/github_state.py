"""
GitHub Provisioner Agent State Models

Defines the state and interface for the GitHub Repository Provisioner agent.
"""

from typing import TypedDict, NotRequired, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GitHubInput(TypedDict):
    """
    External API for GitHub Provisioner Agent

    Clients send messages describing the repository to create.
    Example: "Create a new repo called 'my-api' using the node-express-template"
    """

    # Required: User's request as A2A-compatible messages
    messages: Annotated[list[BaseMessage], add_messages]


class GitHubOutput(TypedDict):
    """
    External API for GitHub Provisioner Agent results

    Returns repository information after creation.
    """

    # Repository URL (HTTPS)
    repo_url: str

    # Clone URL (SSH)
    clone_url: str

    # Operation status
    status: str  # "success" or "failed"

    # Template used (optional)
    template_used: NotRequired[str]

    # Error message if failed
    error: NotRequired[str]


class GitHubState(TypedDict):
    """
    Internal state for GitHub Provisioner Agent

    Hidden from external clients. Used for orchestration logic.
    """

    # From external input
    messages: Annotated[list[BaseMessage], add_messages]

    # Request tracking
    request_id: str
    original_request: str

    # Extracted parameters
    repo_name: NotRequired[str]
    template_name: NotRequired[str]
    organization: NotRequired[str]
    visibility: NotRequired[str]  # "public" or "private"

    # Validation
    is_valid: bool
    validation_error: NotRequired[str]

    # Execution results
    repo_url: NotRequired[str]
    clone_url: NotRequired[str]
    status: str
    error: NotRequired[str]
