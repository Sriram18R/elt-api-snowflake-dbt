.PHONY: help install install-dev lint format test test-unit test-integration dbt-deps dbt-compile dbt-run dbt-test dbt-docs clean setup

.DEFAULT_GOAL := help

PYTHON := python3
PIP := pip3
VENV := venv
SHELL := /bin/bash

help: ## Display this help message
	@echo "ELT API Snowflake DBT - Available Commands"
	@echo "==========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Set up local development environment
	@echo "Setting up development environment..."
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install --upgrade pip setuptools wheel
	. $(VENV)/bin/activate && $(PIP) install -r requirements-dev.txt
	cp .env.example .env
	@echo "✓ Setup complete. Run: source $(VENV)/bin/activate"

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	$(PIP) install -r requirements-dev.txt

lint: ## Run code linting (ruff)
	@echo "Running Ruff linter..."
	ruff check ingestion tests --select=E,W,F
	@echo "✓ Linting passed"

format: ## Format code (black + isort)
	@echo "Formatting code..."
	black ingestion tests
	isort ingestion tests
	@echo "✓ Formatting complete"

type-check: ## Run type checking (mypy)
	@echo "Running mypy type checker..."
	mypy ingestion --strict --ignore-missing-imports
	@echo "✓ Type checking passed"

test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	pytest tests/unit -v --cov=ingestion --cov-report=term-missing --cov-report=html
	@echo "✓ Unit tests passed"

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	pytest tests/integration -v -s
	@echo "✓ Integration tests passed"

test-coverage: ## Generate coverage report and open HTML
	pytest tests -v --cov=ingestion --cov-report=html
	@echo "Opening coverage report..."
	open htmlcov/index.html || xdg-open htmlcov/index.html

ingest: ## Run the ingestion pipeline (local mode)
	@echo "Running ELT ingestion pipeline..."
	export EXECUTION_MODE=local && $(PYTHON) -m ingestion.main
	@echo "✓ Ingestion complete"

dbt-deps: ## Install DBT dependencies
	@echo "Installing DBT dependencies..."
	cd dbt_project && dbt deps
	@echo "✓ DBT dependencies installed"

dbt-compile: ## Compile DBT project (validation only)
	@echo "Compiling DBT project..."
	cd dbt_project && dbt compile
	@echo "✓ DBT project compiled"

dbt-run: ## Execute DBT models (local DuckDB)
	@echo "Running DBT models..."
	cd dbt_project && dbt run
	@echo "✓ DBT models executed"

dbt-test: ## Run DBT tests
	@echo "Running DBT tests..."
	cd dbt_project && dbt test --store-failures
	@echo "✓ DBT tests passed"

dbt-docs: ## Generate DBT documentation
	@echo "Generating DBT documentation..."
	cd dbt_project && dbt docs generate
	@echo "✓ Documentation generated"

dbt-docs-serve: ## Generate and serve DBT documentation
	@echo "Generating and serving DBT documentation..."
	cd dbt_project && dbt docs generate && dbt docs serve

dbt-freshness: ## Check DBT source freshness
	@echo "Checking source freshness..."
	cd dbt_project && dbt source freshness

pipeline: install lint test ingest dbt-run dbt-test ## Run full pipeline: install → lint → test → ingest → dbt

ci: install-dev lint type-check test dbt-compile dbt-test ## Run CI checks (no Snowflake)

clean: ## Clean build artifacts and caches
	@echo "Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage*" -delete
	@echo "✓ Cleaned"

clean-data: ## Remove local data and logs
	@echo "Removing local data and logs..."
	rm -f data/local_warehouse.duckdb
	rm -f logs/*.log
	@echo "✓ Data cleaned"

db-inspect: ## Inspect local DuckDB database
	@echo "Inspecting local DuckDB database..."
	duckdb data/local_warehouse.duckdb ".tables"

db-query: ## Query local DuckDB (usage: make db-query QUERY="SELECT * FROM table LIMIT 10")
	@echo "Executing query..."
	duckdb data/local_warehouse.duckdb "$(QUERY)"

version: ## Show version information
	@echo "Python: $$($(PYTHON) --version)"
	@echo "pip: $$($(PIP) --version)"
	@command -v dbt >/dev/null && echo "DBT: $$(dbt --version)" || echo "DBT: not installed"
	@command -v duckdb >/dev/null && echo "DuckDB: $$(duckdb --version)" || echo "DuckDB: not installed"

.PHONY: help setup install install-dev lint format type-check test test-unit test-integration test-coverage ingest dbt-deps dbt-compile dbt-run dbt-test dbt-docs dbt-docs-serve dbt-freshness pipeline ci clean clean-data db-inspect db-query version
