from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.user_model import User
from app.schemas.user_schema import UserCreate


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get active user by ID.
    
    Args:
        db: Database session
        user_id: User's ID
        
    Returns:
        User object if found and active, None otherwise
    """
    result = await db.execute(
        select(User)
        .filter(User.id == user_id)
        .filter(User.deleted_on.is_(None))
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get active user by email.
    
    Args:
        db: Database session
        email: User's email address
        
    Returns:
        User object if found and active, None otherwise
    """
    result = await db.execute(
        select(User)
        .filter(User.email == email)
        .filter(User.deleted_on.is_(None))
    )
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """Get list of active users with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of active User objects
    """
    result = await db.execute(
        select(User)
        .filter(User.deleted_on.is_(None))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Create a new user in the database.

    Args:
        db: Database session for executing the transaction
        user: UserCreate schema containing the user data

    Returns:
        User: The newly created user object with populated database fields

    Raises:
        SQLAlchemyError: If there's an error during database transaction
    """
    db_user = User(email=user.email)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def delete_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Soft delete a user by setting their deleted_on timestamp.
    
    Args:
        db: Database session
        user_id: ID of the user to delete
        
    Returns:
        User: The deleted user object if found, None otherwise
        
    Raises:
        SQLAlchemyError: If there's an error during database transaction
    """
    user = await get_user(db, user_id)
    if user:
        user.deleted_on = datetime.now()
        await db.commit()
        await db.refresh(user)
    return user
