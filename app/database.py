import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# Create synchronous engine
engine = create_engine(
    settings.SYNC_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=0,
    connect_args={
        "connect_timeout": 10,
        "sslmode": "require" if settings.ENVIRONMENT == "prod" else None,
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
