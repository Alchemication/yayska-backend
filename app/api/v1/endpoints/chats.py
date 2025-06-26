from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import chat as chat_schemas
from app.services import chat as chat_service
from app.utils.deps import CurrentUser

router = APIRouter()
logger = structlog.get_logger()


@router.post(
    "/find-or-create",
    response_model=chat_schemas.ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    description="Finds an existing chat session or creates a new one based on context.",
)
async def find_or_create_session(
    create_data: chat_schemas.ChatSessionFindOrCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    The heart of the chat feature. This single endpoint starts a new chat
    or retrieves an existing one for a specific context, making it endlessly scalable.
    """
    session_row = await chat_service.find_or_create_chat_session(
        db=db, user_id=current_user["id"], create_data=create_data
    )
    return chat_schemas.ChatSessionResponse(
        id=session_row["id"],
        user_id=session_row["user_id"],
        child_id=session_row["child_id"],
        title=session_row["title"],
        entry_point_type=session_row["entry_point_type"],
        entry_point_context=session_row["entry_point_context"],
        created_at=session_row["created_at"],
        updated_at=session_row["updated_at"],
    )


@router.get(
    "/",
    response_model=chat_schemas.ChatSessionListResponse,
    description="Get a paginated list of all chat sessions for the current user.",
)
async def get_sessions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Populates the 'previous sessions' side panel.
    Returns a paginated list of all chat sessions for the current user.
    """
    sessions_data = await chat_service.get_chat_sessions_by_user(
        db=db, user_id=current_user["id"], limit=limit, offset=offset
    )
    return chat_schemas.ChatSessionListResponse(
        items=[
            chat_schemas.ChatSessionListItem(
                id=item["id"],
                title=item["title"],
                updated_at=item["updated_at"],
            )
            for item in sessions_data["items"]
        ],
        total=sessions_data["total"],
    )


@router.get(
    "/{chat_id}/messages",
    response_model=list[chat_schemas.ChatMessageResponse],
    description="Fetch the message history for a given chat session.",
)
async def get_messages(
    chat_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Fetches the message history for a given chat session.
    Use limit and offset for pagination to load older messages.
    """
    message_rows = await chat_service.get_messages_by_session(
        db=db,
        session_id=chat_id,
        user_id=current_user["id"],
        limit=limit,
        offset=offset,
    )
    return [
        chat_schemas.ChatMessageResponse(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            reasoning=row["reasoning"],
            context_snapshot=row["context_snapshot"],
            llm_usage=row["llm_usage"],
            feedback_thumbs=row["feedback_thumbs"],
            feedback_text=row["feedback_text"],
            created_at=row["created_at"],
        )
        for row in message_rows
    ]


@router.post(
    "/{chat_id}/messages",
    response_model=chat_schemas.ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    description="Send a new message and get the AI's response.",
)
async def create_message(
    chat_id: UUID,
    message: chat_schemas.UserMessageCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Sends a new message from the user and gets the AI's response.
    This is the main interaction endpoint.
    For the MVP, it returns a standard JSON response with the assistant's complete message.
    """
    await chat_service.check_and_update_user_ai_request_count(
        db=db, user_id=current_user["id"]
    )
    assistant_message_row = await chat_service.create_message_and_get_bot_response(
        db=db, session_id=chat_id, user_id=current_user["id"], user_message=message
    )
    return chat_schemas.ChatMessageResponse(
        id=assistant_message_row["id"],
        session_id=assistant_message_row["session_id"],
        role=assistant_message_row["role"],
        content=assistant_message_row["content"],
        reasoning=assistant_message_row["reasoning"],
        context_snapshot=assistant_message_row["context_snapshot"],
        llm_usage=assistant_message_row["llm_usage"],
        feedback_thumbs=assistant_message_row["feedback_thumbs"],
        feedback_text=assistant_message_row["feedback_text"],
        created_at=assistant_message_row["created_at"],
    )


@router.patch(
    "/{chat_id}/messages/{message_id}",
    response_model=chat_schemas.ChatMessageResponse,
    description="Add feedback to a specific assistant message.",
)
async def update_message_feedback(
    chat_id: UUID,
    message_id: UUID,
    update_data: chat_schemas.MessageFeedbackUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Adds feedback (a vote and optional text) to a specific message from the assistant.
    """
    updated_message_row = await chat_service.update_message_feedback(
        db=db,
        session_id=chat_id,
        message_id=message_id,
        user_id=current_user["id"],
        vote=update_data.feedback.vote,
        text_feedback=update_data.feedback.text,
    )
    return chat_schemas.ChatMessageResponse(
        id=updated_message_row["id"],
        session_id=updated_message_row["session_id"],
        role=updated_message_row["role"],
        content=updated_message_row["content"],
        reasoning=updated_message_row["reasoning"],
        context_snapshot=updated_message_row["context_snapshot"],
        llm_usage=updated_message_row["llm_usage"],
        feedback_thumbs=updated_message_row["feedback_thumbs"],
        feedback_text=updated_message_row["feedback_text"],
        created_at=updated_message_row["created_at"],
    )
