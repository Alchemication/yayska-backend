from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EducationLevelModel(Base):
    """Model representing education levels in the system.

    Attributes:
        id: Primary key
        name: The name of the education level (e.g., "Bachelor's Degree", "Master's Degree")
        description: Detailed description of the education level
        created_on: Timestamp when the record was created
        updated_on: Timestamp when the record was last updated
        deleted_on: Timestamp when the record was soft deleted
    """

    __tablename__ = "education_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_on: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
