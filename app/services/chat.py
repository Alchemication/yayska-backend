import json
from datetime import date, datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.exceptions import DatabaseError, NotFoundError
from app.prompts import chat as prompt_models
from app.schemas.chat import (
    ChatMessageRole,
    ChatSessionFindOrCreate,
    EntryPointType,
    UserMessageCreate,
)
from app.utils.llm import AIModel, LLMMessage, get_completion, get_completion_stream

logger = structlog.get_logger()

# --- Chat Service Constants ---
DEFAULT_CHAT_MODEL = AIModel.GEMINI_FLASH_2_0
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096


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


async def _get_session_data(
    db: AsyncSession, session_id: UUID, user_id: int
) -> dict[str, Any]:
    """Fetches essential session and context data."""
    session_check_query = text(
        """
        SELECT cs.id, cs.child_id, cs.entry_point_type, cs.entry_point_context,
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
    return session_data


async def _get_conversation_history(
    db: AsyncSession, session_id: UUID
) -> list[prompt_models.Message]:
    """Fetches the recent conversation history for a session."""
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
    return [
        prompt_models.Message(role=row["role"].lower(), content=row["content"])
        for row in history_rows
    ]


async def _save_user_message(
    db: AsyncSession, session_id: UUID, user_message: UserMessageCreate
):
    """Saves the user's message to the database."""
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


def _process_memory_to_instructions(
    parent_memory: dict, child_memory: dict, current_subject: str, child_name: str
) -> tuple[list[str], list[str]]:
    """Convert structured memory into pedagogically sound instruction strings."""

    parent_instructions = []
    child_instructions = []

    # Process parent challenge subjects
    challenge_subjects = parent_memory.get("learning_context", {}).get(
        "challenge_subjects", []
    )
    if challenge_subjects:
        if current_subject.lower() in [s.lower() for s in challenge_subjects]:
            parent_instructions.append(
                f"IMPORTANT: This parent needs extra support with {current_subject}. "
                "Provide clearer step-by-step explanations, more encouragement, and practical examples."
            )
        else:
            subjects_str = ", ".join(challenge_subjects)
            parent_instructions.append(
                f"Note: This parent has indicated they need help with {subjects_str}."
            )

    # Process child interests with pedagogical balance
    child_interests = child_memory.get("interests", [])
    if child_interests:
        interests_str = ", ".join(child_interests)
        child_instructions.append(
            f"LEARNING BRIDGE: {child_name} is interested in {interests_str}. "
            "Use these as a starting point or bridge to introduce new concepts, but also gently "
            "expand into related areas to broaden their horizons. Balance familiar contexts with "
            "new discoveries - use their interests as a foundation, not a limitation."
        )

    return parent_instructions, child_instructions


def _calculate_request_word_count(llm_request_payload: dict) -> int:
    """Calculates the total word count of all messages in an LLM request payload."""
    word_count = 0
    if llm_request_payload and "messages" in llm_request_payload:
        for msg in llm_request_payload["messages"]:
            word_count += len(str(msg.get("content", "")).split())
    return word_count


async def _build_system_prompt(
    db: AsyncSession, user_id: int, session_data: dict[str, Any]
) -> str:
    """Constructs the detailed system prompt for the LLM."""
    prompt_generator = prompt_models.ConceptCoachPrompt()

    # Get all children for context AND their memory
    children_query = text(
        """
        SELECT
            c.id,
            c.name,
            c.memory,
            sy.year_name as school_year
        FROM children c
        LEFT JOIN school_years sy ON c.school_year_id = sy.id
        WHERE c.user_id = :user_id
        ORDER BY c.created_at ASC;
    """
    )
    children_result = await db.execute(children_query, {"user_id": user_id})
    children_rows = children_result.mappings().all()

    children_summary_list = [
        prompt_models.ChildSummary(name=row["name"], school_year=row["school_year"])
        for row in children_rows
    ]

    # Get parent memory
    parent_query = text("SELECT memory FROM users WHERE id = :user_id")
    parent_result = await db.execute(parent_query, {"user_id": user_id})
    parent_memory = parent_result.scalar_one_or_none() or {}

    # Find current child's memory from the children we already retrieved
    current_child_memory = {}
    for child_row in children_rows:
        if child_row["id"] == session_data["child_id"]:
            current_child_memory = child_row["memory"] or {}
            break

    # Get current subject for context
    current_subject = ""
    if session_data["entry_point_type"] == EntryPointType.CONCEPT_COACH.value:
        concept_id = session_data["entry_point_context"].get("concept_id")
        if concept_id:
            subject_query = text(
                "SELECT s.subject_name FROM concepts c JOIN subjects s ON c.subject_id = s.id WHERE c.id = :concept_id"
            )
            subject_result = await db.execute(subject_query, {"concept_id": concept_id})
            current_subject = subject_result.scalar_one_or_none() or ""

    # Process memory into instructions
    parent_instructions, child_instructions = _process_memory_to_instructions(
        parent_memory, current_child_memory, current_subject, session_data["child_name"]
    )

    parent_context = prompt_models.ParentContext(
        name=session_data["user_name"],
        children=children_summary_list,
        parent_notes_from_memory=parent_instructions,
    )
    child_context = prompt_models.ChildContext(
        name=session_data["child_name"],
        class_level=session_data["school_year"],
        notes_from_memory=child_instructions,
    )

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
            "current_session_id": session_data["id"],
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

    learning_context = None
    concept_id = None
    # TODO: This logic is specific to CONCEPT_COACH. In the future, we should
    # have different prompt builders for different entry point types.
    if session_data["entry_point_type"] == EntryPointType.CONCEPT_COACH.value:
        concept_id = session_data["entry_point_context"].get("concept_id")
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

    return prompt_generator.get_system_prompt(
        parent_context=parent_context,
        child_context=child_context,
        learning_context=learning_context,
    )


async def _save_assistant_message(
    db: AsyncSession,
    session_id: UUID,
    assistant_content: str,
    llm_usage_data: dict | None,
    context_snapshot: dict | None = None,
) -> dict[str, Any]:
    """Saves the assistant's response and updates the session timestamp."""
    assistant_insert_query = text(
        """
        INSERT INTO chat_messages (session_id, role, content, llm_usage, context_snapshot)
        VALUES (:session_id, :role, :content, :llm_usage, :context_snapshot)
        RETURNING *;
    """
    )

    # Enhance llm_usage_data with consistent fields for analytics
    # This now only contains metadata from the LLM response, not the request.
    enhanced_usage_data = llm_usage_data.copy() if llm_usage_data else {}
    enhanced_usage_data["response_length"] = len(assistant_content)
    enhanced_usage_data["response_word_count"] = len(assistant_content.split())

    # Calculate request word count from the snapshot for consistency
    if context_snapshot and "llm_request" in context_snapshot:
        enhanced_usage_data["request_word_count"] = _calculate_request_word_count(
            context_snapshot["llm_request"]
        )

    # TODO: Implement cost calculation based on model and token counts.
    enhanced_usage_data["cost"] = None

    result = await db.execute(
        assistant_insert_query,
        {
            "session_id": session_id,
            "role": ChatMessageRole.ASSISTANT.value,
            "content": assistant_content,
            "llm_usage": json.dumps(enhanced_usage_data),
            "context_snapshot": json.dumps(context_snapshot)
            if context_snapshot
            else None,
        },
    )
    assistant_message = result.mappings().first()
    if not assistant_message:
        raise DatabaseError("Failed to create assistant message.")

    update_session_query = text(
        """
        UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = :session_id
    """
    )
    await db.execute(update_session_query, {"session_id": session_id})

    return assistant_message


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
    # 1. Fetch session data and build prompt context
    session_data = await _get_session_data(db, session_id, user_id)
    system_prompt = await _build_system_prompt(db, user_id, session_data)

    # 2. Fetch conversation history
    conversation_history = await _get_conversation_history(db, session_id)

    # 3. Insert the new user message
    await _save_user_message(db, session_id, user_message)

    # 4. Prepare messages for LLM
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
    # Create the full request payload for the snapshot
    api_messages = [msg.model_dump() for msg in messages]
    if system_prompt:
        api_messages.insert(0, {"role": "system", "content": system_prompt})

    llm_request_payload = {
        "model": DEFAULT_CHAT_MODEL.value,
        "messages": api_messages,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": DEFAULT_MAX_TOKENS,
    }
    context_snapshot = {"llm_request": llm_request_payload}

    llm_response = await get_completion(
        ai_model=DEFAULT_CHAT_MODEL,
        system_prompt=system_prompt,
        messages=messages,
        response_type=None,  # We want a plain string response
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )
    assistant_content = llm_response.content
    if not isinstance(assistant_content, str):
        # Handle cases where the LLM might return unexpected structured data
        assistant_content = str(assistant_content)

    # 6. Save the assistant's response
    assistant_message = await _save_assistant_message(
        db,
        session_id,
        assistant_content,
        llm_response.usage_metadata,
        context_snapshot,
    )

    if not assistant_message:
        raise DatabaseError("Failed to create assistant message.")

    return assistant_message


async def create_message_and_stream_bot_response(
    db: AsyncSession,
    session_id: UUID,
    user_id: int,
    user_message: UserMessageCreate,
) -> AsyncGenerator[str, None]:
    """
    Creates a user message, constructs a detailed prompt, calls the LLM,
    streams the response, and then saves the final message to the database.
    """
    # 1. Fetch session data and build prompt context
    session_data = await _get_session_data(db, session_id, user_id)
    system_prompt = await _build_system_prompt(db, user_id, session_data)

    # 2. Fetch conversation history
    conversation_history = await _get_conversation_history(db, session_id)

    # 3. Insert the new user message - MOVED TO FINALLY BLOCK
    # await _save_user_message(db, session_id, user_message)

    # 4. Prepare messages for LLM
    conversation_history.append(
        prompt_models.Message(
            role=ChatMessageRole.USER.value, content=user_message.content
        )
    )
    messages = [
        LLMMessage(role=msg.role, content=msg.content) for msg in conversation_history
    ]

    # 5. Stream the LLM response and save it afterwards
    # Create the full request payload for the snapshot
    api_messages = [msg.model_dump() for msg in messages]
    if system_prompt:
        api_messages.insert(0, {"role": "system", "content": system_prompt})

    llm_request_payload = {
        "model": DEFAULT_CHAT_MODEL.value,
        "messages": api_messages,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "stream": True,
    }
    context_snapshot = {"llm_request": llm_request_payload}
    full_response = ""
    try:
        stream = get_completion_stream(
            ai_model=DEFAULT_CHAT_MODEL,
            system_prompt=system_prompt,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        async for chunk in stream:
            yield chunk
            full_response += chunk
    finally:
        # 6. Save the full assistant message after streaming is complete
        if full_response:
            # We must use a new session here because the original `db` session
            # from the request context will be closed by the time the stream finishes.
            async with AsyncSessionLocal() as session:
                try:
                    # Save both user and assistant messages in one transaction
                    await _save_user_message(session, session_id, user_message)

                    # We call a simplified save operation here because we don't get
                    # token usage data from the streaming endpoint.
                    # For streaming, we only know the final response length.
                    llm_usage_data = {
                        "response_length": len(full_response),
                        "response_word_count": len(full_response.split()),
                        "request_word_count": _calculate_request_word_count(
                            llm_request_payload
                        ),
                        # TODO: Implement cost calculation for streaming if possible,
                        # or estimate based on response length.
                        "cost": None,
                    }
                    assistant_insert_query = text(
                        """
                        INSERT INTO chat_messages (session_id, role, content, llm_usage, context_snapshot)
                        VALUES (:session_id, :role, :content, :llm_usage, :context_snapshot)
                        RETURNING id;
                    """
                    )
                    await session.execute(
                        assistant_insert_query,
                        {
                            "session_id": session_id,
                            "role": ChatMessageRole.ASSISTANT.value,
                            "content": full_response,
                            "llm_usage": json.dumps(llm_usage_data),
                            "context_snapshot": json.dumps(context_snapshot),
                        },
                    )
                    update_session_query = text(
                        """
                        UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = :session_id
                    """
                    )
                    await session.execute(
                        update_session_query, {"session_id": session_id}
                    )
                    await session.commit()
                    logger.info(
                        "Saved user message and streamed response to database",
                        session_id=session_id,
                    )
                except Exception as e:
                    await session.rollback()
                    logger.error(
                        "Failed to save user message and streamed response to database",
                        session_id=session_id,
                        error=str(e),
                    )


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
        WHERE m.id = :message_id AND s.id = :session_id AND s.user_id = :user_id AND m.role = 'assistant'
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
