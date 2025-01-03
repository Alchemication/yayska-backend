import socket
import ssl
from functools import lru_cache

import structlog
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        # Remove env_file configuration so it only uses environment variables
        # env_file=".env",
        # env_file_encoding="utf-8",
    )

    # App Settings
    ENVIRONMENT: str = "local"

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Yayska"
    SECRET_KEY: str

    # PostgreSQL Settings
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str = "5432"

    # Third Party Services
    ANTHROPIC_API_KEY: str

    # Model Names
    ANTHROPIC_CLAUDE_3_5_HAIKU: str = "claude-3-5-haiku-20241022"
    ANTHROPIC_CLAUDE_3_5_SONNET: str = "claude-3-5-sonnet-20241022"

    @property
    def get_db_connect_args(self) -> dict:
        """Get database connection arguments based on environment (for async)."""
        if self.ENVIRONMENT == "prod":
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return {"ssl": ssl_context}
        return {}

    @property
    def get_sync_db_connect_args(self) -> dict:
        """Get database connection arguments based on environment (for sync)."""
        if self.ENVIRONMENT == "prod":
            return {"sslmode": "require"}
        return {}

    @lru_cache()
    def _resolve_db_host(self) -> str:
        """Resolve database hostname to IP address."""
        if self.ENVIRONMENT == "prod":
            try:
                return socket.gethostbyname(self.POSTGRES_SERVER)
            except Exception as e:
                logger.error(f"Failed to resolve database hostname: {str(e)}")
                return self.POSTGRES_SERVER
        return self.POSTGRES_SERVER

    @property
    def DATABASE_URI(self) -> PostgresDsn:
        """Builds database URI dynamically."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self._resolve_db_host(),  # Use resolved IP
            port=int(self.POSTGRES_PORT),
            path=self.POSTGRES_DB,
        )

    # Optional: Add a method to load .env file only in local development
    @classmethod
    def load_from_env_file(cls):
        """Load settings from .env file in local development."""
        import os
        from pathlib import Path

        from dotenv import load_dotenv

        if os.getenv("ENVIRONMENT") != "prod":
            env_file = Path(".env")
            if env_file.exists():
                load_dotenv(env_file, override=True)
        return cls()


# Use the conditional loading
settings = Settings.load_from_env_file()
