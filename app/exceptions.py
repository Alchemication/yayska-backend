"""
Custom exceptions and error handling utilities for the Yayska application.
"""

from typing import Any, Dict, Optional


class YayskaException(Exception):
    """Base exception class for all Yayska application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        super().__init__(message)


class ValidationError(YayskaException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message, status_code=400, details=details, error_code="VALIDATION_ERROR"
        )


class AuthenticationError(YayskaException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401, error_code="AUTHENTICATION_ERROR")


class AuthorizationError(YayskaException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403, error_code="AUTHORIZATION_ERROR")


class NotFoundError(YayskaException):
    """Raised when a resource is not found."""

    def __init__(
        self, message: str = "Resource not found", resource_type: Optional[str] = None
    ):
        details = {"resource_type": resource_type} if resource_type else {}
        super().__init__(
            message, status_code=404, details=details, error_code="NOT_FOUND_ERROR"
        )


class ConflictError(YayskaException):
    """Raised when there's a conflict with the current state."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409, error_code="CONFLICT_ERROR")


class SQLError(YayskaException):
    """Raised when SQL query execution fails."""

    def __init__(
        self,
        message: str = "SQL query failed",
        query: Optional[str] = None,
        original_error: Optional[str] = None,
    ):
        details = {}
        if query:
            details["query"] = query
        if original_error:
            details["original_error"] = original_error
        super().__init__(
            message, status_code=500, details=details, error_code="SQL_ERROR"
        )


class DatabaseError(YayskaException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
    ):
        details = {"operation": operation} if operation else {}
        super().__init__(
            message, status_code=500, details=details, error_code="DATABASE_ERROR"
        )


class ExternalServiceError(YayskaException):
    """Raised when external service calls fail."""

    def __init__(
        self, message: str = "External service error", service: Optional[str] = None
    ):
        details = {"service": service} if service else {}
        super().__init__(
            message,
            status_code=502,
            details=details,
            error_code="EXTERNAL_SERVICE_ERROR",
        )


class RateLimitError(YayskaException):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_ERROR")


def extract_sql_error_message(exception: Exception) -> tuple[str, str]:
    """
    Extract meaningful error message from SQLAlchemy exceptions.

    Returns:
        tuple: (user_friendly_message, technical_details)
    """
    error_str = str(exception)

    # Handle common PostgreSQL errors
    if "column" in error_str.lower() and "does not exist" in error_str.lower():
        # Extract column name from error like: 'column "c.age" does not exist'
        import re

        match = re.search(r'column "([^"]*)" does not exist', error_str)
        if match:
            column_name = match.group(1)
            return f"Database column '{column_name}' does not exist", error_str
        return "Database column does not exist", error_str

    elif "relation" in error_str.lower() and "does not exist" in error_str.lower():
        # Handle table/relation errors
        match = re.search(r'relation "([^"]*)" does not exist', error_str)
        if match:
            table_name = match.group(1)
            return f"Database table '{table_name}' does not exist", error_str
        return "Database table does not exist", error_str

    elif "syntax error" in error_str.lower():
        return "SQL syntax error in query", error_str

    elif "duplicate key" in error_str.lower():
        return "Duplicate record - this data already exists", error_str

    elif "foreign key constraint" in error_str.lower():
        return "Invalid reference - related record not found", error_str

    elif "not null constraint" in error_str.lower():
        return "Required field is missing", error_str

    # Default fallback
    return "Database query failed", error_str
