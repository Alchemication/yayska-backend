import json

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import DatabaseError
from app.schemas.events import EventCreate, EventResponse
from app.utils.deps import CurrentUser

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new event"""

    # Extract metadata from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Convert payload to JSON string for PostgreSQL JSONB
    payload_json = (
        json.dumps(event_data.payload) if event_data.payload is not None else None
    )

    query = text("""
        INSERT INTO events (
            created_at, 
            user_id, 
            event_type, 
            payload, 
            session_id, 
            ip_address, 
            user_agent, 
            source
        )
        VALUES (
            CURRENT_TIMESTAMP, 
            :user_id, 
            :event_type, 
            :payload, 
            :session_id, 
            :ip_address, 
            :user_agent, 
            :source
        )
        RETURNING id, created_at, user_id, event_type, payload, session_id, ip_address, user_agent, source
    """)

    try:
        result = await db.execute(
            query,
            {
                "user_id": current_user["id"],
                "event_type": event_data.event_type.value,
                "payload": payload_json,
                "session_id": event_data.session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "source": event_data.source.value,
            },
        )
        await db.commit()

        event_row = result.mappings().first()
        if not event_row:
            raise DatabaseError(
                "Failed to create event - no data returned", operation="create_event"
            )

        return EventResponse(
            id=event_row["id"],
            created_at=event_row["created_at"].isoformat(),
            user_id=event_row["user_id"],
            event_type=event_row["event_type"],
            payload=event_row["payload"],
            session_id=event_row["session_id"],
            ip_address=str(event_row["ip_address"])
            if event_row["ip_address"]
            else None,
            user_agent=event_row["user_agent"],
            source=event_row["source"],
        )

    except DatabaseError:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            "Database error in create_event",
            error=str(e),
            error_type=type(e).__name__,
            user_id=current_user["id"],
            event_type=event_data.event_type.value,
        )
        raise DatabaseError(
            f"Failed to create event: {str(e)}", operation="create_event"
        )
