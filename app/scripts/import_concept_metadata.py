"""Script to import concept metadata     into the database.

This script loads predefined concept metadata from a JSON file into the concept_metadata table.
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_data() -> list[dict[str, Any]]:
    """Load concept metadata from JSON file.

    Returns:
        list[dict[str, Any]]: List of dictionaries containing the concept metadata
    """
    json_path = Path(__file__).parents[2] / "app" / "data" / "concept_metadata.json"
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("Concept metadata file not found: %s", json_path)
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in concept metadata file")
        raise


def truncate_tables(engine: Any) -> None:
    """Truncate concept_metadata table.

    Args:
        engine: SQLAlchemy engine instance
    """
    with engine.begin() as conn:
        try:
            # Truncate concept_metadata table
            conn.execute(
                text("TRUNCATE TABLE concept_metadata RESTART IDENTITY CASCADE")
            )
            logger.info("Truncated concept_metadata table")
        except SQLAlchemyError as e:
            logger.error("Error truncating concept_metadata table: %s", str(e))
            raise


def insert_concept_metadata(engine: Any, data: list[dict[str, Any]]) -> None:
    """Insert concept metadata into the database.


    Args:
        engine: SQLAlchemy engine instance
        data: List of dictionaries containing the concept metadata records
    """
    insert_query = """
        INSERT INTO concept_metadata (
            concept_id,
            why_important,
            difficulty_stats,
            parent_guide,
            real_world,
            learning_path,
            time_guide,
            assessment_approaches,
            irish_language_support
        ) VALUES (
            :concept_id,
            CAST(:why_important AS jsonb),
            CAST(:difficulty_stats AS jsonb),
            CAST(:parent_guide AS jsonb),
            CAST(:real_world AS jsonb),
            CAST(:learning_path AS jsonb),
            CAST(:time_guide AS jsonb),
            CAST(:assessment_approaches AS jsonb),
            CAST(:irish_language_support AS jsonb)
        )
    """

    with engine.begin() as conn:
        for record in tqdm(data, desc="Inserting concept metadata"):
            try:
                conn.execute(
                    text(insert_query),
                    {
                        "concept_id": record["concept_id"],
                        "why_important": json.dumps(record["why_important"]),
                        "difficulty_stats": json.dumps(record["difficulty_stats"]),
                        "parent_guide": json.dumps(record["parent_guide"]),
                        "real_world": json.dumps(record["real_world"]),
                        "learning_path": json.dumps(record["learning_path"]),
                        "time_guide": json.dumps(record["time_guide"]),
                        "assessment_approaches": json.dumps(
                            record["assessment_approaches"]
                        ),
                        "irish_language_support": json.dumps(
                            record["irish_language_support"]
                        ),
                    },
                )
            except SQLAlchemyError as e:
                logger.error(
                    "Error inserting concept_id %s: %s", record["concept_id"], str(e)
                )
                raise
            except KeyError as e:
                logger.error(
                    "Missing required field for concept_id %s: %s",
                    record.get("concept_id", "unknown"),
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
        # Create database engine with synchronous URL and SSL if needed
        engine = create_engine(
            get_sync_database_url(), connect_args=settings.get_sync_db_connect_args
        )

        # Load JSON data
        logger.info("Loading concept metadata data from JSON file...")
        data = load_json_data()

        # Truncate existing data
        logger.info("Truncating existing concept metadata data...")
        truncate_tables(engine)

        # Insert new data
        logger.info("Inserting new concept metadata data...")
        insert_concept_metadata(engine, data)

        logger.info("Concept metadata import completed successfully")

    except Exception as e:
        logger.error("Failed to import concept metadata: %s", str(e))
        raise


if __name__ == "__main__":
    main()
