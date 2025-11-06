"""
GitHub Repository Provisioner Agent

Creates GitHub repositories from templates.
Placeholder implementation that returns mock success responses.
"""

import logging
from langchain_core.runnables import RunnableConfig

from ..models.github_state import GitHubState, GitHubInput, GitHubOutput
from ..utils import create_base_state, create_simple_provisioner_graph

logger = logging.getLogger(__name__)


def transform_input(input_data: GitHubInput) -> GitHubState:
    """Transform external input to internal state"""
    return create_base_state(input_data, "GitHub Provisioner")


def validate_request(state: GitHubState) -> dict:
    """Validate the repository creation request"""

    request = state.get("original_request", "").lower()

    # Simple validation: check for key terms
    if "repo" in request or "repository" in request or "github" in request:
        logger.info("Request validated")
        return {
            "is_valid": True,
            "repo_name": "user-service",  # Placeholder extraction
            "template_name": "node-express-template",
            "organization": "my-org"
        }
    else:
        return {
            "is_valid": False,
            "validation_error": "Request does not appear to be about repository creation"
        }


def provision_repository(state: GitHubState) -> dict:
    """
    Provision GitHub repository (PLACEHOLDER)

    In a real implementation, this would:
    - Use GitHub API to create repository
    - Clone from template if specified
    - Set up branch protection rules
    - Configure webhooks
    """

    if not state.get("is_valid"):
        return {
            "status": "failed",
            "error": state.get("validation_error", "Invalid request")
        }

    repo_name = state.get("repo_name", "user-service")
    org = state.get("organization", "my-org")
    template = state.get("template_name", "express-api-template")

    logger.info(f"Creating repository: {org}/{repo_name} from template {template}")

    # PLACEHOLDER: Return mock success
    return {
        "repo_url": f"https://github.com/{org}/{repo_name}",
        "clone_url": f"git@github.com:{org}/{repo_name}.git",
        "template_used": template,
        "status": "success"
    }


def transform_output(state: GitHubState) -> GitHubOutput:
    """Transform internal state to external output"""

    output: GitHubOutput = {
        "repo_url": state.get("repo_url", ""),
        "clone_url": state.get("clone_url", ""),
        "status": state.get("status", "failed")
    }

    if state.get("template_used"):
        output["template_used"] = state["template_used"]

    if state.get("error"):
        output["error"] = state["error"]

    logger.info(f"Repository provisioned: {output.get('repo_url')}")

    return output


def create_github_provisioner_graph(config: RunnableConfig = None):
    """Factory function to create GitHub Provisioner Agent graph"""
    return create_simple_provisioner_graph(
        agent_name="GitHub Provisioner Agent",
        state_class=GitHubState,
        input_class=GitHubInput,
        output_class=GitHubOutput,
        transform_input_fn=transform_input,
        validate_fn=validate_request,
        provision_fn=provision_repository,
        transform_output_fn=transform_output,
        config=config
    )
