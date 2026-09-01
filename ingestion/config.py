"""Configuration management for the ELT pipeline."""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from ingestion.exceptions import ConfigurationError

# Load environment variables from .env file
load_dotenv()


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration."""

    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate Snowflake configuration."""
        required_fields = ["account", "user", "password", "warehouse", "database", "schema"]
        for field_name in required_fields:
            if not getattr(self, field_name):
                raise ConfigurationError(
                    f"Snowflake config missing required field: {field_name}"
                )


@dataclass
class DuckDBConfig:
    """DuckDB configuration."""

    database_path: str = "data/local_warehouse.duckdb"


@dataclass
class APIConfig:
    """API configuration for data extraction."""

    base_url: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    headers: Dict[str, str] = field(default_factory=dict)
    api_key: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate API configuration."""
        if not self.base_url:
            raise ConfigurationError("API base_url is required")


@dataclass
class ValidationConfig:
    """Data validation configuration."""

    strict_mode: bool = True
    allow_null_required_fields: bool = False
    max_validation_errors: int = 100


@dataclass
class TransformationConfig:
    """Data transformation configuration."""

    normalize_case: bool = True
    remove_duplicates: bool = True
    handle_nulls: bool = True


@dataclass
class LoaderConfig:
    """Data loader configuration."""

    batch_size: int = 1000
    upsert_enabled: bool = True
    truncate_before_load: bool = False
    create_tables_if_missing: bool = True


class Config:
    """Main configuration class for the ELT pipeline."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.execution_mode = os.getenv("EXECUTION_MODE", "local").lower()
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.data_dir = os.getenv("DATA_DIR", "data")

        # Initialize mode-specific configs
        if self.execution_mode == "snowflake":
            self.warehouse_config = self._load_snowflake_config()
        else:
            self.warehouse_config = self._load_duckdb_config()

        # Initialize pipeline components
        self.api_config = self._load_api_config()
        self.validation_config = self._load_validation_config()
        self.transformation_config = self._load_transformation_config()
        self.loader_config = self._load_loader_config()

        self._validate_config()

    @staticmethod
    def _load_snowflake_config() -> SnowflakeConfig:
        """Load Snowflake configuration from environment variables."""
        return SnowflakeConfig(
            account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            user=os.getenv("SNOWFLAKE_USER", ""),
            password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", ""),
            database=os.getenv("SNOWFLAKE_DATABASE", ""),
            schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
            role=os.getenv("SNOWFLAKE_ROLE"),
        )

    @staticmethod
    def _load_duckdb_config() -> DuckDBConfig:
        """Load DuckDB configuration from environment variables."""
        return DuckDBConfig(
            database_path=os.getenv("DUCKDB_PATH", "data/local_warehouse.duckdb")
        )

    @staticmethod
    def _load_api_config() -> APIConfig:
        """Load API configuration from environment variables."""
        return APIConfig(
            base_url=os.getenv("API_BASE_URL", ""),
            timeout=int(os.getenv("API_TIMEOUT", "30")),
            max_retries=int(os.getenv("API_MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("API_RETRY_DELAY", "5")),
            api_key=os.getenv("API_KEY"),
        )

    @staticmethod
    def _load_validation_config() -> ValidationConfig:
        """Load validation configuration from environment variables."""
        return ValidationConfig(
            strict_mode=os.getenv("VALIDATION_STRICT_MODE", "true").lower() == "true",
            allow_null_required_fields=os.getenv(
                "VALIDATION_ALLOW_NULL_REQUIRED", "false"
            ).lower()
            == "true",
            max_validation_errors=int(
                os.getenv("VALIDATION_MAX_ERRORS", "100")
            ),
        )

    @staticmethod
    def _load_transformation_config() -> TransformationConfig:
        """Load transformation configuration from environment variables."""
        return TransformationConfig(
            normalize_case=os.getenv("TRANSFORM_NORMALIZE_CASE", "true").lower()
            == "true",
            remove_duplicates=os.getenv(
                "TRANSFORM_REMOVE_DUPLICATES", "true"
            ).lower()
            == "true",
            handle_nulls=os.getenv("TRANSFORM_HANDLE_NULLS", "true").lower()
            == "true",
        )

    @staticmethod
    def _load_loader_config() -> LoaderConfig:
        """Load loader configuration from environment variables."""
        return LoaderConfig(
            batch_size=int(os.getenv("LOADER_BATCH_SIZE", "1000")),
            upsert_enabled=os.getenv("LOADER_UPSERT_ENABLED", "true").lower()
            == "true",
            truncate_before_load=os.getenv(
                "LOADER_TRUNCATE_BEFORE_LOAD", "false"
            ).lower()
            == "true",
            create_tables_if_missing=os.getenv(
                "LOADER_CREATE_TABLES_IF_MISSING", "true"
            ).lower()
            == "true",
        )

    def _validate_config(self) -> None:
        """Validate configuration consistency."""
        if self.execution_mode not in ["local", "snowflake"]:
            raise ConfigurationError(
                f"Invalid EXECUTION_MODE: {self.execution_mode}. "
                "Must be 'local' or 'snowflake'"
            )

        if not self.api_config.base_url:
            raise ConfigurationError("API_BASE_URL environment variable is required")

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "execution_mode": self.execution_mode,
            "log_level": self.log_level,
            "data_dir": self.data_dir,
            "warehouse_config": self.warehouse_config,
            "api_config": self.api_config,
            "validation_config": self.validation_config,
            "transformation_config": self.transformation_config,
            "loader_config": self.loader_config,
        }

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(mode={self.execution_mode}, log_level={self.log_level})"
