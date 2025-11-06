"""
Jenkins Provisioner Agent State Models

Defines the state and interface for the Jenkins CI/CD Provisioner agent.
"""

from typing import TypedDict, NotRequired, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class JenkinsInput(TypedDict):
    """
    External API for Jenkins Provisioner Agent

    Clients send messages describing the pipeline to create.
    Example: "Set up a Node.js CI/CD pipeline for https://github.com/org/my-api"
    """

    # Required: User's request as A2A-compatible messages
    messages: Annotated[list[BaseMessage], add_messages]


class JenkinsOutput(TypedDict):
    """
    External API for Jenkins Provisioner Agent results

    Returns pipeline information after creation.
    """

    # Jenkins job URL
    job_url: str

    # Pipeline type configured
    pipeline_type: str

    # Operation status
    status: str  # "success" or "failed"

    # Initial build number if triggered
    initial_build: NotRequired[str]

    # Error message if failed
    error: NotRequired[str]


class JenkinsState(TypedDict):
    """
    Internal state for Jenkins Provisioner Agent

    Hidden from external clients. Used for orchestration logic.
    """

    # From external input
    messages: Annotated[list[BaseMessage], add_messages]

    # Request tracking
    request_id: str
    original_request: str

    # Extracted parameters
    github_repo_url: NotRequired[str]
    pipeline_type: NotRequired[str]  # e.g., "node-build-test", "python-pytest"
    branch_pattern: NotRequired[str]  # e.g., "main", "develop", "feature/*"
    auto_trigger: NotRequired[bool]

    # Validation
    is_valid: bool
    validation_error: NotRequired[str]

    # Execution results
    job_url: NotRequired[str]
    job_name: NotRequired[str]
    initial_build: NotRequired[str]
    status: str
    error: NotRequired[str]
