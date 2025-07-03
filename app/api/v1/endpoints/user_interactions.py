from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user_interactions import UserInteraction, UserInteractionCreate
from app.services import user_interactions as user_interactions_service
from app.utils.deps import CurrentUser

router = APIRouter()


@router.post(
    "",
    response_model=UserInteraction,
    status_code=status.HTTP_201_CREATED,
    description="Logs a new user interaction.",
)
async def create_user_interaction(
    interaction_data: UserInteractionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> UserInteraction:
    interaction_row = await user_interactions_service.create_user_interaction(
        db=db, user_id=current_user["id"], interaction_data=interaction_data
    )
    return UserInteraction.model_validate(interaction_row)
