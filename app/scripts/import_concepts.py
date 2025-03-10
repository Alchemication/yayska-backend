"""Script to import concepts into the database.

This script loads generated concepts from a JSON file into the concepts table.
It follows a specific order to maintain referential integrity and truncates existing
data before loading new data.
"""

from pathlib import Path
from typing import Any

from tqdm import tqdm

from app.utils.db import batch_insert, get_engine, load_json_data, truncate_table
from app.utils.logger import get_logger

logger = get_logger(__name__)


def prepare_concept_records(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare concept records for database insertion.

    Args:
        data: Raw data from JSON file

    Returns:
        list[dict[str, Any]]: List of prepared concept records
    """
    records = []
    for record in tqdm(data, desc="Preparing concepts"):
        for concept in record.get("concepts", []):
            records.append(
                {
                    "subject_id": concept["subject_id"],
                    "year_id": concept["year_id"],
                    "concept_name": concept["concept_name"],
                    "concept_description": concept["concept_description"],
                    "learning_objectives": concept["learning_objectives"],
                    "strand_reference": concept["strand_reference"],
                    "display_order": concept["display_order"],
                }
            )
    return records


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine
        engine = get_engine()

        # Load JSON data
        json_path = Path(__file__).parents[2] / "app" / "data" / "concepts.json"
        logger.info("Loading concepts data from JSON file...")
        data = load_json_data(json_path)

        # Truncate existing data
        logger.info("Truncating existing concepts data...")
        truncate_table(engine, "concept_metadata")
        truncate_table(engine, "concepts")

        # Prepare and insert records
        logger.info("Preparing and inserting concepts data...")
        records = prepare_concept_records(data)
        batch_insert(engine, "concepts", records)

        logger.info("Concepts import completed successfully")

    except Exception as e:
        logger.error("Failed to import concepts: %s", str(e))
        raise


if __name__ == "__main__":
    main()
