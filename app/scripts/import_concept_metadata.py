"""Script to import concept metadata into the database.

This script loads predefined concept metadata from a JSON file into the concept_metadata table.
"""

import json
import logging
from pathlib import Path
from typing import Any

from tqdm import tqdm

from app.utils.db import batch_insert, get_engine, load_json_data, truncate_table

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_metadata_records(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare concept metadata records for database insertion.

    Args:
        data: Raw data from JSON file

    Returns:
        list[dict[str, Any]]: List of prepared concept metadata records
    """
    records = []
    for record in tqdm(data, desc="Preparing concept metadata"):
        records.append(
            {
                "concept_id": record["concept_id"],
                "why_important": json.dumps(record["why_important"]),
                "difficulty_stats": json.dumps(record["difficulty_stats"]),
                "parent_guide": json.dumps(record["parent_guide"]),
                "real_world": json.dumps(record["real_world"]),
                "learning_path": json.dumps(record["learning_path"]),
                "time_guide": json.dumps(record["time_guide"]),
                "assessment_approaches": json.dumps(record["assessment_approaches"]),
                "irish_language_support": json.dumps(record["irish_language_support"]),
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
        logger.info("Loading concept metadata data from JSON file...")
        data = load_json_data(json_path)

        # Truncate existing data
        logger.info("Truncating existing concept metadata data...")
        truncate_table(engine, "concept_metadata")

        # Prepare and insert records
        logger.info("Preparing and inserting concept metadata data...")
        records = prepare_metadata_records(data)
        batch_insert(engine, "concept_metadata", records)

        logger.info("Concept metadata import completed successfully")

    except Exception as e:
        logger.error("Failed to import concept metadata: %s", str(e))
        raise


if __name__ == "__main__":
    main()
