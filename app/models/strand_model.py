from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class StrandModel(Base):
    """Model representing curriculum strands within subjects."""

    __tablename__ = "strands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    updated_on = Column(DateTime, nullable=True)
    deleted_on = Column(DateTime, nullable=True)

    # Relationships
    subject = relationship("Subject", back_populates="strands")
    learning_outcomes = relationship("LearningOutcome", back_populates="strand")
