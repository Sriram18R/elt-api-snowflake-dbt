"""Unit tests for data extractor."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ingestion.extractor import Extractor
from ingestion.config import APIConfig
from ingestion.exceptions import ExtractionError, RetryableError


@pytest.fixture
def api_config():
    """Create API configuration for testing."""
    return APIConfig(
        base_url="https://api.example.com",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def extractor(api_config):
    """Create extractor instance for testing."""
    return Extractor(api_config)


class TestExtractor:
    """Test data extraction."""

    def test_initialization(self, extractor):
        """Test extractor initialization."""
        assert extractor.config.base_url == "https://api.example.com"
        assert extractor.session is not None

    @patch("ingestion.extractor.requests.Session.get")
    def test_extract_success(self, mock_get, extractor):
        """Test successful data extraction."""
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1, "name": "test"}]
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        records = extractor.extract("users")

        assert len(records) == 1
        assert records[0]["id"] == 1
        mock_get.assert_called_once()

    @patch("ingestion.extractor.requests.Session.get")
    def test_extract_timeout(self, mock_get, extractor):
        """Test extraction with timeout."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()
        with pytest.raises(RetryableError):
            extractor.extract("users")

    @patch("ingestion.extractor.requests.Session.get")
    def test_extract_http_error(self, mock_get, extractor):
        """Test extraction with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(ExtractionError):
            extractor.extract("invalid_endpoint")
