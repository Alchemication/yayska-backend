"""Script to import concepts into the database.

This script loads predefined concepts from a JSON file into the concepts table.
It follows a specific order to maintain referential integrity and truncates existing
data before loading new data.
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_data() -> list[dict[str, Any]]:
    """Load concepts from JSON file.

    Returns:
        list[dict[str, Any]]: List of dictionaries containing the concepts data
    """
    json_path = Path(__file__).parents[2] / "app" / "data" / "concepts.json"
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("Concepts file not found: %s", json_path)
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in concepts file")
        raise


def truncate_tables(engine: Any) -> None:
    """Truncate concepts table in reverse order to handle foreign key constraints.

    Args:
        engine: SQLAlchemy engine instance
    """
    with engine.begin() as conn:
        try:
            # First truncate dependent tables if they exist
            conn.execute(
                text("TRUNCATE TABLE concept_metadata RESTART IDENTITY CASCADE")
            )
            conn.execute(text("TRUNCATE TABLE quizzes RESTART IDENTITY CASCADE"))
            # Then truncate concepts table
            conn.execute(text("TRUNCATE TABLE concepts RESTART IDENTITY CASCADE"))
            logger.info("Truncated concepts and related tables")
        except SQLAlchemyError as e:
            logger.error("Error truncating tables: %s", str(e))
            raise


def insert_concepts(engine: Any, data: list[dict[str, Any]]) -> None:
    """Insert concepts into the database.

    Args:
        engine: SQLAlchemy engine instance
        data: List of dictionaries containing the concepts data
    """
    insert_query = """
        INSERT INTO concepts 
            (outcome_id, concept_name, concept_description, difficulty_level)
        VALUES 
            (:outcome_id, :concept_name, :concept_description, :difficulty_level)
    """

    with engine.begin() as conn:
        for record in data:
            concepts = record.get("concepts", [])
            for concept in concepts:
                try:
                    conn.execute(
                        text(insert_query),
                        {
                            "outcome_id": concept["learning_outcome_id"],
                            "concept_name": concept["concept_name"],
                            "concept_description": concept["concept_description"],
                            "difficulty_level": concept["complexity_level"],
                        },
                    )
                except SQLAlchemyError as e:
                    logger.error(
                        "Error inserting concept %s: %s",
                        concept["concept_name"],
                        str(e),
                    )
                    raise


def get_sync_database_url() -> str:
    """Convert async database URL to sync format.

    Returns:
        str: Synchronous database URL
    """
    return str(settings.DATABASE_URI).replace("postgresql+asyncpg://", "postgresql://")


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine with synchronous URL
        engine = create_engine(get_sync_database_url())

        # Load JSON data
        logger.info("Loading concepts data from JSON file...")
        data = load_json_data()

        # Truncate existing data
        logger.info("Truncating existing concepts data...")
        truncate_tables(engine)

        # Insert new data
        logger.info("Inserting new concepts data...")
        insert_concepts(engine, data)

        logger.info("Concepts import completed successfully")

    except Exception as e:
        logger.error("Failed to import concepts: %s", str(e))
        raise


if __name__ == "__main__":
    main()
