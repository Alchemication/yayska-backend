from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserUpdate(BaseModel):
    """Schema for updating a user's memory."""

    memory: dict = Field(..., description="Arbitrary JSON data for user memory.")


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    picture_url: Optional[str] = None
    memory: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
