"""
Agent Card Registry

Provides agent cards for A2A discovery.
LangGraph Server will use these cards when agents are queried via /a2a/{id}/card

Only the Router card is hardcoded here since it's not discovered as a subordinate agent.
All other agents are discovered dynamically via A2A protocol.
"""


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


# Card registry - only router is hardcoded
AGENT_CARDS = {
    "router": ROUTER_CARD
}


def get_agent_card(graph_id: str) -> dict:
    """
    Get agent card by graph ID

    Args:
        graph_id: The graph identifier (currently only "router" is supported)

    Returns:
        Agent card dictionary, or a default unknown agent card if not found
    """
    return AGENT_CARDS.get(graph_id, {
        "name": "Unknown Agent",
        "description": "No card available",
        "capabilities": [],
        "skills": []
    })
