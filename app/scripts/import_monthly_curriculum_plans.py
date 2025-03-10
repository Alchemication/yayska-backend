"""Script to import monthly curriculum plans into the database.

This script loads generated monthly curriculum plans from a JSON file into the monthly_curriculum_plans table.
"""

from pathlib import Path
from typing import Any

from tqdm import tqdm

from app.utils.db import batch_insert, get_engine, load_json_data, truncate_table
from app.utils.logger import get_logger

logger = get_logger(__name__)


def prepare_monthly_curriculum_plans(
    data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prepare monthly curriculum plans records for database insertion.

    Args:
        data: Raw data from JSON file

    Returns:
        list[dict[str, Any]]: List of prepared monthly curriculum plan records
    """
    if not data:
        logger.error("No data found in the JSON file")
        return []

    records = []
    # Each item in data is a yearly plan
    for yearly_plan in tqdm(data, desc="Preparing yearly plans"):
        year_id = yearly_plan["year_id"]

        # Process each month in the yearly plan
        for i, monthly_plan in enumerate(yearly_plan.get("monthly_plans", [])):
            # i+1 represents the month order (1-based index)
            month_order = i + 1

            # Verify all required fields are present
            if (
                "month" not in monthly_plan
                or "concepts" not in monthly_plan
                or "focus" not in monthly_plan
            ):
                logger.warning(
                    "Missing required fields in monthly plan",
                    year_id=year_id,
                    month=i + 1,
                )
                continue

            # Get concept IDs from the concepts object
            concepts = monthly_plan.get("concepts", {})
            essential_concept_ids = concepts.get("essential", [])
            important_concept_ids = concepts.get("important", [])
            supplementary_concept_ids = concepts.get("supplementary", [])

            # Ensure concept_ids are lists
            if not all(
                isinstance(ids, list)
                for ids in [
                    essential_concept_ids,
                    important_concept_ids,
                    supplementary_concept_ids,
                ]
            ):
                logger.warning(
                    "One or more concept_ids fields is not a list",
                    essential=essential_concept_ids,
                    important=important_concept_ids,
                    supplementary=supplementary_concept_ids,
                )
                continue

            records.append(
                {
                    "year_id": year_id,
                    "month_order": month_order,
                    "month_name": monthly_plan["month"],
                    "essential_concept_ids": essential_concept_ids,
                    "important_concept_ids": important_concept_ids,
                    "supplementary_concept_ids": supplementary_concept_ids,
                    "focus_statement": monthly_plan["focus"],
                }
            )

    logger.info("Prepared records for insertion", count=len(records))
    return records


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine
        engine = get_engine()

        # Load JSON data
        json_path = (
            Path(__file__).parents[2] / "app" / "data" / "monthly_curriculum_plans.json"
        )

        if not json_path.exists():
            logger.error("JSON file not found", path=str(json_path))
            return

        logger.info(
            "Loading monthly curriculum plans from JSON file", path=str(json_path)
        )
        data = load_json_data(json_path)
        logger.info("Loaded yearly plans from JSON", count=len(data))

        # Truncate existing data
        logger.info("Truncating existing monthly curriculum plans data")
        truncate_table(engine, "monthly_curriculum_plans")

        # Prepare and insert records
        logger.info("Preparing and inserting monthly curriculum plans data")
        records = prepare_monthly_curriculum_plans(data)

        if not records:
            logger.error("No records to insert")
            return

        logger.info("Inserting records into database", count=len(records))
        batch_insert(engine, "monthly_curriculum_plans", records)

        logger.info("Monthly curriculum plans import completed successfully")

    except Exception as e:
        logger.error("Failed to import monthly curriculum plans", error=str(e))
        raise


if __name__ == "__main__":
    main()
