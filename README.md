# ELT Pipeline: API → Snowflake → dbt

A production-ready ELT (Extract, Load, Transform) pipeline that extracts data from APIs, validates it, and loads it into Snowflake or DuckDB for transformation with dbt.

## Features

- **Extract**: Pull data from REST APIs with retry logic and pagination support
- **Validate**: Comprehensive data quality checks and schema validation
- **Transform**: Normalize, clean, and enrich data before loading
- **Load**: Support for both DuckDB (local) and Snowflake (production)
- **Logging**: Detailed logging with file rotation and console output
- **Configuration Management**: Environment-based configuration with sensible defaults
- **Error Handling**: Custom exception hierarchy with retry policies

## Project Structure

```
.
├── ingestion/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── exceptions.py      # Custom exceptions
│   ├── logger.py          # Logging setup
│   ├── extractor.py       # API data extraction
│   ├── validator.py       # Data validation
│   ├── transformer.py     # Data transformation
│   ├── loader.py          # Data loading
│   └── main.py            # Pipeline orchestration
├── tests/                 # Unit and integration tests
├── dbt_project/          # dbt models and configurations
├── .env.example          # Environment variables template
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── Makefile             # Development commands
└── README.md            # This file
```

## Installation

### Prerequisites

- Python 3.8+
- pip or conda

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd elt-api-snowflake-dbt
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Edit `.env` to configure the pipeline:

### Execution Mode
```env
EXECUTION_MODE=local  # or 'snowflake' for production
LOG_LEVEL=INFO        # DEBUG, INFO, WARNING, ERROR
```

### API Configuration
```env
API_BASE_URL=https://api.example.com
API_TIMEOUT=30
API_MAX_RETRIES=3
API_KEY=your_api_key
```

### Snowflake Configuration (if EXECUTION_MODE=snowflake)
```env
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=ANALYTICS
SNOWFLAKE_SCHEMA=PUBLIC
```

## Usage

### Basic Pipeline Run

```python
from ingestion.main import ELTPipeline

with ELTPipeline() as pipeline:
    report = pipeline.run(
        endpoint="api/users",
        table_name="users",
        load_mode="append"
    )
    print(report)
```

### Paginated Data Extraction

```python
with ELTPipeline() as pipeline:
    report = pipeline.extract_paginated(
        endpoint="api/events",
        table_name="events",
        page_size=100,
        max_pages=10
    )
```

### With Data Validation

```python
schema = {
    "required_fields": ["id", "email"],
    "field_types": {
        "id": int,
        "email": str
    }
}

with ELTPipeline() as pipeline:
    report = pipeline.run(
        endpoint="api/users",
        table_name="users",
        schema=schema
    )
```

### With Data Transformation

```python
transformations = [
    {"type": "rename", "from": "user_id", "to": "id"},
    {"type": "map", "field": "status", "mapping": {"active": 1, "inactive": 0}},
]

with ELTPipeline() as pipeline:
    report = pipeline.run(
        endpoint="api/users",
        table_name="users",
        transformations=transformations
    )
```

## Development

### Run Tests
```bash
make test
```

### Run with Coverage
```bash
make coverage
```

### Code Quality Checks
```bash
make lint      # Run linters
make format    # Format code with black
make type-check  # Run mypy type checker
```

### View Logs
```bash
tail -f logs/elt_pipeline.log
```

## Architecture

### Extract Phase
- Connects to REST APIs using configurable authentication
- Supports pagination for large datasets
- Implements retry logic with exponential backoff
- Rate limiting to avoid API throttling

### Validate Phase
- Schema validation against defined schemas
- Data quality checks (null counts, missing values)
- Duplicate detection based on key fields
- Configurable strict vs. lenient mode

### Transform Phase
- Field normalization (lowercase, trim whitespace)
- Null value handling
- Duplicate removal
- Custom transformations (rename, map, concatenate, extract)
- Computed field generation

### Load Phase
- Batch loading for performance
- Support for multiple warehouse backends
- Automatic table creation with schema inference
- Configurable truncate-before-load behavior

## Error Handling

The pipeline uses custom exceptions for different error scenarios:

- `ELTException`: Base exception for all pipeline errors
- `ConfigurationError`: Configuration is invalid or missing
- `ExtractionError`: Data extraction from API fails
- `ValidationError`: Data validation fails
- `TransformationError`: Data transformation fails
- `LoadingError`: Data loading fails
- `RetryableError`: Errors that can be retried
- `NonRetryableError`: Errors that should not be retried

## Logging

The pipeline logs to both console and file:

- **Console**: Shows INFO level and above
- **File**: `logs/elt_pipeline.log` (rotated, 10MB max)

Log levels can be configured via `LOG_LEVEL` environment variable.

## Data Warehouse Support

### DuckDB (Local Development)
- Lightweight, serverless
- Perfect for testing and development
- Stores data in `data/local_warehouse.duckdb`

### Snowflake (Production)
- Fully managed cloud warehouse
- Scalable to any data volume
- Requires Snowflake credentials

## dbt Integration

The loaded raw data can be transformed using dbt:

```bash
cd dbt_project
dbt run
dbt test
dbt docs generate
```

## Performance Tuning

- **Batch Size**: Adjust `LOADER_BATCH_SIZE` for optimal insert performance
- **Pagination**: Use smaller `page_size` for unreliable networks
- **Retry Delays**: Increase `API_RETRY_DELAY` for rate-limited APIs
- **Validation**: Use `VALIDATION_STRICT_MODE=false` to collect all errors before failing

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and add tests
3. Run tests and linters: `make test lint`
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature/your-feature`
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions, please open a GitHub issue.
