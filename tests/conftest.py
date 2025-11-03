"""
Pytest Configuration and Shared Fixtures

Provides common fixtures and configuration for all tests.
"""

import pytest
import os
from unittest.mock import Mock

# Set test environment variables
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["LANGGRAPH_SERVER_URL"] = "http://localhost:2024"


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    monkeypatch.setenv("LANGGRAPH_SERVER_URL", "http://localhost:2024")
