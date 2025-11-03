"""
Agent Discovery Utility

Functions for discovering agents via LangGraph Server and fetching their capabilities.
"""

import os
import requests
from typing import Dict

from ..models.router_state import AgentCapability


def discover_agents_from_langgraph() -> Dict[str, AgentCapability]:
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
        # 1. Discover all assistants
        search_response = requests.post(
            f"{langgraph_url}/assistants/search",
            json={},
            timeout=10
        )
        search_response.raise_for_status()
        assistants = search_response.json()

        print(f"[Discovery] Found {len(assistants)} assistants")

        # 2. Fetch capabilities for each agent
        agent_registry = {}

        for assistant in assistants:
            assistant_id = assistant.get("assistant_id")
            graph_id = assistant.get("graph_id")

            # Skip the router itself
            if graph_id == "router":
                continue

            try:
                # Fetch agent card
                card_response = requests.get(
                    f"{langgraph_url}/a2a/{assistant_id}/card",
                    timeout=5
                )
                card_response.raise_for_status()
                card = card_response.json()

                # Build capability object
                capability = AgentCapability(
                    agent_id=assistant_id,
                    name=card.get("name", graph_id),
                    capabilities=card.get("capabilities", []),
                    skills=card.get("skills", []),
                    description=card.get("description", "")
                )

                agent_registry[assistant_id] = capability
                print(f"[Discovery] Registered agent: {capability['name']} ({assistant_id})")

            except Exception as e:
                print(f"[Discovery] Warning: Failed to fetch card for {assistant_id}: {e}")
                continue

        print(f"[Discovery] Successfully registered {len(agent_registry)} agents")
        return agent_registry

    except requests.exceptions.RequestException as e:
        print(f"[Discovery] Error: Failed to connect to LangGraph Server at {langgraph_url}: {e}")
        # Return empty registry rather than failing - allows testing without server
        return {}


def refresh_agent_registry() -> Dict[str, AgentCapability]:
    """
    Re-discovers agents (for API endpoint to trigger refresh)

    Returns:
        Updated agent registry
    """
    print("[Discovery] Refreshing agent registry...")
    return discover_agents_from_langgraph()
