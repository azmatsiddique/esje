"""Custom exceptions and error formatting for esje."""

from typing import Optional


class EsjeError(Exception):
    """Base exception class for all esje errors."""

    def __init__(self, message: str, hint: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\nHint: {self.hint}"
        return self.message


class ConnectionError(EsjeError):
    """Raised when database connection fails or credentials are invalid."""
    pass


class QueryError(EsjeError):
    """Raised when SQL query execution fails."""
    pass


class ConfigurationError(EsjeError):
    """Raised when configuration or connection registry parameters are invalid."""
    pass
