"""Data loading to data warehouse."""

from typing import Any, Dict, List, Optional

import duckdb
import snowflake.connector

from ingestion.config import LoaderConfig, SnowflakeConfig, DuckDBConfig
from ingestion.exceptions import LoadingError, ConnectionError as PipelineConnectionError
from ingestion.logger import get_logger

logger = get_logger(__name__)


class DuckDBLoader:
    """Load data into DuckDB."""

    def __init__(self, config: DuckDBConfig) -> None:
        """Initialize DuckDB loader.

        Args:
            config: DuckDB configuration
        """
        self.config = config
        self.connection = self._connect()
        logger.info(f"DuckDBLoader initialized with database: {config.database_path}")

    def _connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to DuckDB.

        Returns:
            DuckDB connection

        Raises:
            PipelineConnectionError: If connection fails
        """
        try:
            conn = duckdb.connect(self.config.database_path)
            logger.info(f"Connected to DuckDB: {self.config.database_path}")
            return conn
        except Exception as e:
            msg = f"Failed to connect to DuckDB: {str(e)}"
            logger.error(msg)
            raise PipelineConnectionError(msg) from e

    def load(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        mode: str = "append",
    ) -> int:
        """Load data into DuckDB table.

        Args:
            table_name: Target table name
            records: Records to load
            mode: Load mode - 'append', 'replace', or 'upsert'

        Returns:
            Number of rows loaded

        Raises:
            LoadingError: If loading fails
        """
        if not records:
            logger.warning(f"No records to load into {table_name}")
            return 0

        try:
            if mode == "replace":
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"Dropped existing table: {table_name}")

            # Convert records to DuckDB table format
            self.connection.register("temp_table", records)
            self.connection.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_table")

            row_count = self.connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            logger.info(f"Loaded {row_count} rows into {table_name}")
            return row_count

        except Exception as e:
            msg = f"Failed to load data into {table_name}: {str(e)}"
            logger.error(msg)
            raise LoadingError(msg) from e

    def close(self) -> None:
        """Close DuckDB connection."""
        if self.connection:
            self.connection.close()
            logger.info("DuckDB connection closed")


class SnowflakeLoader:
    """Load data into Snowflake."""

    def __init__(self, config: SnowflakeConfig, loader_config: LoaderConfig) -> None:
        """Initialize Snowflake loader.

        Args:
            config: Snowflake configuration
            loader_config: Loader configuration
        """
        self.config = config
        self.loader_config = loader_config
        self.connection = self._connect()
        logger.info(f"SnowflakeLoader initialized for {config.database}.{config.schema}")

    def _connect(self) -> snowflake.connector.SnowflakeConnection:
        """Connect to Snowflake.

        Returns:
            Snowflake connection

        Raises:
            PipelineConnectionError: If connection fails
        """
        try:
            conn = snowflake.connector.connect(
                account=self.config.account,
                user=self.config.user,
                password=self.config.password,
                warehouse=self.config.warehouse,
                database=self.config.database,
                schema=self.config.schema,
                role=self.config.role,
            )
            logger.info(
                f"Connected to Snowflake: {self.config.account}/"
                f"{self.config.database}.{self.config.schema}"
            )
            return conn
        except Exception as e:
            msg = f"Failed to connect to Snowflake: {str(e)}"
            logger.error(msg)
            raise PipelineConnectionError(msg) from e

    def load(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        mode: str = "append",
    ) -> int:
        """Load data into Snowflake table.

        Args:
            table_name: Target table name
            records: Records to load
            mode: Load mode - 'append' or 'replace'

        Returns:
            Number of rows loaded

        Raises:
            LoadingError: If loading fails
        """
        if not records:
            logger.warning(f"No records to load into {table_name}")
            return 0

        try:
            cursor = self.connection.cursor()

            # Create table if missing
            if self.loader_config.create_tables_if_missing:
                self._create_table_if_missing(cursor, table_name, records[0])

            # Truncate if specified
            if mode == "replace" and self.loader_config.truncate_before_load:
                cursor.execute(f"TRUNCATE TABLE {table_name}")
                logger.info(f"Truncated table: {table_name}")

            # Load in batches
            batch_size = self.loader_config.batch_size
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                self._insert_batch(cursor, table_name, batch)

            row_count = len(records)
            logger.info(f"Loaded {row_count} rows into {table_name}")

            cursor.close()
            return row_count

        except Exception as e:
            msg = f"Failed to load data into {table_name}: {str(e)}"
            logger.error(msg)
            raise LoadingError(msg) from e

    def _create_table_if_missing(
        self, cursor: Any, table_name: str, sample_record: Dict[str, Any]
    ) -> None:
        """Create table if it doesn't exist.

        Args:
            cursor: Database cursor
            table_name: Table name
            sample_record: Sample record to infer schema
        """
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if cursor.fetchone() is None:
            # Build CREATE TABLE statement from sample record
            columns = []
            for key in sample_record.keys():
                columns.append(f"{key} VARCHAR")

            create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
            cursor.execute(create_sql)
            logger.info(f"Created table: {table_name}")

    def _insert_batch(
        self, cursor: Any, table_name: str, batch: List[Dict[str, Any]]
    ) -> None:
        """Insert batch of records.

        Args:
            cursor: Database cursor
            table_name: Table name
            batch: Records to insert
        """
        if not batch:
            return

        keys = batch[0].keys()
        placeholders = ", ".join(["?" for _ in keys])
        insert_sql = (
            f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"
        )

        for record in batch:
            values = [record.get(key) for key in keys]
            cursor.execute(insert_sql, values)

    def close(self) -> None:
        """Close Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Snowflake connection closed")


class Loader:
    """Universal loader for both DuckDB and Snowflake."""

    def __init__(
        self,
        warehouse_config: Any,
        loader_config: LoaderConfig,
        mode: str = "duckdb",
    ) -> None:
        """Initialize loader.

        Args:
            warehouse_config: Warehouse configuration
            loader_config: Loader configuration
            mode: 'duckdb' or 'snowflake'
        """
        self.mode = mode
        self.loader_config = loader_config

        if mode == "snowflake":
            self.backend = SnowflakeLoader(warehouse_config, loader_config)
        else:
            self.backend = DuckDBLoader(warehouse_config)

        logger.info(f"Loader initialized in {mode} mode")

    def load(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        mode: str = "append",
    ) -> int:
        """Load data into warehouse.

        Args:
            table_name: Target table name
            records: Records to load
            mode: Load mode

        Returns:
            Number of rows loaded
        """
        return self.backend.load(table_name, records, mode)

    def close(self) -> None:
        """Close database connection."""
        self.backend.close()

    def __enter__(self) -> "Loader":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
