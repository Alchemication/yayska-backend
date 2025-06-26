from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, conint


class EntryPointType(str, Enum):
    """Enum for chat entry points."""

    CONCEPT_COACH = "CONCEPT_COACH"
    # Future entry points can be added here
    # SUBJECT_ASSISTANT = "SUBJECT_ASSISTANT"
    # MONTHLY_PLANNER = "MONTHLY_PLANNER"


class ChatSessionFindOrCreate(BaseModel):
    """Schema for finding or creating a chat session."""

    child_id: int = Field(..., description="ID of the child for this chat session.")
    entry_point_type: EntryPointType = Field(
        ..., description="The context from which the chat was initiated."
    )
    context_data: dict[str, Any] = Field(
        ...,
        description="Data specific to the entry point, e.g., {'concept_id': 123}.",
        examples=[{"concept_id": 123}],
    )


class ChatSessionResponse(BaseModel):
    """Schema for a full chat session object response."""

    id: UUID
    user_id: int
    child_id: int
    title: str
    entry_point_type: str
    entry_point_context: dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ChatSessionListItem(BaseModel):
    """Schema for a single item in the chat session list."""

    id: UUID
    title: Optional[str]
    updated_at: Optional[datetime]


class ChatSessionListResponse(BaseModel):
    """Schema for the paginated list of chat sessions."""

    items: list[ChatSessionListItem]
    total: int


class ChatMessageRole(str, Enum):
    """Enum for message roles."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"


class UserMessageCreate(BaseModel):
    """Schema for creating a new user message."""

    content: str = Field(..., min_length=1, max_length=4096)


class ChatMessageResponse(BaseModel):
    """Schema for a chat message response."""

    id: UUID
    session_id: UUID
    role: ChatMessageRole
    content: str
    reasoning: Optional[str] = None
    context_snapshot: Optional[dict[str, Any]] = Field(default_factory=dict)
    llm_usage: Optional[dict[str, Any]] = Field(default_factory=dict)
    feedback_thumbs: Optional[int] = None
    feedback_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageFeedback(BaseModel):
    """Schema for providing feedback on a message."""

    vote: conint(ge=-1, le=1) = Field(..., description="Vote: 1 for up, -1 for down.")
    text: Optional[str] = Field(
        None, max_length=1024, description="Optional text feedback."
    )


class MessageFeedbackUpdate(BaseModel):
    """Schema for the PATCH request to update message feedback."""

    feedback: MessageFeedback
