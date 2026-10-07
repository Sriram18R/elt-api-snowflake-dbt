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
        self.config = config
        self.connection = self._connect()
        logger.info(f"DuckDBLoader initialized with database: {config.database_path}")

    def _connect(self) -> duckdb.DuckDBPyConnection:
        try:
            conn = duckdb.connect(self.config.database_path)
            logger.info(f"Connected to DuckDB: {self.config.database_path}")
            return conn
        except Exception as e:
            msg = f"Failed to connect to DuckDB: {str(e)}"
            logger.error(msg)
            raise PipelineConnectionError(msg) from e

    @staticmethod
    def _sql_type_for_value(value: Any) -> str:
        """Infer SQL type from Python value."""
        if value is None:
            return "VARCHAR"
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "BIGINT"
        if isinstance(value, float):
            return "DOUBLE"
        return "VARCHAR"

    def _table_exists(self, table_name: str) -> bool:
        try:
            result = self.connection.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
                [table_name.lower()],
            ).fetchone()
            return result is not None
        except Exception:
            return False

    def load(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        mode: str = "append",
    ) -> int:
        if not records:
            logger.warning(f"No records to load into {table_name}")
            return 0

        try:
            table_name = table_name.strip('"').lower()
            columns = list(records[0].keys())
            quoted_cols = ", ".join(f'"{col.lower()}"' for col in columns)

            if mode == "replace":
                self.connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                logger.info(f"Dropped existing table: {table_name}")

            if mode == "replace" or not self._table_exists(table_name):
                column_definitions = ", ".join(
                    f'"{col.lower()}" {self._sql_type_for_value(records[0].get(col))}'
                    for col in columns
                )
                self.connection.execute(
                    f'CREATE TABLE IF NOT EXISTS "{table_name}" ({column_definitions})'
                )
                logger.info(f"Created table: {table_name}")

            placeholders = ", ".join(["?"] * len(columns))
            insert_sql = (
                f'INSERT INTO "{table_name}" ({quoted_cols}) VALUES ({placeholders})'
            )
            for record in records:
                values = [record.get(col) for col in columns]
                self.connection.execute(insert_sql, values)

            self.connection.commit()
            logger.info(f"Committed {len(records)} records to {table_name}")

            row_count = self.connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            logger.info(f"Loaded {row_count} rows into {table_name}")
            return row_count

        except Exception as e:
            msg = f"Failed to load data into {table_name}: {str(e)}"
            logger.error(msg)
            raise LoadingError(msg) from e

    def close(self) -> None:
        if self.connection:
            try:
                self.connection.close()
                logger.info("DuckDB connection closed")
            except Exception as e:
                logger.warning(f"Error closing DuckDB connection: {e}")


class SnowflakeLoader:
    """Load data into Snowflake."""

    def __init__(self, config: SnowflakeConfig, loader_config: LoaderConfig) -> None:
        self.config = config
        self.loader_config = loader_config
        self.connection = self._connect()
        logger.info(f"SnowflakeLoader initialized for {config.database}.{config.schema}")

    def _connect(self) -> snowflake.connector.SnowflakeConnection:
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
        if not records:
            logger.warning(f"No records to load into {table_name}")
            return 0

        try:
            cursor = self.connection.cursor()

            if self.loader_config.create_tables_if_missing:
                self._create_table_if_missing(cursor, table_name, records[0])

            if mode == "replace" and self.loader_config.truncate_before_load:
                cursor.execute(f"TRUNCATE TABLE {table_name}")
                logger.info(f"Truncated table: {table_name}")

            batch_size = self.loader_config.batch_size
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                self._insert_batch(cursor, table_name, batch)

            self.connection.commit()
            logger.info(f"Committed batch to {table_name}")

            row_count = len(records)
            logger.info(f"Loaded {row_count} rows into {table_name}")
            cursor.close()
            return row_count

        except Exception as e:
            self.connection.rollback()
            msg = f"Failed to load data into {table_name}: {str(e)}"
            logger.error(msg)
            raise LoadingError(msg) from e

    def _create_table_if_missing(
        self, cursor: Any, table_name: str, sample_record: Dict[str, Any]
    ) -> None:
        cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        if cursor.fetchone() is None:
            columns = []
            for key in sample_record.keys():
                columns.append(f"{key} VARCHAR")

            create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
            cursor.execute(create_sql)
            logger.info(f"Created table: {table_name}")

    def _insert_batch(
        self, cursor: Any, table_name: str, batch: List[Dict[str, Any]]
    ) -> None:
        if not batch:
            return

        keys = list(batch[0].keys())
        placeholders = ", ".join(["(%s)" for _ in keys]).replace("(%s)", "%s,").rstrip(",")
        insert_sql = f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})"

        for record in batch:
            values = tuple(record.get(key) for key in keys)
            cursor.execute(insert_sql, values)

    def close(self) -> None:
        if self.connection:
            try:
                self.connection.close()
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")


class Loader:
    """Universal loader for both DuckDB and Snowflake."""

    def __init__(
        self,
        warehouse_config: Any,
        loader_config: LoaderConfig,
        mode: str = "local",
    ) -> None:
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
        return self.backend.load(table_name, records, mode)

    def close(self) -> None:
        self.backend.close()

    def __enter__(self) -> "Loader":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


__all__ = ["Loader", "DuckDBLoader", "SnowflakeLoader"]
