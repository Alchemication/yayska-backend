from typing import Optional

from pydantic import BaseModel, Field


class ChildBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    school_year_id: int = Field(..., description="Reference to school_years table")
    memory: dict = Field(default_factory=dict)


class ChildCreate(ChildBase):
    """Schema for creating a new child"""

    pass


class ChildUpdate(BaseModel):
    """Schema for updating a child"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    school_year_id: Optional[int] = Field(None)
    memory: dict


class ChildResponse(ChildBase):
    """Schema for child response"""

    id: int
    user_id: int
    created_at: str
    updated_at: str | None

    # Include school year details
    school_year_name: str


class ChildrenListResponse(BaseModel):
    """Schema for listing children"""

    children: list[ChildResponse]
