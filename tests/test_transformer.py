"""Unit tests for data transformer."""

import pytest
from ingestion.transformer import Transformer
from ingestion.config import TransformationConfig


@pytest.fixture
def transformer():
    """Create transformer instance for testing."""
    config = TransformationConfig(
        normalize_case=True,
        remove_duplicates=True,
        handle_nulls=True,
    )
    return Transformer(config)


class TestTransformer:
    """Test data transformation."""

    def test_normalize_case(self, transformer):
        """Test field name normalization."""
        records = [{"UserId": 1, "UserName": "test"}, {"UserId": 2, "UserName": "test2"}]
        result = transformer._normalize_case(records)

        assert "userid" in result[0]
        assert "username" in result[0]
        assert "UserId" not in result[0]

    def test_handle_nulls(self, transformer):
        """Test null value handling."""
        records = [{"id": 1, "name": None}, {"id": 2, "name": "test"}]
        result = transformer._handle_nulls(records)

        assert result[0]["name"] == ""
        assert result[1]["name"] == "test"

    def test_remove_duplicates(self, transformer):
        """Test duplicate removal."""
        records = [{"id": 1, "name": "test"}, {"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]
        result = transformer._remove_duplicates(records)

        assert len(result) == 2

    def test_rename_field(self, transformer):
        """Test field renaming."""
        records = [{"old_name": "value1"}, {"old_name": "value2"}]
        result = Transformer._rename_field(records, "old_name", "new_name")

        assert "new_name" in result[0]
        assert "old_name" not in result[0]

    def test_concatenate_fields(self, transformer):
        """Test field concatenation."""
        records = [{"first_name": "John", "last_name": "Doe"}, {"first_name": "Jane", "last_name": "Smith"}]
        result = Transformer._concatenate_fields(records, ["first_name", "last_name"], "full_name")

        assert result[0]["full_name"] == "John Doe"
        assert result[1]["full_name"] == "Jane Smith"
