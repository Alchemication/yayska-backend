import logging
import ssl
from typing import AsyncGenerator

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
pool = None


async def get_connection_pool():
    global pool
    if pool is None:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            pool = await asyncpg.create_pool(
                dsn=str(settings.DATABASE_URI),
                min_size=1,
                max_size=1,
                ssl=ssl_context if settings.ENVIRONMENT == "prod" else None,
                command_timeout=10,
                connection_timeout=10,
            )
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    return pool


# Create engine with specific configuration for serverless
engine = create_async_engine(
    str(settings.DATABASE_URI),
    echo=settings.ENVIRONMENT == "local",
    poolclass=NullPool,
    connect_args={
        "ssl": settings.ENVIRONMENT == "prod",
        "connect_timeout": 10,
        "command_timeout": 10,
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()
