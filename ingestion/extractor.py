"""Data extraction from APIs."""

import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.config import APIConfig
from ingestion.exceptions import ExtractionError, RetryableError
from ingestion.logger import get_logger

logger = get_logger(__name__)


class Extractor:
    """Extract data from APIs with retry logic and error handling."""

    def __init__(self, config: APIConfig) -> None:
        """Initialize extractor with API configuration.

        Args:
            config: API configuration

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self.session = self._create_session()
        logger.info(f"Extractor initialized with base_url: {config.base_url}")

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(self.config.headers)
        if self.config.api_key:
            session.headers.update({"Authorization": f"Bearer {self.config.api_key}"})

        return session

    def extract(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract data from API endpoint.

        Args:
            endpoint: API endpoint path (appended to base_url)
            params: Query parameters

        Returns:
            List of extracted records

        Raises:
            ExtractionError: If extraction fails
        """
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        logger.info(f"Extracting data from: {url}")

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            data = response.json()
            records = data if isinstance(data, list) else [data]

            logger.info(f"Successfully extracted {len(records)} records from {url}")
            return records

        except requests.exceptions.Timeout as e:
            msg = f"Timeout while extracting from {url}"
            logger.error(msg)
            raise RetryableError(msg) from e

        except requests.exceptions.ConnectionError as e:
            msg = f"Connection error while extracting from {url}"
            logger.error(msg)
            raise RetryableError(msg) from e

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code >= 500:
                msg = f"Server error ({status_code}) while extracting from {url}"
                logger.error(msg)
                raise RetryableError(msg) from e
            else:
                msg = f"HTTP error ({status_code}) while extracting from {url}"
                logger.error(msg)
                raise ExtractionError(msg) from e

        except ValueError as e:
            msg = f"Invalid JSON response from {url}"
            logger.error(msg)
            raise ExtractionError(msg) from e

        except Exception as e:
            msg = f"Unexpected error extracting from {url}: {str(e)}"
            logger.error(msg)
            raise ExtractionError(msg) from e

    def extract_paginated(
        self,
        endpoint: str,
        page_param: str = "page",
        limit_param: str = "limit",
        page_size: int = 100,
        max_pages: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract data from paginated API endpoint.

        Args:
            endpoint: API endpoint path
            page_param: Name of page parameter
            limit_param: Name of limit/size parameter
            page_size: Number of records per page
            max_pages: Maximum number of pages to extract (None = all)
            params: Additional query parameters

        Returns:
            List of all extracted records

        Raises:
            ExtractionError: If extraction fails
        """
        all_records: List[Dict[str, Any]] = []
        page = 1

        logger.info(
            f"Starting paginated extraction from {endpoint} "
            f"(page_size={page_size}, max_pages={max_pages})"
        )

        while True:
            if max_pages and page > max_pages:
                logger.info(f"Reached max_pages limit: {max_pages}")
                break

            request_params = {**(params or {}), page_param: page, limit_param: page_size}

            try:
                records = self.extract(endpoint, request_params)

                if not records:
                    logger.info(f"No more records at page {page}")
                    break

                all_records.extend(records)
                logger.info(
                    f"Extracted page {page}: {len(records)} records "
                    f"(total: {len(all_records)})"
                )

                # Check if we got fewer records than page_size (indicating last page)
                if len(records) < page_size:
                    logger.info(f"Reached last page at page {page}")
                    break

                page += 1
                time.sleep(0.5)  # Rate limiting

            except RetryableError as e:
                logger.warning(f"Retryable error on page {page}: {str(e)}")
                time.sleep(self.config.retry_delay)
                page += 1

        logger.info(f"Paginated extraction complete: {len(all_records)} total records")
        return all_records

    def close(self) -> None:
        """Close the requests session."""
        self.session.close()
        logger.info("Extractor session closed")

    def __enter__(self) -> "Extractor":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
