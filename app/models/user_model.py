from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from app.database import Base


class UserModel(Base):
    """User model for storing user related details"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    created_on = Column(DateTime, nullable=False, default=datetime.now)
    updated_on = Column(DateTime, nullable=True, onupdate=datetime.now)
    deleted_on = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_on is not None
