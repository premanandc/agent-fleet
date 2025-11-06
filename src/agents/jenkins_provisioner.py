"""
Jenkins CI/CD Provisioner Agent

Creates Jenkins pipelines for applications.
Placeholder implementation that returns mock success responses.
"""

import uuid
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from ..models.jenkins_state import JenkinsState, JenkinsInput, JenkinsOutput

logger = logging.getLogger(__name__)


def transform_input(input_data: JenkinsInput) -> JenkinsState:
    """Transform external input to internal state"""

    # Extract user's message
    user_message = ""
    if input_data.get("messages"):
        last_msg = input_data["messages"][-1]
        if hasattr(last_msg, 'content'):
            user_message = last_msg.content
        elif isinstance(last_msg, dict):
            user_message = last_msg.get('content', '')

    logger.info(f"Jenkins Provisioner: {user_message[:100]}...")

    return {
        "messages": input_data["messages"],
        "request_id": str(uuid.uuid4()),
        "original_request": user_message,
        "is_valid": False,
        "status": "pending"
    }


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

    logger.info("Initializing Jenkins Provisioner Agent...")

    # Create state graph with explicit input/output schemas
    graph = StateGraph(
        JenkinsState,          # Internal state
        input=JenkinsInput,    # External input
        output=JenkinsOutput   # External output
    )

    # Add nodes
    graph.add_node("transform_input", transform_input)
    graph.add_node("validate", validate_request)
    graph.add_node("provision", provision_pipeline)
    graph.add_node("transform_output", transform_output)

    # Build flow
    graph.add_edge(START, "transform_input")
    graph.add_edge("transform_input", "validate")
    graph.add_edge("validate", "provision")
    graph.add_edge("provision", "transform_output")
    graph.add_edge("transform_output", END)

    # Compile
    checkpointer = MemorySaver()
    compiled_graph = graph.compile(checkpointer=checkpointer)

    logger.info("Jenkins Provisioner Agent initialized successfully")

    return compiled_graph
