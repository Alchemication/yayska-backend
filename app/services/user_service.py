from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user_model import UserModel
from app.schemas.user_schema import UserCreate


# Password hashing, keep it here to avoid recreating the context in each create_user function
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

async def get_user(db: AsyncSession, user_id: int) -> UserModel | None:
    """Get active user by ID.
    
    Args:
        db: Database session
        user_id: User's ID
        
    Returns:
        User object if found and active, None otherwise
    """
    result = await db.execute(
        select(UserModel)
        .filter(UserModel.id == user_id)
        .filter(UserModel.deleted_on.is_(None))
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    """Get active user by email.
    
    Args:
        db: Database session
        email: User's email address
        
    Returns:
        User object if found (active or inactive), None otherwise
    """
    result = await db.execute(
        select(UserModel)
        .filter(UserModel.email == email)
    )
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> UserModel | None:
    """Get active user by username.
    
    Args:
        db: Database session
        username: User's username
        
    Returns:
        User object if found (active or inactive), None otherwise
    """
    result = await db.execute(
        select(UserModel)
        .filter(UserModel.username == username)
    )
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[UserModel]:
    """Get list of active users with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of active User objects
    """
    result = await db.execute(
        select(UserModel)
        .filter(UserModel.deleted_on.is_(None))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_user(db: AsyncSession, user: UserCreate) -> UserModel:
    """Create a new user in the database with hashed password.

    Args:
        db: Database session for executing the transaction
        user: UserCreate schema containing the user data

    Returns:
        User: The newly created user object with populated database fields
    """
    db_user = UserModel(
        email=user.email,
        username=user.username,
        password_hash=pwd_context.hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def delete_user(db: AsyncSession, user_id: int) -> UserModel | None:
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
