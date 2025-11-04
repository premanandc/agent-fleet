"""
Agent Discovery Utility

Functions for discovering agents via LangGraph Server and fetching their capabilities.
"""

import os
import logging
import httpx
from typing import Dict

from ..models.router_state import AgentCapability

logger = logging.getLogger(__name__)


# Fallback agent metadata for known agents
# Used when A2A card doesn't provide detailed capabilities
AGENT_METADATA = {
    "quick_agent": {
        "name": "QuickAgent",
        "description": "Fast analysis agent for quick validation and checks. Optimized for speed over depth.",
        "capabilities": [
            "analysis",
            "quick-check",
            "validation",
            "syntax-checking"
        ],
        "skills": [
            "Analyze code syntax",
            "Quick validation",
            "Fast security scans",
            "Basic code review",
            "Structure analysis"
        ]
    },
    "slow_agent": {
        "name": "SlowAgent",
        "description": "Deep analysis agent for comprehensive code review and remediation. Optimized for thoroughness.",
        "capabilities": [
            "deep-analysis",
            "remediation",
            "sonarqube",
            "code-quality",
            "security-analysis"
        ],
        "skills": [
            "Fix SonarQube violations",
            "Deep code analysis",
            "Security vulnerability fixes",
            "Code quality improvements",
            "Comprehensive refactoring"
        ]
    }
}


async def discover_agents_from_langgraph() -> Dict[str, AgentCapability]:
    """
    Discovers available agents from LangGraph Server

    This function:
    1. Calls /assistants/search to find all available agents
    2. Fetches each agent's card via /a2a/{id}/card
    3. Builds a registry of agent capabilities

    Returns:
        Dictionary mapping agent_id to AgentCapability

    Raises:
        Exception: If LangGraph Server is unreachable or returns errors
    """

    langgraph_url = os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:2024")

    try:
        async with httpx.AsyncClient() as client:
            # 1. Discover all assistants
            search_response = await client.post(
                f"{langgraph_url}/assistants/search",
                json={},
                timeout=10.0
            )
            search_response.raise_for_status()
            assistants = search_response.json()

            logger.info(f"Found {len(assistants)} assistants")

            # 2. Fetch capabilities for each agent
            agent_registry = {}

            for assistant in assistants:
                assistant_id = assistant.get("assistant_id")
                graph_id = assistant.get("graph_id")

                # Skip the router itself and task_breakdown (legacy)
                if graph_id in ["router", "task_breakdown"]:
                    logger.info(f"Skipping {graph_id} (not a subordinate agent)")
                    continue

                try:
                    # Fetch agent card via .well-known endpoint
                    card_response = await client.get(
                        f"{langgraph_url}/.well-known/agent-card.json",
                        params={"assistant_id": assistant_id},
                        timeout=5.0
                    )
                    card_response.raise_for_status()
                    card = card_response.json()

                    # Build capability object from A2A card format
                    # Try to use fallback metadata for known agents first
                    if graph_id in AGENT_METADATA:
                        # Use detailed metadata from our fallback registry
                        metadata = AGENT_METADATA[graph_id]
                        capability = AgentCapability(
                            agent_id=assistant_id,
                            name=metadata["name"],
                            capabilities=metadata["capabilities"],
                            skills=metadata["skills"],
                            description=metadata["description"]
                        )
                        logger.info(f"Using fallback metadata for {graph_id}")
                    else:
                        # Extract from A2A card (for dynamically added agents)
                        skills = card.get("skills", [])
                        skill_names = [skill.get("name", "") for skill in skills if isinstance(skill, dict)]
                        capabilities = skill_names if skill_names else []

                        capability = AgentCapability(
                            agent_id=assistant_id,
                            name=card.get("name", graph_id),
                            capabilities=capabilities,
                            skills=skill_names,
                            description=card.get("description", "")
                        )

                    agent_registry[assistant_id] = capability
                    logger.info(f"Registered agent: {capability['name']} ({assistant_id})")

                except httpx.HTTPStatusError as e:
                    # Agent doesn't have A2A card endpoint - skip silently
                    if e.response.status_code == 404:
                        logger.info(f"Skipping {graph_id} (no A2A card endpoint)")
                    else:
                        logger.warning(f"HTTP {e.response.status_code} fetching card for {graph_id}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to fetch card for {graph_id}: {e}")
                    continue

            logger.info(f"Successfully registered {len(agent_registry)} agents")
            return agent_registry

    except httpx.HTTPError as e:
        logger.error(f"Failed to connect to LangGraph Server at {langgraph_url}: {e}")
        # Return empty registry rather than failing - allows testing without server
        return {}


async def refresh_agent_registry() -> Dict[str, AgentCapability]:
    """
    Re-discovers agents (for API endpoint to trigger refresh)

    Returns:
        Updated agent registry
    """
    logger.info("Refreshing agent registry...")
    return await discover_agents_from_langgraph()
