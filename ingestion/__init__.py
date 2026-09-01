"""ELT API Snowflake DBT - Ingestion Module

Production-quality ELT pipeline for extracting data from public APIs,
validating, normalizing, and loading into Snowflake or local DuckDB.
"""

__version__ = "1.0.0"
__author__ = "Data Engineering Team"

from ingestion.config import Config
from ingestion.extractor import Extractor
from ingestion.loader import Loader
from ingestion.transformer import Transformer
from ingestion.validator import Validator

__all__ = [
    "Config",
    "Extractor",
    "Validator",
    "Transformer",
    "Loader",
]
