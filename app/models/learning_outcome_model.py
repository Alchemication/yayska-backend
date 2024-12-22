from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class LearningOutcomeModel(Base):
    """Model representing learning outcomes for specific strands and school years."""

    __tablename__ = "learning_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strand_id = Column(Integer, ForeignKey("strands.id"), nullable=False)
    school_year_id = Column(Integer, ForeignKey("school_years.id"), nullable=False)
    description = Column(Text, nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    updated_on = Column(DateTime, nullable=True)
    deleted_on = Column(DateTime, nullable=True)

    # Relationships
    strand = relationship("Strand", back_populates="learning_outcomes")
    school_year = relationship("SchoolYear", back_populates="learning_outcomes")
    topics = relationship("Topic", back_populates="learning_outcome")
