import os
from collections.abc import AsyncGenerator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

# Construct async database URL (note the postgresql+asyncpg://)
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
ENV = os.getenv("ENVIRONMENT", "local")


@lru_cache()
def get_database_url():
    """Get database URL with appropriate configuration based on environment."""
    url = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

    # Configure SSL for production (Neon.tech) only
    if ENV == "prod":
        connect_args = {"ssl": True, "sslmode": "require"}
    else:
        connect_args = {}

    return url, connect_args


url, connect_args = get_database_url()
engine = create_async_engine(
    url,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args=connect_args,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)


AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
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
