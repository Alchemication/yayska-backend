from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class SchoolYearModel(Base):
    """Model representing academic school years/classes."""

    __tablename__ = "school_years"

    id = Column(Integer, primary_key=True, autoincrement=True)
    education_level_id = Column(Integer, ForeignKey("education_levels.id"), nullable=False)
    name = Column(String(50), nullable=False)
    short_name = Column(String(20), nullable=False)
    order_sequence = Column(Integer, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    updated_on = Column(DateTime, nullable=True)
    deleted_on = Column(DateTime, nullable=True)

    # Relationships
    education_level = relationship("EducationLevel", back_populates="school_years")
    learning_outcomes = relationship("LearningOutcome", back_populates="school_year")
