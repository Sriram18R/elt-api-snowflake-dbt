"""Main ELT pipeline orchestration."""

from typing import Any, Dict, List, Optional

from ingestion.config import Config
from ingestion.extractor import Extractor
from ingestion.loader import Loader
from ingestion.transformer import Transformer
from ingestion.validator import Validator
from ingestion.exceptions import ELTException
from ingestion.logger import get_logger

logger = get_logger(__name__)


class ELTPipeline:
    """Orchestrate the complete ELT pipeline."""

    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize ELT pipeline.

        Args:
            config: Pipeline configuration (creates new if None)
        """
        self.config = config or Config()
        self.extractor = Extractor(self.config.api_config)
        self.transformer = Transformer(self.config.transformation_config)
        self.validator = Validator(self.config.validation_config)
        self.loader = Loader(
            self.config.warehouse_config,
            self.config.loader_config,
            self.config.execution_mode,
        )

        logger.info(
            f"ELT Pipeline initialized "
            f"(mode={self.config.execution_mode}, log_level={self.config.log_level})"
        )

    def run(
        self,
        endpoint: str,
        table_name: str,
        schema: Optional[Dict[str, Any]] = None,
        transformations: Optional[List[Dict[str, Any]]] = None,
        load_mode: str = "append",
    ) -> Dict[str, Any]:
        """Run complete ELT pipeline.

        Args:
            endpoint: API endpoint to extract from
            table_name: Target table name
            schema: Optional data schema for validation
            transformations: Optional transformation rules
            load_mode: Load mode ('append' or 'replace')

        Returns:
            Pipeline execution report

        Raises:
            ELTException: If any stage fails
        """
        report = {
            "endpoint": endpoint,
            "table_name": table_name,
            "extracted_records": 0,
            "transformed_records": 0,
            "validated_records": 0,
            "loaded_records": 0,
            "status": "started",
        }

        try:
            logger.info(f"Starting ELT pipeline for {endpoint} -> {table_name}")

            # Extract
            logger.info(f"EXTRACT: Fetching data from {endpoint}")
            records = self.extractor.extract(endpoint)
            report["extracted_records"] = len(records)
            logger.info(f"EXTRACT: Retrieved {len(records)} records")

            # Transform
            logger.info(f"TRANSFORM: Transforming {len(records)} records")
            records = self.transformer.transform(records, transformations)
            report["transformed_records"] = len(records)
            logger.info(f"TRANSFORM: Transformed to {len(records)} records")

            # Validate
            logger.info(f"VALIDATE: Validating {len(records)} records")
            records = self.validator.validate_records(records, schema)
            report["validated_records"] = len(records)
            logger.info(f"VALIDATE: Validated {len(records)} records")

            # Load
            logger.info(f"LOAD: Loading {len(records)} records into {table_name}")
            loaded_count = self.loader.load(table_name, records, load_mode)
            report["loaded_records"] = loaded_count
            logger.info(f"LOAD: Successfully loaded {loaded_count} records")

            report["status"] = "completed"
            logger.info(f"ELT pipeline completed successfully for {endpoint}")

        except Exception as e:
            report["status"] = "failed"
            report["error"] = str(e)
            logger.error(f"ELT pipeline failed: {str(e)}", exc_info=True)
            raise

        return report

    def extract_paginated(
        self,
        endpoint: str,
        table_name: str,
        page_param: str = "page",
        limit_param: str = "limit",
        page_size: int = 100,
        max_pages: Optional[int] = None,
        schema: Optional[Dict[str, Any]] = None,
        transformations: Optional[List[Dict[str, Any]]] = None,
        load_mode: str = "append",
    ) -> Dict[str, Any]:
        """Run ELT pipeline with paginated extraction.

        Args:
            endpoint: API endpoint to extract from
            table_name: Target table name
            page_param: Page parameter name
            limit_param: Limit parameter name
            page_size: Records per page
            max_pages: Maximum pages to extract
            schema: Optional data schema
            transformations: Optional transformation rules
            load_mode: Load mode

        Returns:
            Pipeline execution report
        """
        report = {
            "endpoint": endpoint,
            "table_name": table_name,
            "extracted_records": 0,
            "transformed_records": 0,
            "validated_records": 0,
            "loaded_records": 0,
            "status": "started",
        }

        try:
            logger.info(
                f"Starting paginated ELT pipeline for {endpoint} -> {table_name}"
            )

            # Extract paginated
            logger.info(f"EXTRACT: Fetching paginated data from {endpoint}")
            records = self.extractor.extract_paginated(
                endpoint,
                page_param=page_param,
                limit_param=limit_param,
                page_size=page_size,
                max_pages=max_pages,
            )
            report["extracted_records"] = len(records)
            logger.info(f"EXTRACT: Retrieved {len(records)} records")

            # Transform
            logger.info(f"TRANSFORM: Transforming {len(records)} records")
            records = self.transformer.transform(records, transformations)
            report["transformed_records"] = len(records)
            logger.info(f"TRANSFORM: Transformed to {len(records)} records")

            # Validate
            logger.info(f"VALIDATE: Validating {len(records)} records")
            records = self.validator.validate_records(records, schema)
            report["validated_records"] = len(records)
            logger.info(f"VALIDATE: Validated {len(records)} records")

            # Load
            logger.info(f"LOAD: Loading {len(records)} records into {table_name}")
            loaded_count = self.loader.load(table_name, records, load_mode)
            report["loaded_records"] = loaded_count
            logger.info(f"LOAD: Successfully loaded {loaded_count} records")

            report["status"] = "completed"
            logger.info(f"Paginated ELT pipeline completed for {endpoint}")

        except Exception as e:
            report["status"] = "failed"
            report["error"] = str(e)
            logger.error(f"Paginated ELT pipeline failed: {str(e)}", exc_info=True)
            raise

        return report

    def close(self) -> None:
        """Close all connections."""
        self.extractor.close()
        self.loader.close()
        logger.info("ELT Pipeline closed")

    def __enter__(self) -> "ELTPipeline":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def main() -> None:
    """Example usage of ELT pipeline."""
    try:
        with ELTPipeline() as pipeline:
            # Example: Extract, transform, and load data
            report = pipeline.run(
                endpoint="api/users",
                table_name="users",
                load_mode="append",
            )
            print(f"Pipeline Report: {report}")

    except ELTException as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
