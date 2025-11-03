#!/usr/bin/env python3
"""
Quick Local Test for Router Agent

This script tests the Router Agent locally without needing LangGraph Server.
It uses mocked agent discovery and runs a simple validation flow.
"""

import os
from unittest.mock import patch, Mock

# Set environment variables for testing
os.environ["ANTHROPIC_API_KEY"] = "test-key-replace-with-real-key"
os.environ["LLM_PROVIDER"] = "anthropic"
os.environ["LLM_MODEL"] = "claude-3-5-sonnet-20241022"

from src.agents.router_agent import create_router_graph, create_initial_state


def test_router_creation():
    """Test that Router Agent can be created"""
    print("Testing Router Agent Creation...")

    # Mock agent discovery to avoid needing LangGraph Server
    with patch("src.utils.discovery.requests.post") as mock_post, \
         patch("src.utils.discovery.requests.get") as mock_get:

        # Mock discovery response
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: [
                {"assistant_id": "test-agent", "graph_id": "test"}
            ]
        )

        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "name": "Test Agent",
                "capabilities": ["testing"],
                "skills": ["Run tests"],
                "description": "A test agent"
            }
        )

        # Create router graph
        graph = create_router_graph()

        print("✓ Router Agent created successfully")
        print(f"✓ Discovered {len(graph.agent_registry)} agents")

        # Verify graph structure
        assert hasattr(graph, "agent_registry")
        assert len(graph.agent_registry) == 1

        print("\nGraph Structure:")
        print(f"  - Nodes: validate, reject, plan, approval, execute, analyze, aggregate")
        print(f"  - Agent Registry: {list(graph.agent_registry.keys())}")

        return graph


def test_initial_state():
    """Test initial state creation"""
    print("\nTesting Initial State Creation...")

    state = create_initial_state(
        "Test request",
        mode="auto",
        max_replans=2
    )

    print("✓ Initial state created successfully")
    print(f"  - Request: {state['original_request']}")
    print(f"  - Mode: {state['mode']}")
    print(f"  - Max Replans: {state['max_replans']}")

    assert state["original_request"] == "Test request"
    assert state["mode"] == "auto"
    assert state["max_replans"] == 2

    return state


def main():
    """Run all tests"""
    print("=" * 60)
    print("Router Agent Local Test")
    print("=" * 60)
    print()

    try:
        # Test 1: Graph creation
        graph = test_router_creation()

        # Test 2: State creation
        state = test_initial_state()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        print("Next Steps:")
        print("1. Set ANTHROPIC_API_KEY in .env")
        print("2. Start LangGraph Server: langgraph dev")
        print("3. Deploy subordinate agents (Coda, AskCody)")
        print("4. Test with real requests via API")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
