"""Database utility functions for data import operations."""

import json
import logging
from pathlib import Path
from typing import Any, List

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_data(file_path: Path | str) -> list[dict[str, Any]]:
    """Load data from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        list[dict[str, Any]]: List of dictionaries containing the data

    Raises:
        FileNotFoundError: If the file doesn't exist
        JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("JSON file not found: %s", file_path)
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in file: %s", file_path)
        raise


def get_sync_database_url() -> str:
    """Convert async database URL to sync format.

    Returns:
        str: Synchronous database URL
    """
    return str(settings.DATABASE_URI).replace("postgresql+asyncpg://", "postgresql://")


def get_engine() -> Any:
    """Create and return a SQLAlchemy engine instance.

    Returns:
        Any: SQLAlchemy engine instance
    """
    return create_engine(
        get_sync_database_url(), connect_args=settings.get_sync_db_connect_args
    )


def execute_query(engine: Any, query: str) -> List[dict[str, Any]]:
    """Execute a query and return results as a list of dictionaries.

    Args:
        engine: SQLAlchemy engine instance
        query: SQL query to execute

    Returns:
        List[dict[str, Any]]: Query results as a list of dictionaries
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row) for row in result.mappings()]
    except SQLAlchemyError as e:
        logger.error("Error executing query: %s", str(e))
        raise


def truncate_table(engine: Any, table_name: str) -> None:
    """Truncate specified table.

    Args:
        engine: SQLAlchemy engine instance
        table_name: Name of the table to truncate
    """
    with engine.begin() as conn:
        try:
            conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
            logger.info("Truncated %s table", table_name)
        except SQLAlchemyError as e:
            logger.error("Error truncating %s table: %s", table_name, str(e))
            raise


def batch_insert(
    engine: Any, table_name: str, records: list[dict[str, Any]], batch_size: int = 100
) -> None:
    """Insert records in batches.

    Args:
        engine: SQLAlchemy engine instance
        table_name: Name of the table to insert into
        records: List of records to insert
        batch_size: Size of each batch
    """
    if not records:
        logger.warning("No records to insert")
        return

    # Create the INSERT query dynamically based on the first record's keys
    columns = list(records[0].keys())
    placeholders = [f":{col}" for col in columns]
    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
    """

    with engine.begin() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            try:
                conn.execute(text(insert_query), batch)
            except SQLAlchemyError as e:
                logger.error(
                    "Error inserting batch starting at index %d: %s", i, str(e)
                )
                raise
