from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Enum for event types organized by category"""

    # Authentication & User Management
    USER_LOGIN = "USER_LOGIN"
    USER_REGISTRATION = "USER_REGISTRATION"
    USER_LOGOUT = "USER_LOGOUT"
    LOGIN_ATTEMPT = "LOGIN_ATTEMPT"
    LOGIN_FAILED = "LOGIN_FAILED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"

    # Onboarding Flow
    ONBOARDING_STARTED = "ONBOARDING_STARTED"
    ONBOARDING_COMPLETION_ATTEMPT = "ONBOARDING_COMPLETION_ATTEMPT"
    ONBOARDING_COMPLETED = "ONBOARDING_COMPLETED"
    ONBOARDING_FAILED = "ONBOARDING_FAILED"
    CHILD_YEAR_SELECTED = "CHILD_YEAR_SELECTED"

    # Content Engagement
    CONCEPT_CLICKED = "CONCEPT_CLICKED"
    CONCEPT_VIEW = "CONCEPT_VIEW"
    CONCEPT_SECTION_SWITCHED = "CONCEPT_SECTION_SWITCHED"
    CONCEPT_LOAD_ERROR = "CONCEPT_LOAD_ERROR"
    CONCEPT_STUDIED_15_SEC = "CONCEPT_STUDIED_15_SEC"

    # Navigation & User Behavior
    CHILD_SWITCHED = "CHILD_SWITCHED"
    SUBJECT_EXPANDED = "SUBJECT_EXPANDED"
    MONTHLY_CURRICULUM_NAVIGATION = "MONTHLY_CURRICULUM_NAVIGATION"
    NAVIGATION = "NAVIGATION"
    SESSION_STARTED = "SESSION_STARTED"

    # Content Loading
    CURRICULUM_LOADED = "CURRICULUM_LOADED"

    # AI Chat & Interaction
    CHAT_INITIATED = "CHAT_INITIATED"
    CHAT_INITIATION_FAILED = "CHAT_INITIATION_FAILED"
    CHAT_SESSION_LOADED = "CHAT_SESSION_LOADED"
    CHAT_SESSION_ENDED = "CHAT_SESSION_ENDED"
    CHAT_LOAD_ERROR = "CHAT_LOAD_ERROR"
    CHAT_MESSAGE_SENT = "CHAT_MESSAGE_SENT"
    CHAT_SEND_ERROR = "CHAT_SEND_ERROR"
    CHAT_RESPONSE_RECEIVED = "CHAT_RESPONSE_RECEIVED"
    CHAT_FEEDBACK_GIVEN = "CHAT_FEEDBACK_GIVEN"
    CHAT_FEEDBACK_ERROR = "CHAT_FEEDBACK_ERROR"

    # System Events - Keep for server-side usage
    ERROR_OCCURRED = "ERROR_OCCURRED"
    API_CALL = "API_CALL"


class Source(str, Enum):
    """Enum for event sources to ensure consistency"""

    WEB = "web"
    ANDROID = "android"
    IOS = "ios"
    SERVER = "server"
    API = "api"


class EventCreate(BaseModel):
    """Schema for creating a new event"""

    event_type: EventType = Field(..., description="Type of event from predefined enum")
    payload: Optional[dict[str, Any]] = Field(
        None, description="Flexible JSON payload for event-specific data"
    )
    session_id: Optional[str] = Field(
        None, max_length=255, description="Optional session identifier"
    )
    source: Optional[Source] = Field(
        Source.WEB,
        description="Source of the event (defaults to web for client events)",
    )


class EventResponse(BaseModel):
    """Schema for event response"""

    id: int
    created_at: str
    user_id: int
    event_type: str
    payload: Optional[dict[str, Any]]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    source: str
