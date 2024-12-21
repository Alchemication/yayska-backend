from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_on = Column(DateTime, default=lambda: datetime.now())
    deleted_on = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_on is not None
