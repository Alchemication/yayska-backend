import asyncio
import os
import ssl
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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


async def test_connection():
    ENV = os.getenv("ENVIRONMENT", "prod")

    env_file = Path(".env")
    print(f"Loading environment from: {env_file.absolute()}")

    load_dotenv(env_file, override=True)

    url = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connect_args = {"ssl": ssl_context} if ENV == "prod" else {}

    engine = create_async_engine(url, echo=True, connect_args=connect_args)

    try:
        async with engine.connect() as conn:
            # Test basic connection
            result = await conn.scalar(text("SELECT 1"))
            print("Connection successful!")
            print(f"Test query result: {result}")

            # Test listing tables
            result = await conn.execute(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            )
            rows = result.fetchall()  # No await needed here
            print("\nExisting tables:")
            for row in rows:
                print(f"- {row[0]}")

    except Exception as e:
        print(f"Connection failed: {e}")
        print(f"Error type: {type(e)}")
        import traceback

        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_connection())
