import os
import ssl
from collections.abc import AsyncGenerator
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Clear any existing env vars that might interfere
env_vars_to_clear = [
    "POSTGRES_SERVER",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_PORT",
]

for var in env_vars_to_clear:
    if var in os.environ:
        del os.environ[var]

env_file = Path(".env")
load_dotenv(env_file, override=True)
ENV = os.getenv("ENVIRONMENT", "local")


@lru_cache()
def get_database_url():
    """Get database URL with appropriate configuration based on environment."""
    url = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

    # Configure SSL for production (Neon.tech) only
    if ENV == "prod":
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args = {"ssl": ssl_context}
    else:
        connect_args = {}

    return url, connect_args


url, connect_args = get_database_url()

# Create engine with appropriate configuration
engine = create_async_engine(
    url,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args=connect_args,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,  # Helps with connection drops
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
