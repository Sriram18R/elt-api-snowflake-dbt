"""Unit tests for configuration module."""

import os
import pytest
from ingestion.config import Config, SnowflakeConfig, DuckDBConfig
from ingestion.exceptions import ConfigurationError


class TestSnowflakeConfig:
    """Test Snowflake configuration."""

    def test_valid_config(self):
        """Test valid Snowflake configuration."""
        config = SnowflakeConfig(
            account="test_account",
            user="test_user",
            password="test_password",
            warehouse="test_warehouse",
            database="test_db",
            schema="test_schema",
        )
        assert config.account == "test_account"
        assert config.user == "test_user"

    def test_missing_required_field(self):
        """Test configuration with missing required field."""
        with pytest.raises(ConfigurationError):
            SnowflakeConfig(
                account="",
                user="test_user",
                password="test_password",
                warehouse="test_warehouse",
                database="test_db",
                schema="test_schema",
            )


class TestDuckDBConfig:
    """Test DuckDB configuration."""

    def test_default_path(self):
        """Test default DuckDB path."""
        config = DuckDBConfig()
        assert config.database_path == "data/local_warehouse.duckdb"

    def test_custom_path(self):
        """Test custom DuckDB path."""
        config = DuckDBConfig(database_path="/custom/path.duckdb")
        assert config.database_path == "/custom/path.duckdb"


class TestConfig:
    """Test main configuration class."""

    def test_default_execution_mode(self, monkeypatch):
        """Test default execution mode."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.setenv("API_BASE_URL", "https://api.example.com")
        config = Config()
        assert config.execution_mode == "local"

    def test_invalid_execution_mode(self, monkeypatch):
        """Test invalid execution mode."""
        monkeypatch.setenv("EXECUTION_MODE", "invalid")
        monkeypatch.setenv("API_BASE_URL", "https://api.example.com")
        with pytest.raises(ConfigurationError):
            Config()

    def test_missing_api_url(self, monkeypatch):
        """Test missing API URL."""
        monkeypatch.setenv("EXECUTION_MODE", "local")
        monkeypatch.delenv("API_BASE_URL", raising=False)
        with pytest.raises(ConfigurationError):
            Config()
