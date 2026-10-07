"""Data transformation utilities for the ELT pipeline."""

from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, List, Optional

from ingestion.config import TransformationConfig
from ingestion.exceptions import TransformationError
from ingestion.logger import get_logger

logger = get_logger(__name__)


class Transformer:
    """Normalize, clean, and transform extracted records before loading."""

    def __init__(self, config: TransformationConfig) -> None:
        self.config = config
        logger.info(
            "Transformer initialized (normalize_case=%s, remove_duplicates=%s, handle_nulls=%s)",
            self.config.normalize_case,
            self.config.remove_duplicates,
            self.config.handle_nulls,
        )

    def transform(
        self,
        records: List[Dict[str, Any]],
        transformations: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Apply configured transformations to a list of records."""
        work_records = copy.deepcopy(records)

        if not work_records:
            return []

        if self.config.normalize_case:
            work_records = self._normalize_case(work_records)

        if self.config.handle_nulls:
            work_records = self._handle_nulls(work_records)

        if self.config.remove_duplicates:
            work_records = self._remove_duplicates(work_records)

        if transformations:
            for transformation in transformations:
                work_records = self._apply_transformation(work_records, transformation)

        return work_records

    def _normalize_case(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize dictionary keys to lowercase."""
        normalized: List[Dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                raise TransformationError(f"Expected dict record, got {type(record).__name__}")
            normalized.append({str(key).lower(): value for key, value in record.items()})
        return normalized

    def _handle_nulls(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replace null values with empty strings."""
        handled: List[Dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                raise TransformationError(f"Expected dict record, got {type(record).__name__}")
            handled.append({key: "" if value is None else value for key, value in record.items()})
        return handled

    def _remove_duplicates(
        self,
        records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Remove duplicate records while preserving insertion order."""
        unique: List[Dict[str, Any]] = []
        seen: set[tuple[tuple[str, Any], ...]] = set()

        for record in records:
            if not isinstance(record, dict):
                raise TransformationError(f"Expected dict record, got {type(record).__name__}")
            key = tuple(sorted(record.items()))
            if key in seen:
                continue
            seen.add(key)
            unique.append(record)

        return unique

    @staticmethod
    def _rename_field(
        records: List[Dict[str, Any]],
        source_field: str,
        target_field: str,
    ) -> List[Dict[str, Any]]:
        """Rename a field in every record."""
        renamed: List[Dict[str, Any]] = []
        for record in records:
            updated = dict(record)
            if source_field in updated:
                updated[target_field] = updated.pop(source_field)
            renamed.append(updated)
        return renamed

    @staticmethod
    def _concatenate_fields(
        records: List[Dict[str, Any]],
        fields: Iterable[str],
        target_field: str,
    ) -> List[Dict[str, Any]]:
        """Concatenate multiple fields into a single value."""
        concatenated: List[Dict[str, Any]] = []
        for record in records:
            updated = dict(record)
            values = []
            for field in fields:
                value = record.get(field)
                if value is None:
                    value = ""
                values.append(str(value))
            updated[target_field] = " ".join(part for part in values if part)
            concatenated.append(updated)
        return concatenated

    def _apply_transformation(
        self,
        records: List[Dict[str, Any]],
        transformation: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Apply one named transformation rule."""
        transformation_type = transformation.get("type")

        if transformation_type == "rename":
            return self._rename_field(
                records,
                transformation.get("from"),
                transformation.get("to"),
            )

        if transformation_type == "concatenate":
            return self._concatenate_fields(
                records,
                transformation.get("fields", []),
                transformation.get("new_field") or transformation.get("to"),
            )

        if transformation_type == "map":
            field_name = transformation.get("field")
            mapping = transformation.get("mapping", {})
            mapped: List[Dict[str, Any]] = []
            for record in records:
                updated = dict(record)
                if field_name in updated and updated[field_name] in mapping:
                    updated[field_name] = mapping[updated[field_name]]
                mapped.append(updated)
            return mapped

        if transformation_type == "extract":
            field_name = transformation.get("field")
            pattern = transformation.get("pattern")
            extracted: List[Dict[str, Any]] = []
            for record in records:
                updated = dict(record)
                if field_name in updated and isinstance(updated[field_name], str) and pattern:
                    import re

                    match = re.search(pattern, updated[field_name])
                    if match:
                        updated[field_name] = match.group(0)
                extracted.append(updated)
            return extracted

        raise TransformationError(f"Unsupported transformation type: {transformation_type}")


__all__ = ["Transformer"]
