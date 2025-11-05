"""
Agent Discovery Utility

Functions for discovering agents via LangGraph Server and fetching their capabilities.
"""

import os
import logging
import httpx
from typing import Dict, List, Optional

from ..models.router_state import AgentCapability

logger = logging.getLogger(__name__)


def _get_langgraph_url() -> str:
    """Get LangGraph Server URL from environment configuration"""
    return os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:2024")


def _is_subordinate_agent(graph_id: str) -> bool:
    """
    Check if agent is a subordinate agent (not the router itself)

    Args:
        graph_id: The graph ID of the agent

    Returns:
        True if agent should be processed as a subordinate
    """
    return graph_id != "router"


def _extract_capabilities_from_card(
    card: Dict,
    graph_id: str,
    assistant_id: str
) -> AgentCapability:
    """
    Extract AgentCapability from A2A agent card JSON

    Args:
        card: A2A agent card dictionary
        graph_id: Graph ID for fallback name
        assistant_id: Assistant ID for the capability

    Returns:
        AgentCapability object with extracted metadata
    """
    # Extract skills from card
    skills = card.get("skills", [])
    skill_names = [
        skill.get("name", "")
        for skill in skills
        if isinstance(skill, dict)
    ]
    capabilities = skill_names if skill_names else []

    return AgentCapability(
        agent_id=assistant_id,
        name=card.get("name", graph_id),
        capabilities=capabilities,
        skills=skill_names,
        description=card.get("description", "")
    )


async def _fetch_all_assistants(
    client: httpx.AsyncClient,
    langgraph_url: str
) -> List[Dict]:
    """
    Fetch all assistants from LangGraph Server

    Args:
        client: HTTP client for making requests
        langgraph_url: Base URL of LangGraph Server

    Returns:
        List of assistant dictionaries

    Raises:
        httpx.HTTPError: If request fails
    """
    search_response = await client.post(
        f"{langgraph_url}/assistants/search",
        json={},
        timeout=10.0
    )
    search_response.raise_for_status()
    return search_response.json()


async def _fetch_agent_card(
    client: httpx.AsyncClient,
    langgraph_url: str,
    assistant_id: str,
    graph_id: str
) -> Optional[Dict]:
    """
    Fetch A2A agent card for a specific assistant

    Args:
        client: HTTP client for making requests
        langgraph_url: Base URL of LangGraph Server
        assistant_id: Unique assistant ID
        graph_id: Graph ID for logging

    Returns:
        Agent card dictionary or None if fetch fails
    """
    try:
        card_response = await client.get(
            f"{langgraph_url}/.well-known/agent-card.json",
            params={"assistant_id": assistant_id},
            timeout=5.0
        )
        card_response.raise_for_status()
        return card_response.json()

    except httpx.HTTPStatusError as e:
        # Agent doesn't have A2A card endpoint - skip silently
        if e.response.status_code == 404:
            logger.info(f"Skipping {graph_id} (no A2A card endpoint)")
        else:
            logger.warning(f"HTTP {e.response.status_code} fetching card for {graph_id}")
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch card for {graph_id}: {e}")
        return None


async def _build_agent_registry(
    client: httpx.AsyncClient,
    langgraph_url: str,
    assistants: List[Dict]
) -> Dict[str, AgentCapability]:
    """
    Build agent registry from list of assistants

    Processes each assistant by:
    1. Filtering out non-subordinate agents (router)
    2. Fetching agent cards
    3. Extracting capabilities
    4. Building registry dictionary

    Args:
        client: HTTP client for making requests
        langgraph_url: Base URL of LangGraph Server
        assistants: List of assistant dictionaries from search

    Returns:
        Dictionary mapping agent_id to AgentCapability
    """
    agent_registry = {}

    for assistant in assistants:
        assistant_id = assistant.get("assistant_id")
        graph_id = assistant.get("graph_id")

        # Skip non-subordinate agents
        if not _is_subordinate_agent(graph_id):
            logger.info(f"Skipping {graph_id} (not a subordinate agent)")
            continue

        # Fetch agent card
        card = await _fetch_agent_card(client, langgraph_url, assistant_id, graph_id)
        if card is None:
            continue

        # Extract capabilities from card
        capability = _extract_capabilities_from_card(card, graph_id, assistant_id)

        # Register agent
        agent_registry[assistant_id] = capability
        logger.info(f"Registered agent: {capability['name']} ({assistant_id})")

    return agent_registry


async def discover_agents_from_langgraph() -> Dict[str, AgentCapability]:
    """
    Discovers available agents from LangGraph Server dynamically

    Orchestrates the agent discovery process by:
    1. Fetching all assistants from LangGraph Server
    2. Building a registry of subordinate agent capabilities

    All agent metadata (name, description, capabilities, skills) is extracted
    from the A2A agent cards - no hardcoded fallbacks are used.

    Returns:
        Dictionary mapping agent_id to AgentCapability

    Raises:
        Exception: If LangGraph Server is unreachable or returns errors
    """
    langgraph_url = _get_langgraph_url()

    try:
        async with httpx.AsyncClient() as client:
            assistants = await _fetch_all_assistants(client, langgraph_url)
            logger.info(f"Found {len(assistants)} assistants")

            registry = await _build_agent_registry(client, langgraph_url, assistants)
            logger.info(f"Successfully registered {len(registry)} agents")

            return registry

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
