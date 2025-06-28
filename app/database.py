import asyncio
import logging
import ssl
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)


def get_connect_args():
    """Get connection arguments"""
    connect_args = {
        "timeout": 30,
        "command_timeout": 30,
    }

    if settings.ENVIRONMENT == "prod":
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args.update(
            {
                "ssl": ssl_context,
                "server_settings": {
                    "application_name": "fastapi_app",
                    "client_encoding": "utf8",
                },
            }
        )

        # Add Neon-specific parameters
        if settings.NEON_ENDPOINT_ID:
            connect_args["server_settings"]["neon.endpoint_id"] = (
                settings.NEON_ENDPOINT_ID
            )

    return connect_args


# Create engine with specific configuration for serverless
engine = create_async_engine(
    settings.DATABASE_URI,
    echo=settings.DB_ECHO_QUERIES,
    poolclass=NullPool,
    connect_args=get_connect_args(),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    for attempt in range(3):
        try:
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except HTTPException as http_exc:
                    await session.rollback()
                    raise http_exc
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database error: {str(e)}")
                    raise
                break
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt == 2:
                logger.error("All database connection attempts failed")
                raise
            await asyncio.sleep(1)
