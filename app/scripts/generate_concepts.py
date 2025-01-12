"""Script to generate concepts in the database.

This script generates concepts for each learning outcome in the curriculum.

Ideally this could be developed as a batch job to save on costs.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from app.prompts.concepts import (
    ConceptsResponse,
    system_prompt,
    user_prompt,
)
from app.utils.db import execute_query, get_engine
from app.utils.llm import batch_process_with_llm, setup_llm_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_curriculum_data(engine: Any) -> list[Dict[str, Any]]:
    """Load curriculum data from the database.

    Returns:
        list[Dict[str, Any]]: List of dictionaries containing the curriculum data
    """
    school_years_query = (
        "SELECT DISTINCT id, year_name FROM school_years ORDER BY id ASC"
    )
    subjects_query = """
        SELECT 
            s.id AS subject_id,
            s.subject_name,
            s.introduction_year_id
        FROM subjects s
        ORDER BY 
            s.subject_name,
            s.introduction_year_id
    """

    school_years = execute_query(engine, school_years_query)
    subjects = execute_query(engine, subjects_query)

    # Create a dict where key is the year_id and value is the year_name
    year_dict = {year["id"]: year["year_name"] for year in school_years}

    # Get the max year_id
    max_year_id = max(year["id"] for year in school_years)

    # Multiply each subject by adding new property: year_name from school_years
    subjects_with_years = []
    for subject in subjects:
        start_year_id = subject["introduction_year_id"]
        for year in range(start_year_id, max_year_id + 1):
            subject_with_year = subject.copy()
            subject_with_year["year_name"] = year_dict[year]
            subjects_with_years.append(subject_with_year)

    return subjects_with_years


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine
        engine = get_engine()

        # Retrieve curriculum data
        logger.info("Loading curriculum data from database...")
        subjects = get_curriculum_data(engine)
        logger.info("Loaded %d subjects", len(subjects))

        # Set up LLM cache
        setup_llm_cache("concepts")

        # Generate concepts
        logger.info("Generating concepts...")
        concepts = batch_process_with_llm(
            data=subjects,
            response_type=ConceptsResponse,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Save outcomes to JSON file into the data folder
        json_path = Path(__file__).parents[2] / "app" / "data" / "concepts.json"
        with open(json_path, "w") as f:
            # Convert Pydantic objects to dictionaries using model_dump()
            serializable_concepts = [concept.model_dump() for concept in concepts]
            json.dump(serializable_concepts, f, indent=2)

        logger.info("Concepts generation completed successfully")

    except Exception as e:
        logger.error("Failed to generate concepts: %s", str(e))
        raise


if __name__ == "__main__":
    main()
