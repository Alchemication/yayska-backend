import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.schemas.user_interactions import UserInteractionCreate


async def create_user_interaction(
    db: AsyncSession, user_id: int, interaction_data: UserInteractionCreate
) -> dict[str, Any]:
    """
    Logs a user interaction event in the database.
    """
    query = text(
        """
        INSERT INTO user_interactions (user_id, session_id, interaction_type, interaction_context)
        VALUES (:user_id, :session_id, :interaction_type, :interaction_context)
        RETURNING id, user_id, session_id, interaction_type, interaction_context, created_at
    """
    )
    result = await db.execute(
        query,
        {
            "user_id": user_id,
            "session_id": interaction_data.session_id,
            "interaction_type": interaction_data.interaction_type.value,
            "interaction_context": json.dumps(interaction_data.interaction_context)
            if interaction_data.interaction_context
            else None,
        },
    )
    await db.commit()
    created_interaction = result.mappings().one()
    return created_interaction
