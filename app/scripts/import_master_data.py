"""Script to import initial master data in the database.

This script loads predefined master data from a JSON file into the database tables.
It follows a specific order to maintain referential integrity and truncates existing
data before loading new data.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Table loading order to maintain referential integrity
TABLES_LOAD_ORDER = [
    "education_levels",
    "school_years",
    "curriculum_areas",
    "subjects",
    "strands",
    "strand_units",
    "learning_outcomes",
    "concepts",
    "quizzes",
    "concept_metadata",
]


def load_json_data() -> Dict[str, Any]:
    """Load master data from JSON file.

    Returns:
        Dict[str, Any]: Dictionary containing the master data
    """
    json_path = Path(__file__).parents[2] / "app" / "data" / "master_data.json"
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("Master data file not found: %s", json_path)
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in master data file")
        raise


def truncate_tables(engine: Any) -> None:
    """Truncate all tables in reverse order to handle foreign key constraints.

    Args:
        engine: SQLAlchemy engine instance
    """
    with engine.begin() as conn:
        # Temporarily disable foreign key checks for PostgreSQL
        conn.execute(text("SET CONSTRAINTS ALL DEFERRED"))

        # Truncate tables in reverse order
        for table in reversed(TABLES_LOAD_ORDER):
            try:
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                logger.info("Truncated table: %s", table)
            except SQLAlchemyError as e:
                logger.error("Error truncating table %s: %s", table, str(e))
                raise


def insert_data(engine: Any, data: Dict[str, Any]) -> None:
    """Insert data into tables in the correct order.

    Args:
        engine: SQLAlchemy engine instance
        data: Dictionary containing the data to insert
    """
    with engine.begin() as conn:
        for table in TABLES_LOAD_ORDER:
            if table not in data:
                logger.warning("No data found for table: %s", table)
                continue

            table_data = data[table]
            if not table_data:
                continue

            # Convert data list to tuple for bulk insert
            columns = table_data[0].keys()

            # Create named parameters for each row
            for idx, row in enumerate(table_data):
                # Convert the row data to use named parameters
                param_dict = {f"param_{k}_{idx}": v for k, v in row.items()}

                # Construct the INSERT statement with named parameters
                placeholders = [f":{f'param_{k}_{idx}'}" for k in columns]
                column_names = ",".join(columns)
                placeholder_str = ",".join(placeholders)

                insert_query = f"""
                    INSERT INTO {table} ({column_names})
                    VALUES ({placeholder_str})
                """

                try:
                    conn.execute(text(insert_query), param_dict)
                except SQLAlchemyError as e:
                    logger.error("Error inserting data into %s: %s", table, str(e))
                    raise


def get_sync_database_url() -> str:
    """Convert async database URL to sync format.

    Returns:
        str: Synchronous database URL
    """
    # Replace async driver with sync driver
    return str(settings.DATABASE_URI).replace("postgresql+asyncpg://", "postgresql://")


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine with synchronous URL and SSL if needed
        engine = create_engine(
            get_sync_database_url(), connect_args=settings.get_sync_db_connect_args
        )

        # Load JSON data
        logger.info("Loading master data from JSON file...")
        data = load_json_data()

        # Truncate existing data
        logger.info("Truncating existing data...")
        truncate_tables(engine)

        # Insert new data
        logger.info("Inserting new data...")
        insert_data(engine, data)

        logger.info("Master data initialization completed successfully")

    except Exception as e:
        logger.error("Failed to initialize master data: %s", str(e))
        raise


if __name__ == "__main__":
    main()
