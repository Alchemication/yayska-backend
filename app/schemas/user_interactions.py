import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class InteractionType(str, Enum):
    CONCEPT_STUDIED = "CONCEPT_STUDIED"
    AI_CHAT_ENGAGED = "AI_CHAT_ENGAGED"


class UserInteractionCreate(BaseModel):
    interaction_type: InteractionType
    interaction_context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class UserInteraction(UserInteractionCreate):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
