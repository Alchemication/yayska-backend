import socket

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_mapping={
            "GOOGLE_CLIENT_ID": ["GOOGLE_WEB_CLIENT_ID"],
            "GOOGLE_CLIENT_SECRET": ["GOOGLE_WEB_CLIENT_SECRET"],
        },
    )

    # App Settings
    ENVIRONMENT: str = "local"

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Yayska"
    SECRET_KEY: str

    # JWT Settings
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 365  # Long lived token for best UX
    REFRESH_TOKEN_EXPIRE_DAYS: int = 730  # 2 years for refresh token

    # OAuth Settings - Google Web
    GOOGLE_CLIENT_ID: str = ""  # Default fallback to environment variable
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8081/auth/google/callback"
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL: str = "https://www.googleapis.com/oauth2/v1/userinfo"

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

    @classmethod
    def load_from_env_file(cls):
        """Load settings from .env file in local development."""
        import os
        from pathlib import Path

        from dotenv import load_dotenv

        # Always load .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file, override=True)

        # Create the settings instance
        instance = cls()

        # Manually map the web client credentials if they're not set directly
        if not instance.GOOGLE_CLIENT_ID and os.environ.get("GOOGLE_WEB_CLIENT_ID"):
            instance.GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_WEB_CLIENT_ID")

        if not instance.GOOGLE_CLIENT_SECRET and os.environ.get(
            "GOOGLE_WEB_CLIENT_SECRET"
        ):
            instance.GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_WEB_CLIENT_SECRET")

        return instance


# Use the conditional loading
settings = Settings.load_from_env_file()
