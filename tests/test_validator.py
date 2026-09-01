"""Unit tests for data validator."""

import pytest
from ingestion.validator import Validator
from ingestion.config import ValidationConfig
from ingestion.exceptions import ValidationError, DataQualityError


@pytest.fixture
def validator():
    """Create validator instance for testing."""
    config = ValidationConfig(strict_mode=True)
    return Validator(config)


class TestValidator:
    """Test data validation."""

    def test_validate_valid_records(self, validator):
        """Test validation of valid records."""
        records = [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]
        result = validator.validate_records(records)
        assert len(result) == 2

    def test_validate_schema_required_fields(self, validator):
        """Test schema validation with required fields."""
        schema = {"required_fields": ["id", "name"], "field_types": {}}
        records = [{"id": 1, "name": "test"}, {"id": 2}]

        with pytest.raises(ValidationError):
            validator.validate_records(records, schema)

    def test_check_duplicates(self, validator):
        """Test duplicate detection."""
        records = [{"id": 1, "email": "test@example.com"}, {"id": 1, "email": "test@example.com"}, {"id": 2, "email": "test2@example.com"}]
        result = validator.check_duplicates(records, ["id"])

        assert result["total_records"] == 3
        assert result["unique_records"] == 2
        assert result["duplicate_count"] == 1

    def test_check_data_quality(self, validator):
        """Test data quality checks."""
        records = [{"id": 1, "name": "test", "email": None}, {"id": 2, "name": "test2", "email": "test@example.com"}]
        result = validator.check_data_quality(records)

        assert result["total_records"] == 2
        assert result["null_count"] == 1
        assert "email" in result["null_by_field"]
