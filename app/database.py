import logging
import ssl
from typing import AsyncGenerator

import asyncpg
from sqlalchemy import text  # Add this import
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)


# Create a connection pool factory for asyncpg
async def create_pool():
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        pool = await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_SERVER,
            port=int(settings.POSTGRES_PORT),
            database=settings.POSTGRES_DB,
            ssl=ssl_context if settings.ENVIRONMENT == "prod" else None,
            min_size=1,
            max_size=1,  # Limit pool size for serverless
            command_timeout=10,
        )
        return pool
    except Exception as e:
        logger.error(f"Error creating connection pool: {e}")
        raise


# Create engine with minimal pooling for serverless
engine = create_async_engine(
    str(settings.DATABASE_URI),
    echo=settings.ENVIRONMENT == "local",
    poolclass=NullPool,  # Disable SQLAlchemy pooling
    connect_args=settings.get_db_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# Dependency with connection pool handling
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    for attempt in range(3):  # Try 3 times
        try:
            async with AsyncSessionLocal() as session:
                try:
                    # Test the connection with a simple query using text()
                    await session.execute(text("SELECT 1"))
                    yield session
                    await session.commit()
                    break
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database error: {e}")
                    raise
        except Exception as e:
            if attempt == 2:  # Last attempt
                logger.error(f"Failed to connect after 3 attempts: {e}")
                raise
            import asyncio

            await asyncio.sleep(1)  # Wait 1 second before retrying
