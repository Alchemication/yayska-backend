import json
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import DatabaseError, NotFoundError
from app.prompts import chat as prompt_models
from app.schemas.chat import (
    ChatMessageRole,
    ChatSessionFindOrCreate,
    EntryPointType,
    UserMessageCreate,
)
from app.utils.llm import AIModel, LLMMessage, get_completion

logger = structlog.get_logger()


async def check_and_update_user_ai_request_count(db: AsyncSession, user_id: int):
    """
    Checks the user's AI request count and updates it.
    Raises an HTTPException if the limit is exceeded.
    """
    logger.info("Checking user for AI chat rate limit", user_id=user_id)
    user_query = text(
        """
        SELECT email, ai_chat_request_daily_count, last_ai_chat_request_date
        FROM users
        WHERE id = :user_id
        """
    )
    user_result = await db.execute(user_query, {"user_id": user_id})
    user = user_result.mappings().first()

    if not user:
        raise NotFoundError(f"User with id {user_id} not found.")

    if user["email"] in settings.AI_REQUEST_WHITELIST:
        logger.info(
            "User is in whitelist, skipping rate limit check",
            user_id=user_id,
            email=user["email"],
        )
        return

    today = date.today()
    last_request_date = user["last_ai_chat_request_date"]

    if last_request_date != today:
        # First request of the day, reset count
        logger.info(
            "Resetting user AI chat request count for a new day", user_id=user_id
        )
        update_query = text(
            """
            UPDATE users
            SET ai_chat_request_daily_count = 1, last_ai_chat_request_date = :today
            WHERE id = :user_id
            """
        )
        await db.execute(update_query, {"user_id": user_id, "today": today})
    else:
        # Subsequent request on the same day
        if user["ai_chat_request_daily_count"] >= settings.AI_REQUESTS_PER_DAY_LIMIT:
            logger.warning(
                "User has exceeded AI chat request limit",
                user_id=user_id,
                count=user["ai_chat_request_daily_count"],
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You have exceeded your daily limit for AI chat requests.",
            )
        else:
            logger.info(
                "Incrementing user AI chat request count",
                user_id=user_id,
                new_count=user["ai_chat_request_daily_count"] + 1,
            )
            update_query = text(
                """
                UPDATE users
                SET ai_chat_request_daily_count = ai_chat_request_daily_count + 1
                WHERE id = :user_id
                """
            )
            await db.execute(update_query, {"user_id": user_id})
    await db.commit()


async def find_or_create_chat_session(
    db: AsyncSession, user_id: int, create_data: ChatSessionFindOrCreate
) -> dict[str, Any]:
    """Finds an existing chat session or creates a new one."""
    session_row = None
    if create_data.entry_point_type == EntryPointType.CONCEPT_COACH:
        concept_id = create_data.context_data.get("concept_id")
        if not concept_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="concept_id is required for CONCEPT_COACH entry point.",
            )

        find_query = text(
            """
            SELECT id FROM chat_sessions
            WHERE user_id = :user_id
              AND child_id = :child_id
              AND entry_point_type = :entry_point_type
              AND entry_point_context ->> 'concept_id' = :concept_id
            ORDER BY created_at DESC
            LIMIT 1;
        """
        )
        result = await db.execute(
            find_query,
            {
                "user_id": user_id,
                "child_id": create_data.child_id,
                "entry_point_type": create_data.entry_point_type.value,
                "concept_id": str(concept_id),
            },
        )
        session_row = result.fetchone()

    if session_row:
        session_id = session_row[0]
    else:
        # --- Create a new session ---
        title = "New Chat"  # Default title
        if create_data.entry_point_type == EntryPointType.CONCEPT_COACH:
            concept_id = create_data.context_data.get("concept_id")
            concept_query = text(
                "SELECT concept_name FROM concepts WHERE id = :concept_id"
            )
            concept_result = await db.execute(concept_query, {"concept_id": concept_id})
            concept_row = concept_result.fetchone()
            if concept_row:
                title = f"Coaching on {concept_row[0]}"

        create_query = text(
            """
            INSERT INTO chat_sessions (user_id, child_id, title, entry_point_type, entry_point_context, updated_at)
            VALUES (:user_id, :child_id, :title, :entry_point_type, :entry_point_context, CURRENT_TIMESTAMP)
            RETURNING id;
        """
        )
        result = await db.execute(
            create_query,
            {
                "user_id": user_id,
                "child_id": create_data.child_id,
                "title": title,
                "entry_point_type": create_data.entry_point_type.value,
                "entry_point_context": json.dumps(create_data.context_data),
            },
        )
        session_id = result.scalar_one()

    # Fetch the full session to return
    full_session_query = text("SELECT * FROM chat_sessions WHERE id = :session_id")
    full_session_result = await db.execute(
        full_session_query, {"session_id": session_id}
    )
    new_session_row = full_session_result.mappings().first()
    if not new_session_row:
        raise NotFoundError("Chat session not found after creation.")
    return new_session_row


async def get_chat_sessions_by_user(
    db: AsyncSession, user_id: int, limit: int, offset: int
):
    """Retrieves a paginated list of chat sessions for a user."""
    count_query = text("SELECT COUNT(*) FROM chat_sessions WHERE user_id = :user_id")
    total_result = await db.execute(count_query, {"user_id": user_id})
    total = total_result.scalar_one()

    query = text(
        """
        SELECT id, title, updated_at
        FROM chat_sessions
        WHERE user_id = :user_id
        ORDER BY updated_at DESC NULLS LAST, created_at DESC
        LIMIT :limit OFFSET :offset;
    """
    )
    result = await db.execute(
        query, {"user_id": user_id, "limit": limit, "offset": offset}
    )
    sessions = result.mappings().all()
    return {"items": sessions, "total": total}


async def get_messages_by_session(
    db: AsyncSession, session_id: UUID, user_id: int, limit: int, offset: int
):
    """Retrieves a paginated list of messages for a given chat session."""
    session_check = text(
        "SELECT id FROM chat_sessions WHERE id = :session_id AND user_id = :user_id"
    )
    session_result = await db.execute(
        session_check, {"session_id": session_id, "user_id": user_id}
    )
    if not session_result.fetchone():
        raise NotFoundError(f"Chat session with id {session_id} not found.")

    query = text(
        """
        SELECT * FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY message_order ASC
        LIMIT :limit OFFSET :offset;
    """
    )
    result = await db.execute(
        query, {"session_id": session_id, "limit": limit, "offset": offset}
    )
    return result.mappings().all()


def _time_ago(dt: datetime) -> str:
    """Converts a datetime object to a human-readable 'time ago' string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"over {years} year{'s' if years > 1 else ''} ago"
    if diff.days > 30:
        months = diff.days // 30
        return f"about {months} month{'s' if months > 1 else ''} ago"
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    if diff.seconds < 3600:
        return "less than an hour ago"
    hours = diff.seconds // 3600
    return f"about {hours} hour{'s' if hours > 1 else ''} ago"


async def create_message_and_get_bot_response(
    db: AsyncSession,
    session_id: UUID,
    user_id: int,
    user_message: UserMessageCreate,
):
    """
    Creates a user message, constructs a detailed prompt, calls the LLM,
    and returns the assistant's response.
    """
    # 1. Verify session exists and belongs to user, and get its context
    session_check_query = text(
        """
        SELECT cs.id, cs.child_id, cs.entry_point_context,
               u.first_name as user_name,
               c.name as child_name,
               sy.year_name as school_year
        FROM chat_sessions cs
        JOIN users u ON cs.user_id = u.id
        JOIN children c ON cs.child_id = c.id
        LEFT JOIN school_years sy ON c.school_year_id = sy.id
        WHERE cs.id = :session_id AND cs.user_id = :user_id
    """
    )
    session_result = await db.execute(
        session_check_query, {"session_id": session_id, "user_id": user_id}
    )
    session_data = session_result.mappings().first()
    if not session_data:
        raise NotFoundError(f"Chat session with id {session_id} not found.")

    # 2. Fetch conversation history (from before this new message)
    history_query = text(
        """
        SELECT role, content FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY message_order DESC
        LIMIT 10
    """
    )
    history_result = await db.execute(history_query, {"session_id": session_id})
    history_rows = reversed(history_result.mappings().all())
    conversation_history = [
        prompt_models.Message(role=row["role"].lower(), content=row["content"])
        for row in history_rows
    ]

    # 3. Insert the new user message *after* fetching history
    user_insert_query = text(
        """
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:session_id, :role, :content)
        RETURNING id;
    """
    )
    await db.execute(
        user_insert_query,
        {
            "session_id": session_id,
            "role": ChatMessageRole.USER.value,
            "content": user_message.content,
        },
    )

    # 4. Construct the prompt for the LLM
    prompt_generator = prompt_models.ConceptCoachPrompt()

    # 4a. Populate Parent and Child Context
    parent_context = prompt_models.ParentContext(name=session_data["user_name"])
    child_context = prompt_models.ChildContext(
        name=session_data["child_name"],
        class_level=session_data["school_year"],
        # notes_from_memory will be populated from DB in the future
    )

    # 4b. Fetch Concept Interaction History
    interaction_history_query = text(
        """
        SELECT
            cs.entry_point_context ->> 'concept_id' as concept_id,
            c.concept_name as concept_name,
            s.subject_name as subject_name,
            cs.updated_at
        FROM chat_sessions cs
        JOIN concepts c ON (cs.entry_point_context ->> 'concept_id')::int = c.id
        LEFT JOIN subjects s ON c.subject_id = s.id
        WHERE cs.user_id = :user_id
          AND cs.child_id = :child_id
          AND cs.entry_point_type = 'CONCEPT_COACH'
          AND cs.id != :current_session_id
        ORDER BY cs.updated_at DESC
        LIMIT 10;
    """
    )
    interaction_result = await db.execute(
        interaction_history_query,
        {
            "user_id": user_id,
            "child_id": session_data["child_id"],
            "current_session_id": session_id,
        },
    )
    concept_history = [
        prompt_models.ConceptHistoryItem(
            concept_id=row["concept_id"],
            concept_name=row["concept_name"],
            subject=row["subject_name"],
            viewed_ago=_time_ago(row["updated_at"]),
        )
        for row in interaction_result.mappings().all()
    ]

    # 4c. Populate Learning Context (specific to CONCEPT_COACH)
    concept_id = session_data["entry_point_context"].get("concept_id")
    learning_context = None
    if concept_id:
        concept_query = text(
            """
            SELECT
                c.concept_name,
                c.concept_description,
                s.subject_name,
                cm.why_important ->> 'practical_value' as practical_value,
                cm.parent_guide -> 'key_points' as key_points,
                cm.difficulty_stats -> 'common_barriers' as common_barriers
            FROM concepts c
            LEFT JOIN subjects s ON c.subject_id = s.id
            LEFT JOIN concept_metadata cm ON c.id = cm.concept_id
            WHERE c.id = :concept_id
        """
        )
        concept_result = await db.execute(concept_query, {"concept_id": concept_id})
        concept_data = concept_result.mappings().first()
        if concept_data:
            learning_context = prompt_models.LearningContext(
                current_concept_id=concept_id,
                current_concept_name=concept_data["concept_name"],
                current_subject=concept_data["subject_name"],
                short_description=concept_data["concept_description"],
                practical_value=concept_data["practical_value"],
                key_points=concept_data["key_points"],
                common_barriers=concept_data["common_barriers"],
                recent_concept_chats=concept_history,
            )

    if not learning_context:
        raise DatabaseError(
            f"Could not construct learning context for concept_id: {concept_id}"
        )

    # 4d. Build the final system prompt string and conversation messages
    system_prompt = prompt_generator.get_system_prompt(
        parent_context=parent_context,
        child_context=child_context,
        learning_context=learning_context,
    )
    # The user's new message is part of the conversation now
    conversation_history.append(
        prompt_models.Message(
            role=ChatMessageRole.USER.value, content=user_message.content
        )
    )
    messages = [
        LLMMessage(role=msg.role, content=msg.content) for msg in conversation_history
    ]

    # 5. Call the LLM
    llm_response = await get_completion(
        ai_model=AIModel.GEMINI_FLASH_2_0,
        system_prompt=system_prompt,
        messages=messages,
        response_type=None,  # We want a plain string response
    )
    assistant_content = llm_response.content
    if not isinstance(assistant_content, str):
        # Handle cases where the LLM might return unexpected structured data
        assistant_content = str(assistant_content)
    llm_usage_data = llm_response.usage_metadata

    # 6. Save the assistant's response to the database
    assistant_insert_query = text(
        """
        INSERT INTO chat_messages (session_id, role, content, llm_usage)
        VALUES (:session_id, :role, :content, :llm_usage)
        RETURNING *;
    """
    )
    result = await db.execute(
        assistant_insert_query,
        {
            "session_id": session_id,
            "role": ChatMessageRole.ASSISTANT.value,
            "content": assistant_content,
            "llm_usage": json.dumps(llm_usage_data) if llm_usage_data else None,
        },
    )
    assistant_message = result.mappings().first()

    # 7. Update the session's updated_at timestamp
    update_session_query = text(
        """
        UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = :session_id
    """
    )
    await db.execute(update_session_query, {"session_id": session_id})

    if not assistant_message:
        raise DatabaseError("Failed to create assistant message.")

    return assistant_message


async def update_message_feedback(
    db: AsyncSession,
    session_id: UUID,
    message_id: UUID,
    user_id: int,
    vote: int,
    text_feedback: str | None,
):
    """Updates the user's feedback for a specific message."""
    # Verify the message exists in a session belonging to the user
    message_check_query = text(
        """
        SELECT m.id FROM chat_messages m
        JOIN chat_sessions s ON m.session_id = s.id
        WHERE m.id = :message_id AND s.id = :session_id AND s.user_id = :user_id AND m.role = 'ASSISTANT'
    """
    )
    result = await db.execute(
        message_check_query,
        {"message_id": message_id, "session_id": session_id, "user_id": user_id},
    )
    if not result.fetchone():
        raise NotFoundError(
            f"Assistant message with id {message_id} not found in session {session_id}."
        )

    update_query = text(
        """
        UPDATE chat_messages
        SET feedback_thumbs = :vote, feedback_text = :text_feedback
        WHERE id = :message_id
        RETURNING *;
    """
    )
    result = await db.execute(
        update_query,
        {"vote": vote, "text_feedback": text_feedback, "message_id": message_id},
    )
    updated_message = result.mappings().first()
    if not updated_message:
        raise DatabaseError("Failed to update message feedback.")

    return updated_message
