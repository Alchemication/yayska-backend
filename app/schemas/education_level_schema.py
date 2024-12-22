from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EducationLevelBase(BaseModel):
    """Base schema for Education Level."""
    name: str
    description: Optional[str] = None


class EducationLevelCreate(EducationLevelBase):
    """Schema for creating an Education Level."""
    pass


class EducationLevel(EducationLevelBase):
    """Schema for retrieving an Education Level."""
    id: int
    created_on: datetime
    updated_on: Optional[datetime] = None
    deleted_on: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) 