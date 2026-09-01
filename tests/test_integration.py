"""Integration tests for the ELT pipeline."""

import pytest
from unittest.mock import Mock, patch
from ingestion.main import ELTPipeline
from ingestion.config import Config


@pytest.fixture
def pipeline():
    """Create ELT pipeline for testing."""
    with patch("ingestion.config.Config.warehouse_config"):
        return ELTPipeline()


class TestELTPipeline:
    """Test complete ELT pipeline."""

    @patch("ingestion.extractor.Extractor.extract")
    @patch("ingestion.loader.Loader.load")
    def test_pipeline_run(self, mock_load, mock_extract, pipeline):
        """Test complete pipeline execution."""
        # Mock extraction
        mock_extract.return_value = [{"id": 1, "name": "test"}]
        mock_load.return_value = 1

        # Run pipeline
        report = pipeline.run(
            endpoint="api/users",
            table_name="users",
            load_mode="append",
        )

        # Verify results
        assert report["status"] == "completed"
        assert report["extracted_records"] == 1
        assert report["loaded_records"] == 1
        mock_extract.assert_called_once()
        mock_load.assert_called_once()
