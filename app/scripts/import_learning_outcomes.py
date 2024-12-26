"""Script to import learning outcomes in the database.

This script loads predefined learning outcomes from a JSON file into the database tables.
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


def load_json_data() -> Dict[str, Any]:
    """Load learning outcomes from JSON file.

    Returns:
        Dict[str, Any]: Dictionary containing the learning outcomes
    """
    json_path = Path(__file__).parents[2] / "app" / "data" / "learning_outcomes.json"
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("Learning outcomes file not found: %s", json_path)
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in learning outcomes file")
        raise


def truncate_tables(engine: Any) -> None:
    """Truncate all tables in reverse order to handle foreign key constraints.

    Args:
        engine: SQLAlchemy engine instance
    """
    with engine.begin() as conn:
        try:
            conn.execute(text("TRUNCATE TABLE learning_outcomes CASCADE"))
            logger.info("Truncated learning outcomes table")
        except SQLAlchemyError as e:
            logger.error("Error truncating learning outcomes table: %s", str(e))
            raise


def insert_data(engine: Any, data: Dict[str, Any]) -> None:
    """Insert data into learning outcomes table.

    Args:
        engine: SQLAlchemy engine instance
        data: Dictionary containing the data to insert
    """
    insert_query = """
        INSERT INTO learning_outcomes 
            (unit_id, year_id, outcome_description, prerequisite_knowledge, complexity_level)
        VALUES 
            (:unit_id, :year_id, :outcome_description, :prerequisite_knowledge, :complexity_level)
    """
    with engine.begin() as conn:
        for strand_unit_outcomes in data:
            for outcome_data in strand_unit_outcomes["learning_outcomes"]:
                try:
                    conn.execute(
                        text(insert_query),
                        {
                            "unit_id": outcome_data["unit_id"],
                            "year_id": outcome_data["year_id"],
                            "outcome_description": outcome_data["description"],
                            "prerequisite_knowledge": outcome_data["prerequisites"],
                            "complexity_level": outcome_data["complexity_level"],
                        },
                    )
                    logger.info(
                        "Inserted learning outcome for unit: %s",
                        outcome_data["unit_id"],
                    )
                except SQLAlchemyError as e:
                    logger.error("Error inserting learning outcome: %s", str(e))
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
        # Create database engine with synchronous URL
        engine = create_engine(get_sync_database_url())

        # Load JSON data
        logger.info("Loading master data from JSON file...")
        data = load_json_data()

        # Truncate existing data
        logger.info("Truncating existing data...")
        truncate_tables(engine)

        # Insert new data
        logger.info("Inserting new data...")
        insert_data(engine, data)

        logger.info("Learning outcomes import completed successfully")

    except Exception as e:
        logger.error("Failed to import learning outcomes: %s", str(e))
        raise


if __name__ == "__main__":
    main()
