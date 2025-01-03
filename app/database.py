import asyncio
import logging
import ssl
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)


def get_ssl_context():
    """Create SSL context for database connection"""
    if settings.ENVIRONMENT == "prod":
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    return None


# Create engine with specific configuration for serverless
engine = create_async_engine(
    str(settings.DATABASE_URI),
    echo=settings.ENVIRONMENT == "local",
    poolclass=NullPool,
    connect_args={
        "ssl": get_ssl_context(),
        "timeout": 30,  # Increased timeout
        "command_timeout": 30,
        "server_settings": {
            "statement_timeout": "30000",  # 30 seconds
            "idle_in_transaction_session_timeout": "30000",  # 30 seconds
        },
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
    retries = 3
    retry_delay = 1  # seconds

    for attempt in range(retries):
        try:
            session = AsyncSessionLocal()
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
            break  # Success, exit the retry loop
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt == retries - 1:  # Last attempt
                logger.error("All database connection attempts failed")
                raise
            await asyncio.sleep(retry_delay)  # Wait before retrying
