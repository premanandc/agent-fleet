"""
Environment Provisioner Agent

Creates dev, test, and staging environments for applications.
Placeholder implementation that returns mock success responses.
"""

import uuid
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from ..models.environment_state import EnvironmentState, EnvironmentInput, EnvironmentOutput

logger = logging.getLogger(__name__)


def transform_input(input_data: EnvironmentInput) -> EnvironmentState:
    """Transform external input to internal state"""

    # Extract user's message
    user_message = ""
    if input_data.get("messages"):
        last_msg = input_data["messages"][-1]
        if hasattr(last_msg, 'content'):
            user_message = last_msg.content
        elif isinstance(last_msg, dict):
            user_message = last_msg.get('content', '')

    logger.info(f"Environment Provisioner: {user_message[:100]}...")

    return {
        "messages": input_data["messages"],
        "request_id": str(uuid.uuid4()),
        "original_request": user_message,
        "is_valid": False,
        "status": "pending"
    }


def validate_request(state: EnvironmentState) -> dict:
    """Validate the environment provisioning request"""

    request = state.get("original_request", "").lower()

    # Simple validation: check for key terms
    if any(term in request for term in ["environment", "dev", "test", "staging", "deploy"]):
        logger.info("Request validated")

        # Extract GitHub URL (placeholder logic)
        github_url = "https://github.com/my-org/user-service"
        if "github.com" in request:
            # In real implementation, use regex to extract URL
            pass

        # Determine which environments to create
        env_types = []
        if "dev" in request:
            env_types.append("dev")
        if "test" in request:
            env_types.append("test")
        if "staging" in request:
            env_types.append("staging")

        # Default to all three if not specified
        if not env_types:
            env_types = ["dev", "test", "staging"]

        return {
            "is_valid": True,
            "github_repo_url": github_url,
            "app_name": "user-service",
            "environment_types": env_types,
            "platform": "kubernetes"
        }
    else:
        return {
            "is_valid": False,
            "validation_error": "Request does not appear to be about environment provisioning"
        }


def provision_environments(state: EnvironmentState) -> dict:
    """
    Provision environments (PLACEHOLDER)

    In a real implementation, this would:
    - Connect to Kubernetes/cloud provider API
    - Create namespaces/resource groups
    - Deploy application containers
    - Set up load balancers/ingress
    - Configure environment variables
    - Set up monitoring and logging
    """

    if not state.get("is_valid"):
        return {
            "status": "failed",
            "error": state.get("validation_error", "Invalid request")
        }

    app_name = state.get("app_name", "user-service")
    env_types = state.get("environment_types", ["dev", "test", "staging"])
    platform = state.get("platform", "kubernetes")

    logger.info(f"Creating {len(env_types)} environments for {app_name} on {platform}")

    # PLACEHOLDER: Return mock success
    environments = {}
    resource_ids = {}

    for env_type in env_types:
        environments[env_type] = f"https://{app_name}-{env_type}.example.com"
        resource_ids[env_type] = f"{app_name}-{env_type}-ns"

    return {
        "environments": environments,
        "namespace": f"{app_name}-namespace",
        "resource_ids": resource_ids,
        "platform": platform,
        "status": "success"
    }


def transform_output(state: EnvironmentState) -> EnvironmentOutput:
    """Transform internal state to external output"""

    output: EnvironmentOutput = {
        "environments": state.get("environments", {}),
        "status": state.get("status", "failed"),
        "platform": state.get("platform", "")
    }

    if state.get("namespace"):
        output["namespace"] = state["namespace"]

    if state.get("error"):
        output["error"] = state["error"]

    logger.info(f"Environments provisioned: {list(output.get('environments', {}).keys())}")

    return output


def create_environment_provisioner_graph(config: RunnableConfig = None):
    """Factory function to create Environment Provisioner Agent graph"""

    logger.info("Initializing Environment Provisioner Agent...")

    # Create state graph with explicit input/output schemas
    graph = StateGraph(
        EnvironmentState,          # Internal state
        input=EnvironmentInput,    # External input
        output=EnvironmentOutput   # External output
    )

    # Add nodes
    graph.add_node("transform_input", transform_input)
    graph.add_node("validate", validate_request)
    graph.add_node("provision", provision_environments)
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

    logger.info("Environment Provisioner Agent initialized successfully")

    return compiled_graph
