import socket

import structlog
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
    ANTHROPIC_CLAUDE_3_7_SONNET: str = "claude-3-7-sonnet-20250219"

    @property
    def get_db_connect_args(self) -> dict:
        """Minimal connection arguments for SQLAlchemy."""
        return {"timeout": 10.0}

    @property
    def get_sync_db_connect_args(self) -> dict:
        """Get database connection arguments based on environment (for sync)."""
        if self.ENVIRONMENT == "prod":
            return {"sslmode": "require"}
        return {}

    def _resolve_db_host(self) -> str:
        """Resolve database hostname to IP address."""
        if self.ENVIRONMENT == "prod":
            try:
                return socket.gethostbyname(self.POSTGRES_SERVER)
            except Exception as e:
                print(f"DNS resolution failed: {e}")
                return self.POSTGRES_SERVER
        return self.POSTGRES_SERVER

    @property
    def DATABASE_URI(self) -> str:
        """Builds database URI dynamically."""
        if self.ENVIRONMENT == "prod":
            # For production, use the full connection string format without options
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            # For local development
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

    @property
    def NEON_ENDPOINT_ID(self) -> str:
        """Extract Neon endpoint ID from server name."""
        if self.ENVIRONMENT == "prod":
            return self.POSTGRES_SERVER.split(".")[0]
        return ""

    # Optional: Add a method to load .env file only in local development
    @classmethod
    def load_from_env_file(cls):
        """Load settings from .env file in local development."""
        from pathlib import Path

        from dotenv import load_dotenv

        # Always load .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file, override=True)
        return cls()


# Use the conditional loading
settings = Settings.load_from_env_file()
