"""Conftest for pytest configuration."""

import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables for testing."""
    os.environ["EXECUTION_MODE"] = "local"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["API_BASE_URL"] = "https://api.example.com"
    os.environ["DUCKDB_PATH"] = ":memory:"
    yield
    # Cleanup after test
    for key in ["EXECUTION_MODE", "LOG_LEVEL", "API_BASE_URL", "DUCKDB_PATH"]:
        os.environ.pop(key, None)
