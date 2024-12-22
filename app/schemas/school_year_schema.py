from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SchoolYearBase(BaseModel):
    education_level_id: int
    name: str
    short_name: str
    order_sequence: int


class SchoolYearCreate(SchoolYearBase):
    pass


class SchoolYear(SchoolYearBase):
    id: int
    created_on: datetime
    updated_on: Optional[datetime] = None
    deleted_on: Optional[datetime] = None

    class Config:
        from_attributes = True 