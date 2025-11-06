"""
Jenkins CI/CD Provisioner Agent

Creates Jenkins pipelines for applications.
Placeholder implementation that returns mock success responses.
"""

import logging
from langchain_core.runnables import RunnableConfig

from ..models.jenkins_state import JenkinsState, JenkinsInput, JenkinsOutput
from ..utils import create_base_state, create_simple_provisioner_graph

logger = logging.getLogger(__name__)


def transform_input(input_data: JenkinsInput) -> JenkinsState:
    """Transform external input to internal state"""
    return create_base_state(input_data, "Jenkins Provisioner")


def validate_request(state: JenkinsState) -> dict:
    """Validate the pipeline creation request"""

    request = state.get("original_request", "").lower()

    # Simple validation: check for key terms
    if any(term in request for term in ["pipeline", "ci/cd", "cicd", "jenkins", "build"]):
        logger.info("Request validated")

        # Extract GitHub URL (placeholder logic)
        github_url = "https://github.com/my-org/user-service"
        if "github.com" in request:
            # In real implementation, use regex to extract URL
            pass

        return {
            "is_valid": True,
            "github_repo_url": github_url,
            "pipeline_type": "node-build-test-deploy",
            "branch_pattern": "main",
            "auto_trigger": True
        }
    else:
        return {
            "is_valid": False,
            "validation_error": "Request does not appear to be about CI/CD pipeline creation"
        }


def provision_pipeline(state: JenkinsState) -> dict:
    """
    Provision Jenkins pipeline (PLACEHOLDER)

    In a real implementation, this would:
    - Connect to Jenkins API
    - Create Jenkins job with Jenkinsfile
    - Configure webhooks in GitHub
    - Set up credentials
    - Trigger initial build
    """

    if not state.get("is_valid"):
        return {
            "status": "failed",
            "error": state.get("validation_error", "Invalid request")
        }

    github_url = state.get("github_repo_url", "")
    pipeline_type = state.get("pipeline_type", "node-build-test-deploy")

    # Extract repo name from URL
    repo_name = github_url.split("/")[-1] if github_url else "user-service"

    logger.info(f"Creating Jenkins pipeline for {repo_name} (type: {pipeline_type})")

    # PLACEHOLDER: Return mock success
    return {
        "job_url": f"https://jenkins.example.com/job/{repo_name}",
        "job_name": repo_name,
        "pipeline_type": pipeline_type,
        "initial_build": "1",
        "status": "success"
    }


def transform_output(state: JenkinsState) -> JenkinsOutput:
    """Transform internal state to external output"""

    output: JenkinsOutput = {
        "job_url": state.get("job_url", ""),
        "pipeline_type": state.get("pipeline_type", ""),
        "status": state.get("status", "failed")
    }

    if state.get("initial_build"):
        output["initial_build"] = state["initial_build"]

    if state.get("error"):
        output["error"] = state["error"]

    logger.info(f"Pipeline provisioned: {output.get('job_url')}")

    return output


def create_jenkins_provisioner_graph(config: RunnableConfig = None):
    """Factory function to create Jenkins Provisioner Agent graph"""
    return create_simple_provisioner_graph(
        agent_name="Jenkins Provisioner Agent",
        state_class=JenkinsState,
        input_class=JenkinsInput,
        output_class=JenkinsOutput,
        transform_input_fn=transform_input,
        validate_fn=validate_request,
        provision_fn=provision_pipeline,
        transform_output_fn=transform_output,
        config=config
    )
