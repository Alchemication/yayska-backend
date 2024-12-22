from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services import user_service
from app.schemas.user_schema import UserInDB, UserCreate
from app.database import get_db


router = APIRouter()

@router.post("/", response_model=UserInDB)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user.

    Args:
        user: User creation data containing email, username and other required fields
        db: Database session dependency

    Returns:
        UserInDB: The created user object

    Raises:
        HTTPException: If email or username is already registered
    """
    # Check for existing email
    db_user = await user_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check for existing username
    db_user = await user_service.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    return await user_service.create_user(db=db, user=user)

@router.get("/", response_model=list[UserInDB])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Retrieve a list of users with pagination.

    Args:
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        db: Database session dependency

    Returns:
        list[UserInDB]: List of user objects
    """
    users = await user_service.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserInDB)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific user by ID.

    Args:
        user_id: The ID of the user to retrieve
        db: Database session dependency

    Returns:
        UserInDB: The requested user object

    Raises:
        HTTPException: If user is not found
    """
    db_user = await user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a user by ID.

    Args:
        user_id: The ID of the user to delete
        db: Database session dependency

    Raises:
        HTTPException: If user is not found
    """
    db_user = await user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user_service.delete_user(db, user_id=user_id)
    return None
