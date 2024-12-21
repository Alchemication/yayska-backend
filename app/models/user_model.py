from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True, index=True)
    email = mapped_column(String, unique=True, index=True, nullable=False)
