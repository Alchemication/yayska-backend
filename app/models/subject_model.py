from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class SubjectModel(Base):
    """Model representing academic subjects."""

    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    updated_on = Column(DateTime, nullable=True)
    deleted_on = Column(DateTime, nullable=True)

    # Relationships
    strands = relationship("Strand", back_populates="subject")
