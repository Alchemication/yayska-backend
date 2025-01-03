from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# Create engine with appropriate configuration
engine = create_async_engine(
    str(settings.DATABASE_URI),
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
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
