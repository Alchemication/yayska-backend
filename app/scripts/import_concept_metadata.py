"""Script to import concept metadata into the database.

This script loads generated concept metadata from a JSON file into the concept_metadata table.
"""

import json
from pathlib import Path
from typing import Any

from tqdm import tqdm

from app.utils.db import batch_insert, get_engine, load_json_data, truncate_table
from app.utils.logger import get_logger

logger = get_logger(__name__)


def prepare_metadata_records(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare concept metadata records for database insertion.

    Args:
        data: Raw data from JSON file

    Returns:
        List of prepared concept metadata records
    """
    records = []
    for record in tqdm(data, desc="Preparing concept metadata"):
        for concept in record.get("concepts", []):
            concept_id = concept["concept_id"]

            for tag in concept.get("tags", []):
                records.append(
                    {
                        "concept_id": concept_id,
                        "metadata_type": "tag",
                        "metadata_value": tag,
                    }
                )

            if "prerequisites" in concept:
                records.append(
                    {
                        "concept_id": concept_id,
                        "metadata_type": "prerequisites",
                        "metadata_value": json.dumps(concept["prerequisites"]),
                    }
                )

            if "follow_ups" in concept:
                records.append(
                    {
                        "concept_id": concept_id,
                        "metadata_type": "follow_ups",
                        "metadata_value": json.dumps(concept["follow_ups"]),
                    }
                )

    return records


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine
        engine = get_engine()

        # Load JSON data
        json_path = Path(__file__).parents[2] / "app" / "data" / "concept_metadata.json"
        logger.info("Loading concept metadata from JSON file", path=str(json_path))
        data = load_json_data(json_path)

        # Truncate existing data
        logger.info("Truncating existing concept metadata")
        truncate_table(engine, "concept_metadata")

        # Prepare and insert records
        logger.info("Preparing and inserting concept metadata")
        records = prepare_metadata_records(data)
        logger.info("Inserting concept metadata records", count=len(records))
        batch_insert(engine, "concept_metadata", records)

        logger.info("Concept metadata import completed successfully")

    except Exception as e:
        logger.error("Failed to import concept metadata", error=str(e))
        raise


if __name__ == "__main__":
    main()
