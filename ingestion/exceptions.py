"""Custom exceptions for the ELT pipeline."""


class ELTException(Exception):
    """Base exception for all ELT pipeline errors."""

    pass


class ConfigurationError(ELTException):
    """Raised when configuration is invalid or missing."""

    pass


class ExtractionError(ELTException):
    """Raised when data extraction from API fails."""

    pass


class ValidationError(ELTException):
    """Raised when data validation fails."""

    pass


class TransformationError(ELTException):
    """Raised when data transformation fails."""

    pass


class LoadingError(ELTException):
    """Raised when data loading to warehouse fails."""

    pass


class ConnectionError(ELTException):
    """Raised when database connection fails."""

    pass


class DataQualityError(ELTException):
    """Raised when data quality checks fail."""

    pass


class RetryableError(ELTException):
    """Raised for errors that can be retried."""

    pass


class NonRetryableError(ELTException):
    """Raised for errors that should not be retried."""

    pass
