import os
import ssl
from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Clear any existing env vars before loading new ones
env_vars_to_clear = [
    "POSTGRES_SERVER",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_PORT",
    "ENVIRONMENT",
]

for var in env_vars_to_clear:
    if var in os.environ:
        del os.environ[var]

# Load environment file with override
ENV = os.getenv("ENVIRONMENT", "local")
env_file = Path(".env")
if env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(env_file, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
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

    @property
    def DATABASE_URI(self) -> PostgresDsn:
        """Builds database URI dynamically."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=int(self.POSTGRES_PORT),
            path=self.POSTGRES_DB,
        )


# Force settings reload by creating a new instance
settings = Settings()
