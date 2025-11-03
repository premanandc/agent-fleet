"""
Unit Tests for Router Agent Nodes

Tests individual nodes in isolation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

from src.models.router_state import RouterState, Task, Plan, AgentCapability
from src.nodes import (
    validate_request,
    reject_request,
    generate_plan,
    execute_tasks,
    analyze_results,
    aggregate_results
)


# ========== Fixtures ==========

@pytest.fixture
def base_state():
    """Base state for testing"""
    return {
        "messages": [HumanMessage(content="Fix the SonarQube issues in my code")],
        "request_id": "test-123",
        "original_request": "Fix the SonarQube issues in my code",
        "is_valid": False,
        "rejection_reason": None,
        "plan": None,
        "plan_approved": False,
        "current_task_index": 0,
        "need_replan": False,
        "replan_reason": None,
        "task_results": [],
        "final_response": None,
        "mode": "auto",
        "max_replans": 2,
        "replan_count": 0,
        "status_events": []
    }


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = Mock()
    return llm


@pytest.fixture
def sample_agent_registry():
    """Sample agent registry for testing"""
    return {
        "coda-agent": AgentCapability(
            agent_id="coda-agent",
            name="Coda",
            capabilities=["code-quality", "sonarqube"],
            skills=["Fix SonarQube violations", "Analyze code quality"],
            description="Specialized agent for SonarQube code quality remediation"
        ),
        "askcody-agent": AgentCapability(
            agent_id="askcody-agent",
            name="AskCody",
            capabilities=["ci-cd", "jenkins"],
            skills=["Diagnose build failures", "Fix CI/CD issues"],
            description="Specialized agent for CI/CD diagnostics"
        )
    }


@pytest.fixture
def sample_plan():
    """Sample execution plan for testing"""
    return Plan(
        tasks=[
            Task(
                id="task-1",
                description="Analyze SonarQube violations",
                agent_id="coda-agent",
                agent_name="Coda",
                status="pending",
                result=None,
                error=None,
                dependencies=[],
                rationale="Coda specializes in SonarQube analysis"
            ),
            Task(
                id="task-2",
                description="Generate fix recommendations",
                agent_id="coda-agent",
                agent_name="Coda",
                status="pending",
                result=None,
                error=None,
                dependencies=["task-1"],
                rationale="Follow-up task based on analysis"
            )
        ],
        execution_strategy="sequential",
        created_at=datetime.now(),
        analysis="User needs SonarQube violation remediation"
    )


# ========== Validate Request Node Tests ==========

class TestValidateRequest:
    """Tests for validate_request node"""

    @patch("src.nodes.validate.LLMFactory")
    def test_valid_request(self, mock_factory, base_state, mock_llm):
        """Test validation of on-topic request"""
        # Setup mock LLM response
        mock_llm.invoke.return_value = Mock(
            content='{"is_valid": true, "reasoning": "Request is about code quality"}'
        )
        mock_factory.create.return_value = mock_llm

        # Execute node
        result = validate_request(base_state)

        # Assertions
        assert result["is_valid"] is True
        assert result["rejection_reason"] is None
        assert result["original_request"] == "Fix the SonarQube issues in my code"

    @patch("src.nodes.validate.LLMFactory")
    def test_invalid_request(self, mock_factory, base_state, mock_llm):
        """Test validation of off-topic request"""
        # Update state with off-topic request
        base_state["messages"] = [HumanMessage(content="What's the weather today?")]

        # Setup mock LLM response
        mock_llm.invoke.return_value = Mock(
            content='{"is_valid": false, "reasoning": "Weather is not related to ITEP"}'
        )
        mock_factory.create.return_value = mock_llm

        # Execute node
        result = validate_request(base_state)

        # Assertions
        assert result["is_valid"] is False
        assert "Off-topic request" in result["rejection_reason"]

    def test_no_message(self, base_state):
        """Test validation with no user message"""
        base_state["messages"] = []

        result = validate_request(base_state)

        assert result["is_valid"] is False
        assert "No user message" in result["rejection_reason"]


# ========== Reject Request Node Tests ==========

class TestRejectRequest:
    """Tests for reject_request node"""

    def test_rejection_message(self, base_state):
        """Test rejection message formatting"""
        base_state["rejection_reason"] = "Off-topic request: Weather is not supported"

        result = reject_request(base_state)

        assert "final_response" in result
        assert "ITEP" in result["final_response"]
        assert "Weather is not supported" in result["final_response"]
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)


# ========== Generate Plan Node Tests ==========

class TestGeneratePlan:
    """Tests for generate_plan node"""

    @patch("src.nodes.plan.LLMFactory")
    def test_plan_generation(self, mock_factory, base_state, mock_llm, sample_agent_registry):
        """Test successful plan generation"""
        # Setup mock LLM response
        mock_response = {
            "analysis": "User needs SonarQube help",
            "execution_strategy": "sequential",
            "tasks": [
                {
                    "description": "Fix SonarQube violations",
                    "agent_id": "coda-agent",
                    "agent_name": "Coda",
                    "dependencies": [],
                    "rationale": "Coda specializes in SonarQube"
                }
            ]
        }
        mock_llm.invoke.return_value = Mock(content=str(mock_response).replace("'", '"'))
        mock_factory.create.return_value = mock_llm

        # Create config with agent registry
        config = {"configurable": {"agent_registry": sample_agent_registry}}

        # Execute node
        result = generate_plan(base_state, config)

        # Assertions
        assert "plan" in result
        assert result["plan"] is not None
        assert len(result["plan"]["tasks"]) == 1
        assert result["plan"]["execution_strategy"] == "sequential"
        assert result["need_replan"] is False

    def test_plan_no_agents(self, base_state):
        """Test plan generation with no available agents"""
        config = {"configurable": {"agent_registry": {}}}

        result = generate_plan(base_state, config)

        assert "plan" in result
        assert len(result["plan"]["tasks"]) == 0
        assert "No agents available" in result["plan"]["analysis"]


# ========== Execute Tasks Node Tests ==========

class TestExecuteTasks:
    """Tests for execute_tasks node"""

    @patch("src.nodes.execute.requests.post")
    def test_sequential_execution(self, mock_post, base_state, sample_plan):
        """Test sequential task execution"""
        # Setup state with plan
        base_state["plan"] = sample_plan

        # Mock A2A responses
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "messages": [
                    {"role": "assistant", "content": "Analysis complete: 5 violations found"}
                ]
            }
        )
        mock_post.return_value.raise_for_status = Mock()

        # Create config
        config = {"configurable": {}}

        # Execute node
        result = execute_tasks(base_state, config)

        # Assertions
        assert "task_results" in result
        # Should execute first task only (second has dependency)
        assert len(result["task_results"]) >= 1

    @patch("src.nodes.execute.requests.post")
    def test_failed_task(self, mock_post, base_state, sample_plan):
        """Test handling of failed task"""
        base_state["plan"] = sample_plan

        # Mock failed A2A response
        mock_post.side_effect = Exception("Agent unreachable")

        config = {"configurable": {}}

        result = execute_tasks(base_state, config)

        # Should have results with failures
        assert "task_results" in result


# ========== Analyze Results Node Tests ==========

class TestAnalyzeResults:
    """Tests for analyze_results node"""

    @patch("src.nodes.analyze.LLMFactory")
    def test_sufficient_results(self, mock_factory, base_state, mock_llm):
        """Test analysis with sufficient results"""
        # Setup state with completed tasks
        base_state["task_results"] = [
            Task(
                id="task-1",
                description="Fix violations",
                agent_id="coda-agent",
                agent_name="Coda",
                status="completed",
                result="Fixed 5 violations successfully",
                error=None,
                dependencies=[],
                rationale="Test"
            )
        ]

        # Mock LLM response
        mock_llm.invoke.return_value = Mock(
            content='{"is_sufficient": true, "reasoning": "All violations fixed", "replan_strategy": null}'
        )
        mock_factory.create.return_value = mock_llm

        result = analyze_results(base_state)

        assert result["need_replan"] is False

    @patch("src.nodes.analyze.LLMFactory")
    def test_insufficient_results(self, mock_factory, base_state, mock_llm):
        """Test analysis with insufficient results"""
        base_state["task_results"] = [
            Task(
                id="task-1",
                description="Analyze violations",
                agent_id="coda-agent",
                agent_name="Coda",
                status="completed",
                result="Found violations but didn't fix them",
                error=None,
                dependencies=[],
                rationale="Test"
            )
        ]

        # Mock LLM response indicating need for replan
        mock_llm.invoke.return_value = Mock(
            content='{"is_sufficient": false, "reasoning": "Violations not fixed", "replan_strategy": "Add task to fix violations"}'
        )
        mock_factory.create.return_value = mock_llm

        result = analyze_results(base_state)

        assert result["need_replan"] is True
        assert "replan_reason" in result

    def test_max_replans_reached(self, base_state):
        """Test that replanning stops at max_replans"""
        base_state["replan_count"] = 2
        base_state["max_replans"] = 2

        result = analyze_results(base_state)

        assert result["need_replan"] is False


# ========== Aggregate Results Node Tests ==========

class TestAggregateResults:
    """Tests for aggregate_results node"""

    @patch("src.nodes.aggregate.LLMFactory")
    def test_successful_aggregation(self, mock_factory, base_state, mock_llm):
        """Test successful result aggregation"""
        base_state["task_results"] = [
            Task(
                id="task-1",
                description="Fix violations",
                agent_id="coda-agent",
                agent_name="Coda",
                status="completed",
                result="Fixed 5 violations",
                error=None,
                dependencies=[],
                rationale="Test"
            )
        ]

        # Mock LLM response
        mock_llm.invoke.return_value = Mock(
            content="# SonarQube Violations Fixed\n\nSuccessfully fixed 5 violations in your code."
        )
        mock_factory.create.return_value = mock_llm

        result = aggregate_results(base_state)

        assert "final_response" in result
        assert "SonarQube" in result["final_response"]
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

    @patch("src.nodes.aggregate.LLMFactory")
    def test_aggregation_with_failures(self, mock_factory, base_state, mock_llm):
        """Test aggregation with some failed tasks"""
        base_state["task_results"] = [
            Task(
                id="task-1",
                description="Fix violations",
                agent_id="coda-agent",
                agent_name="Coda",
                status="completed",
                result="Fixed some violations",
                error=None,
                dependencies=[],
                rationale="Test"
            ),
            Task(
                id="task-2",
                description="Deploy fixes",
                agent_id="other-agent",
                agent_name="Other",
                status="failed",
                result=None,
                error="Agent unavailable",
                dependencies=["task-1"],
                rationale="Test"
            )
        ]

        mock_llm.invoke.return_value = Mock(
            content="Fixed violations but deployment failed"
        )
        mock_factory.create.return_value = mock_llm

        result = aggregate_results(base_state)

        assert "final_response" in result
        # Should include failure note
        assert "errors" in result["final_response"].lower() or "note" in result["final_response"].lower()
