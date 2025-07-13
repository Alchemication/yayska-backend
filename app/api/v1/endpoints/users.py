import json

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.utils.deps import CurrentUser

router = APIRouter()
logger = structlog.get_logger()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get information about the currently authenticated user.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_user_memory(
    user_data: UserUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Update the memory for the currently authenticated user.
    """
    query = text(
        """
        UPDATE users
        SET memory = :memory, updated_at = CURRENT_TIMESTAMP
        WHERE id = :user_id
        RETURNING id, email, first_name, last_name, picture_url, memory,
                  created_at, updated_at, last_login_at
    """
    )

    result = await db.execute(
        query,
        {
            "user_id": current_user["id"],
            "memory": json.dumps(user_data.memory),
        },
    )
    await db.commit()

    updated_user = result.mappings().first()

    return updated_user
