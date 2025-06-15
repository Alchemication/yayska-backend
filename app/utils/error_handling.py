"""
Error handling utilities for common database and API operations.
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    DatabaseError,
    NotFoundError,
    SQLError,
    extract_sql_error_message,
)

logger = structlog.getLogger()


async def safe_execute_query(
    db: AsyncSession,
    query: str | text,
    params: Optional[Dict[str, Any]] = None,
    operation_name: str = "database_query",
) -> Any:
    """
    Safely execute a database query with enhanced error handling.

    Args:
        db: Database session
        query: SQL query string or text() object
        params: Query parameters
        operation_name: Name of the operation for error messages

    Returns:
        Query result

    Raises:
        SQLError: If SQL execution fails with clear error message
    """
    try:
        if isinstance(query, str):
            query = text(query)

        result = await db.execute(query, params or {})
        return result
    except Exception as e:
        user_message, technical_details = extract_sql_error_message(e)

        logger.error(
            f"SQL query failed: {operation_name}",
            user_message=user_message,
            technical_details=technical_details,
            query=str(query),
            params=params,
        )

        raise SQLError(
            message=user_message,
            query=str(query),
            original_error=technical_details,
        )


async def verify_resource_ownership(
    db: AsyncSession,
    table_name: str,
    resource_id: int,
    user_id: int,
    resource_type: Optional[str] = None,
) -> None:
    """
    Verify that a resource belongs to the specified user.

    Args:
        db: Database session
        table_name: Name of the table to check
        resource_id: ID of the resource
        user_id: ID of the user
        resource_type: Type of resource for error messages (defaults to table_name)

    Raises:
        NotFoundError: If resource doesn't exist or doesn't belong to user
        DatabaseError: If database operation fails
    """
    from sqlalchemy import text

    if resource_type is None:
        resource_type = table_name.rstrip("s")  # Remove trailing 's' for singular form

    query = text(f"""
        SELECT id FROM {table_name}
        WHERE id = :resource_id AND user_id = :user_id
    """)

    try:
        result = await db.execute(
            query, {"resource_id": resource_id, "user_id": user_id}
        )
        if not result.mappings().first():
            raise NotFoundError(
                f"{resource_type.title()} not found or access denied",
                resource_type=resource_type,
            )
    except NotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(
            f"Failed to verify {resource_type} ownership: {str(e)}",
            operation="verify_ownership",
        )


def handle_database_errors(operation_name: str):
    """
    Decorator to handle common database errors and provide consistent error messages.

    Args:
        operation_name: Name of the operation for error logging
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (DatabaseError, NotFoundError):
                # Re-raise custom exceptions as-is
                raise
            except Exception as e:
                logger.exception(
                    f"Unexpected error in {operation_name}",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise DatabaseError(
                    f"Failed to {operation_name}: {str(e)}", operation=operation_name
                )

        return wrapper

    return decorator


def format_database_error(error: Exception, operation: str) -> Dict[str, Any]:
    """
    Format database errors into a consistent structure for logging.

    Args:
        error: The exception that occurred
        operation: The operation that was being performed

    Returns:
        Dictionary with formatted error information
    """
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "operation": operation,
        "details": getattr(error, "details", {}),
    }


async def safe_database_operation(
    db: AsyncSession, operation: Callable, operation_name: str, *args, **kwargs
) -> Any:
    """
    Safely execute a database operation with automatic error handling and rollback.

    Args:
        db: Database session
        operation: The async function to execute
        operation_name: Name of the operation for error messages
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        Result from the operation

    Raises:
        DatabaseError: If the operation fails
    """
    try:
        result = await operation(*args, **kwargs)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        logger.exception(
            f"Database operation failed: {operation_name}",
            **format_database_error(e, operation_name),
        )
        raise DatabaseError(
            f"Failed to {operation_name}: {str(e)}", operation=operation_name
        )
