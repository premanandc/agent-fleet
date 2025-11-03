"""
Agent Card Registry

Provides agent cards for A2A discovery.
LangGraph Server will use these cards when agents are queried via /a2a/{id}/card
"""

from src.agents.quick_agent import AGENT_CARD as QUICK_CARD
from src.agents.slow_agent import AGENT_CARD as SLOW_CARD


# Router Agent Card
ROUTER_CARD = {
    "name": "Router",
    "version": "1.0.0",
    "description": "Intelligent orchestrator for ITEP platform. Discovers agents, breaks down requests, and coordinates execution.",
    "capabilities": [
        "orchestration",
        "task-breakdown",
        "multi-agent-coordination",
        "request-validation"
    ],
    "skills": [
        "Decompose complex requests into tasks",
        "Match tasks to specialized agents",
        "Coordinate parallel and sequential execution",
        "Synthesize results from multiple agents",
        "Validate requests against platform scope"
    ],
    "input_mode": "messages",
    "output_mode": "messages",
    "features": {
        "auto_discovery": True,
        "capability_driven": True,
        "replanning": True,
        "human_in_loop": True
    },
    "execution_modes": [
        "auto",
        "interactive",
        "review"
    ]
}


# Card registry
AGENT_CARDS = {
    "router": ROUTER_CARD,
    "quick_agent": QUICK_CARD,
    "slow_agent": SLOW_CARD
}


def get_agent_card(graph_id: str) -> dict:
    """
    Get agent card by graph ID

    Args:
        graph_id: The graph identifier (router, quick_agent, slow_agent)

    Returns:
        Agent card dictionary
    """
    return AGENT_CARDS.get(graph_id, {
        "name": "Unknown Agent",
        "description": "No card available",
        "capabilities": [],
        "skills": []
    })
