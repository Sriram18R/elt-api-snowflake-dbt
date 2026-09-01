"""Data validation for the ELT pipeline."""

from typing import Any, Dict, List, Optional, Set

from ingestion.config import ValidationConfig
from ingestion.exceptions import DataQualityError, ValidationError
from ingestion.logger import get_logger

logger = get_logger(__name__)


class Validator:
    """Validate data quality and schema compliance."""

    def __init__(self, config: ValidationConfig) -> None:
        """Initialize validator with configuration.

        Args:
            config: Validation configuration
        """
        self.config = config
        self.validation_errors: List[str] = []
        logger.info(f"Validator initialized (strict_mode={config.strict_mode})")

    def validate_records(
        self,
        records: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Validate list of records against schema.

        Args:
            records: List of records to validate
            schema: Optional schema definition

        Returns:
            List of valid records

        Raises:
            ValidationError: If validation fails in strict mode
        """
        self.validation_errors = []
        valid_records: List[Dict[str, Any]] = []

        logger.info(f"Validating {len(records)} records")

        for idx, record in enumerate(records):
            try:
                if self._validate_record(record, schema):
                    valid_records.append(record)
            except ValidationError as e:
                error_msg = f"Record {idx}: {str(e)}"
                self.validation_errors.append(error_msg)
                logger.warning(error_msg)

                if len(self.validation_errors) >= self.config.max_validation_errors:
                    break

        # Check if we should raise error
        if self.validation_errors:
            error_summary = (
                f"Validation failed: {len(self.validation_errors)} errors found"
            )
            logger.error(error_summary)

            if self.config.strict_mode:
                raise ValidationError(
                    f"{error_summary}\nFirst 5 errors: "
                    f"{self.validation_errors[:5]}"
                )

        logger.info(f"Validation complete: {len(valid_records)}/{len(records)} valid")
        return valid_records

    def _validate_record(
        self, record: Dict[str, Any], schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Validate a single record.

        Args:
            record: Record to validate
            schema: Optional schema definition

        Returns:
            True if record is valid

        Raises:
            ValidationError: If record is invalid
        """
        if not isinstance(record, dict):
            raise ValidationError(f"Expected dict, got {type(record).__name__}")

        if schema:
            return self._validate_against_schema(record, schema)

        return True

    def _validate_against_schema(
        self, record: Dict[str, Any], schema: Dict[str, Any]
    ) -> bool:
        """Validate record against schema definition.

        Args:
            record: Record to validate
            schema: Schema definition

        Returns:
            True if record conforms to schema

        Raises:
            ValidationError: If record violates schema
        """
        required_fields: Set[str] = set(schema.get("required_fields", []))
        field_types: Dict[str, type] = schema.get("field_types", {})

        # Check required fields
        for field in required_fields:
            if field not in record:
                if not self.config.allow_null_required_fields:
                    raise ValidationError(f"Missing required field: {field}")
            elif record[field] is None:
                if not self.config.allow_null_required_fields:
                    raise ValidationError(f"Required field '{field}' is null")

        # Check field types
        for field, expected_type in field_types.items():
            if field in record and record[field] is not None:
                if not isinstance(record[field], expected_type):
                    raise ValidationError(
                        f"Field '{field}': expected {expected_type.__name__}, "
                        f"got {type(record[field]).__name__}"
                    )

        return True

    def check_duplicates(
        self, records: List[Dict[str, Any]], key_fields: List[str]
    ) -> Dict[str, Any]:
        """Check for duplicate records based on key fields.

        Args:
            records: List of records to check
            key_fields: Fields to use as composite key

        Returns:
            Dictionary with duplicate analysis
        """
        logger.info(f"Checking duplicates using key fields: {key_fields}")

        seen_keys: Set[tuple] = set()
        duplicates: List[Dict[str, Any]] = []

        for record in records:
            key_values = tuple(record.get(field) for field in key_fields)

            if key_values in seen_keys:
                duplicates.append(record)
            else:
                seen_keys.add(key_values)

        logger.info(f"Found {len(duplicates)} duplicate records")

        return {
            "total_records": len(records),
            "unique_records": len(seen_keys),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
        }

    def check_data_quality(
        self,
        records: List[Dict[str, Any]],
        quality_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run data quality checks on records.

        Args:
            records: List of records to check
            quality_rules: Optional custom quality rules

        Returns:
            Dictionary with quality metrics

        Raises:
            DataQualityError: If quality checks fail
        """
        logger.info(f"Running data quality checks on {len(records)} records")

        quality_report = {
            "total_records": len(records),
            "null_count": 0,
            "null_by_field": {},
            "missing_values": [],
            "quality_score": 0.0,
        }

        if not records:
            return quality_report

        # Count nulls
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())

        for field in all_fields:
            null_count = sum(1 for r in records if r.get(field) is None)
            quality_report["null_by_field"][field] = null_count

            if null_count == len(records):
                quality_report["missing_values"].append(field)

        total_nulls = sum(quality_report["null_by_field"].values())
        total_cells = len(records) * len(all_fields)
        quality_report["null_count"] = total_nulls
        quality_report["quality_score"] = (
            (total_cells - total_nulls) / total_cells * 100 if total_cells > 0 else 0
        )

        logger.info(
            f"Data quality score: {quality_report['quality_score']:.2f}% "
            f"(nulls: {total_nulls}/{total_cells})"
        )

        if quality_report["quality_score"] < 50:
            raise DataQualityError(
                f"Data quality score too low: {quality_report['quality_score']:.2f}%"
            )

        return quality_report

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors.

        Returns:
            List of validation error messages
        """
        return self.validation_errors
