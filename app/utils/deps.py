"""
Dependency utilities for FastAPI endpoints.
"""

from typing import Annotated, Any, Dict

from fastapi import Depends

from app.database import get_db
from app.services.auth import get_current_user


# Create a reusable dependency for the current authenticated user
async def get_current_user_dependency(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Get the current authenticated user. This is a shorthand dependency that combines
    the database and authentication.

    Args:
        db: Database connection from dependency

    Returns:
        Dict containing user information
    """
    return await get_current_user(db)


# Create a type annotation for a current user
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user_dependency)]
