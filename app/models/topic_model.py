from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, 
    Boolean, Enum as SQLEnum, DateTime
)
from sqlalchemy.orm import relationship
from enum import Enum

from app.database import Base


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearningStyle(str, Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    MIXED = "mixed"


class TopicModel(Base):
    """Model representing detailed topics within learning outcomes."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learning_outcome_id = Column(Integer, ForeignKey("learning_outcomes.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    sequence_order = Column(Integer, nullable=False)
    difficulty_level = Column(
        SQLEnum(DifficultyLevel),
        nullable=False,
        default=DifficultyLevel.BEGINNER
    )
    prerequisites = Column(Text, nullable=True)  # Stored as JSON string
    teaching_methodology = Column(Text, nullable=True)
    required_resources = Column(Text, nullable=True)  # Stored as JSON string
    learning_style = Column(
        SQLEnum(LearningStyle),
        nullable=False,
        default=LearningStyle.MIXED
    )
    assessment_type = Column(String(50), nullable=True)
    practice_time_recommended = Column(Integer, nullable=True)
    is_core = Column(Boolean, nullable=False, default=True)
    curriculum_notes = Column(Text, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    updated_on = Column(DateTime, nullable=True)
    deleted_on = Column(DateTime, nullable=True)

    # Relationships
    learning_outcome = relationship("LearningOutcome", back_populates="topics") 