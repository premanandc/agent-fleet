"""
Integration Tests for Router Agent Graph

Tests the complete graph flow with mocked LLM and A2A calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage

from src.agents.router_agent import create_router_graph, create_initial_state
from src.models.router_state import AgentCapability


# ========== Fixtures ==========

@pytest.fixture
def mock_agent_registry():
    """Mock agent registry"""
    return {
        "coda-agent": AgentCapability(
            agent_id="coda-agent",
            name="Coda",
            capabilities=["code-quality", "sonarqube"],
            skills=["Fix SonarQube violations"],
            description="SonarQube remediation specialist"
        )
    }


@pytest.fixture
def mock_llm_responses():
    """Mock LLM responses for different nodes"""
    return {
        "validate": Mock(content='{"is_valid": true, "reasoning": "Valid request"}'),
        "plan": Mock(content='{"analysis": "Need to fix SonarQube violations", "execution_strategy": "sequential", "tasks": [{"description": "Fix violations", "agent_id": "coda-agent", "agent_name": "Coda", "dependencies": [], "rationale": "Coda is the SonarQube expert"}]}'),
        "analyze": Mock(content='{"is_sufficient": true, "reasoning": "All tasks completed successfully", "replan_strategy": null}'),
        "aggregate": Mock(content="# Results\n\nSuccessfully fixed all SonarQube violations.")
    }


# ========== Graph Flow Tests ==========

class TestRouterGraphFlow:
    """Tests for complete graph execution flows"""

    @patch("src.utils.discovery.requests.post")
    @patch("src.utils.discovery.requests.get")
    @patch("src.nodes.validate.LLMFactory")
    @patch("src.nodes.plan.LLMFactory")
    @patch("src.nodes.execute.requests.post")
    @patch("src.nodes.analyze.LLMFactory")
    @patch("src.nodes.aggregate.LLMFactory")
    def test_happy_path_auto_mode(
        self,
        mock_aggregate_llm,
        mock_analyze_llm,
        mock_execute_post,
        mock_plan_llm,
        mock_validate_llm,
        mock_discovery_get,
        mock_discovery_post,
        mock_llm_responses
    ):
        """Test successful execution in AUTO mode (no human approval)"""

        # Mock agent discovery
        mock_discovery_post.return_value = Mock(
            status_code=200,
            json=lambda: [
                {"assistant_id": "coda-agent", "graph_id": "coda"}
            ]
        )
        mock_discovery_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "name": "Coda",
                "capabilities": ["code-quality"],
                "skills": ["Fix SonarQube violations"],
                "description": "SonarQube specialist"
            }
        )

        # Mock LLM responses for each node
        mock_validate_llm.create.return_value = Mock(invoke=lambda _: mock_llm_responses["validate"])
        mock_plan_llm.create.return_value = Mock(invoke=lambda _: mock_llm_responses["plan"])
        mock_analyze_llm.create.return_value = Mock(invoke=lambda _: mock_llm_responses["analyze"])
        mock_aggregate_llm.create.return_value = Mock(invoke=lambda _: mock_llm_responses["aggregate"])

        # Mock A2A execution
        mock_execute_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "messages": [
                    {"role": "assistant", "content": "Fixed 5 SonarQube violations"}
                ]
            }
        )
        mock_execute_post.return_value.raise_for_status = Mock()

        # Create graph and initial state
        graph = create_router_graph()
        initial_state = create_initial_state(
            "Fix the SonarQube violations in my code",
            mode="auto"
        )

        # Execute graph
        final_state = graph.invoke(
            initial_state,
            config={"configurable": {"agent_registry": graph.agent_registry}}
        )

        # Assertions
        assert final_state["is_valid"] is True
        assert final_state["plan"] is not None
        assert len(final_state["task_results"]) > 0
        assert final_state["final_response"] is not None
        assert "SonarQube" in final_state["final_response"]

    @patch("src.utils.discovery.requests.post")
    @patch("src.utils.discovery.requests.get")
    @patch("src.nodes.validate.LLMFactory")
    def test_rejection_flow(
        self,
        mock_validate_llm,
        mock_discovery_get,
        mock_discovery_post
    ):
        """Test rejection of off-topic request"""

        # Mock agent discovery
        mock_discovery_post.return_value = Mock(
            status_code=200,
            json=lambda: []
        )

        # Mock validation rejection
        mock_validate_llm.create.return_value = Mock(
            invoke=lambda _: Mock(
                content='{"is_valid": false, "reasoning": "Weather is off-topic"}'
            )
        )

        # Create graph and initial state
        graph = create_router_graph()
        initial_state = create_initial_state(
            "What's the weather today?",
            mode="auto"
        )

        # Execute graph
        final_state = graph.invoke(
            initial_state,
            config={"configurable": {"agent_registry": {}}}
        )

        # Assertions
        assert final_state["is_valid"] is False
        assert final_state["rejection_reason"] is not None
        assert final_state["final_response"] is not None
        assert "unable to help" in final_state["final_response"].lower()

    @patch("src.utils.discovery.requests.post")
    @patch("src.utils.discovery.requests.get")
    @patch("src.nodes.validate.LLMFactory")
    @patch("src.nodes.plan.LLMFactory")
    @patch("src.nodes.execute.requests.post")
    @patch("src.nodes.analyze.LLMFactory")
    def test_replanning_flow(
        self,
        mock_analyze_llm,
        mock_execute_post,
        mock_plan_llm,
        mock_validate_llm,
        mock_discovery_get,
        mock_discovery_post
    ):
        """Test replanning when results are insufficient"""

        # Mock agent discovery
        mock_discovery_post.return_value = Mock(
            status_code=200,
            json=lambda: [
                {"assistant_id": "coda-agent", "graph_id": "coda"}
            ]
        )
        mock_discovery_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "name": "Coda",
                "capabilities": ["code-quality"],
                "skills": ["Fix SonarQube violations"],
                "description": "SonarQube specialist"
            }
        )

        # Mock validation
        mock_validate_llm.create.return_value = Mock(
            invoke=lambda _: Mock(
                content='{"is_valid": true, "reasoning": "Valid request"}'
            )
        )

        # Mock planning (will be called twice due to replan)
        plan_call_count = [0]

        def mock_plan_invoke(_):
            plan_call_count[0] += 1
            return Mock(
                content='{"analysis": "Need SonarQube fixes", "execution_strategy": "sequential", "tasks": [{"description": "Fix violations", "agent_id": "coda-agent", "agent_name": "Coda", "dependencies": [], "rationale": "Expert"}]}'
            )

        mock_plan_llm.create.return_value = Mock(invoke=mock_plan_invoke)

        # Mock execution
        mock_execute_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "messages": [{"role": "assistant", "content": "Partial fix"}]
            }
        )
        mock_execute_post.return_value.raise_for_status = Mock()

        # Mock analysis (first insufficient, then sufficient)
        analyze_call_count = [0]

        def mock_analyze_invoke(_):
            analyze_call_count[0] += 1
            if analyze_call_count[0] == 1:
                # First analysis: insufficient
                return Mock(
                    content='{"is_sufficient": false, "reasoning": "Incomplete", "replan_strategy": "Add more tasks"}'
                )
            else:
                # Second analysis: sufficient
                return Mock(
                    content='{"is_sufficient": true, "reasoning": "Complete", "replan_strategy": null}'
                )

        mock_analyze_llm.create.return_value = Mock(invoke=mock_analyze_invoke)

        # Create graph
        graph = create_router_graph()
        initial_state = create_initial_state(
            "Fix SonarQube violations",
            mode="auto",
            max_replans=2
        )

        # Execute graph
        final_state = graph.invoke(
            initial_state,
            config={"configurable": {"agent_registry": graph.agent_registry}}
        )

        # Assertions
        # Should have triggered replan
        assert plan_call_count[0] == 2  # Original plan + 1 replan
        assert final_state["replan_count"] == 1


# ========== State Management Tests ==========

class TestStateManagement:
    """Tests for state initialization and configuration"""

    def test_create_initial_state(self):
        """Test initial state creation"""
        state = create_initial_state(
            "Test request",
            mode="interactive",
            max_replans=3
        )

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Test request"
        assert state["original_request"] == "Test request"
        assert state["mode"] == "interactive"
        assert state["max_replans"] == 3
        assert state["replan_count"] == 0
        assert state["is_valid"] is False
        assert state["plan"] is None

    def test_state_modes(self):
        """Test different execution modes"""
        auto_state = create_initial_state("Test", mode="auto")
        interactive_state = create_initial_state("Test", mode="interactive")
        review_state = create_initial_state("Test", mode="review")

        assert auto_state["mode"] == "auto"
        assert interactive_state["mode"] == "interactive"
        assert review_state["mode"] == "review"
