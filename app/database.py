from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = structlog.get_logger()


def get_connection_string():
    """Get database connection string with appropriate driver."""
    if settings.ENVIRONMENT == "prod":
        # Construct Neon connection string
        return f"postgresql+neon://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    return str(settings.DATABASE_URI)


# Create engine with appropriate configuration
engine = create_async_engine(
    get_connection_string(),
    echo=settings.ENVIRONMENT == "local",
    connect_args=settings.get_db_connect_args,
    # Remove pool settings for serverless environment
    # pool_size=5,
    # max_overflow=10,
    # pool_timeout=30,
    poolclass=NullPool,  # Use NullPool for serverless
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# Dependency
# Dependency with retries
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    for attempt in range(3):  # Try 3 times
        try:
            async with AsyncSessionLocal() as session:
                try:
                    # Test the connection
                    await session.execute("SELECT 1")
                    yield session
                    await session.commit()
                    break  # If successful, break the retry loop
                except Exception:
                    await session.rollback()
                    raise
        except Exception as e:
            if attempt == 2:  # Last attempt
                logger.error(f"Database connection error: {str(e)}", exc_info=True)
                raise  # Re-raise the last exception
            import asyncio

            logger.warning(f"Database connection error: {str(e)}", exc_info=True)

            await asyncio.sleep(1)  # Wait 1 second before retrying
