"""Script to generate concepts for the database.

This script generates concepts for each learning outcome in the curriculum.

Ideally this could be developed as a batch job to save on costs.
"""

import json
from pathlib import Path
from typing import Any

from app.prompts.concepts import (
    ConceptsResponse,
    system_prompt,
    user_prompt,
)
from app.utils.db import execute_query, get_engine
from app.utils.llm import batch_process_with_llm, setup_llm_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_curriculum_data(engine: Any) -> list[dict[str, Any]]:
    """Load curriculum data from the database.

    Args:
        engine: Database engine instance

    Returns:
        List of dictionaries containing the curriculum data
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
        ORDER BY s.subject_name ASC
    """
    strand_units_query = """
        SELECT
            su.id AS strand_unit_id,
            s.id AS strand_id,
            s.strand_name,
            su.subject_id,
            su.strand_unit_name,
            su.description
        FROM strand_units su
        JOIN strands s ON su.strand_id = s.id
        ORDER BY 
            s.strand_name ASC,
            su.strand_unit_name ASC
    """
    learning_outcomes_query = """
        SELECT 
            lo.id AS learning_outcome_id,
            lo.strand_unit_id,
            lo.year_id,
            lo.learning_outcome,
            lo.display_order
        FROM learning_outcomes lo
        ORDER BY 
            lo.strand_unit_id ASC,
            lo.year_id ASC,
            lo.display_order ASC
    """

    # Execute all queries
    school_years = execute_query(engine, school_years_query)
    subjects = execute_query(engine, subjects_query)
    strand_units = execute_query(engine, strand_units_query)
    learning_outcomes = execute_query(engine, learning_outcomes_query)

    # Combine the data
    curriculum_data = []
    for subject in subjects:
        subject_id = subject["subject_id"]
        subject_name = subject["subject_name"]
        introduction_year_id = subject["introduction_year_id"]

        # Filter strand units for this subject
        subject_strand_units = [
            su for su in strand_units if su["subject_id"] == subject_id
        ]

        # Group by school year
        for year in school_years:
            year_id = year["id"]
            year_name = year["year_name"]

            # Skip years before subject introduction
            if year_id < introduction_year_id:
                continue

            # Collect learning outcomes for this subject and year
            year_learning_outcomes = []
            for strand_unit in subject_strand_units:
                strand_unit_id = strand_unit["strand_unit_id"]

                # Filter learning outcomes for this strand unit and year
                unit_outcomes = [
                    lo
                    for lo in learning_outcomes
                    if lo["strand_unit_id"] == strand_unit_id
                    and lo["year_id"] == year_id
                ]

                if unit_outcomes:
                    year_learning_outcomes.append(
                        {
                            "strand_name": strand_unit["strand_name"],
                            "strand_unit_name": strand_unit["strand_unit_name"],
                            "outcomes": unit_outcomes,
                        }
                    )

            # Only add if there are learning outcomes for this year
            if year_learning_outcomes:
                curriculum_data.append(
                    {
                        "subject_id": subject_id,
                        "subject_name": subject_name,
                        "year_id": year_id,
                        "year_name": year_name,
                        "strand_units": year_learning_outcomes,
                    }
                )

    return curriculum_data


def main() -> None:
    """Main function to execute the concept generation process."""
    try:
        # Create database engine
        engine = get_engine()

        # Retrieve curriculum data
        logger.info("Loading curriculum data from database")
        curriculum_data = get_curriculum_data(engine)
        logger.info("Loaded curriculum data entries", count=len(curriculum_data))

        # Set up LLM cache
        setup_llm_cache("concepts")

        # Prepare all prompts
        formatted_prompts = []
        for item in curriculum_data:
            # Format the learning outcomes
            formatted_outcomes = []
            for unit in item["strand_units"]:
                formatted_outcomes.append(f"Strand: {unit['strand_name']}")
                formatted_outcomes.append(f"Strand Unit: {unit['strand_unit_name']}")

                for outcome in unit["outcomes"]:
                    formatted_outcomes.append(
                        f"Learning Outcome: {outcome['learning_outcome']}"
                    )

                formatted_outcomes.append("")  # Add empty line between units

            outcomes_text = "\n".join(formatted_outcomes)

            # Create the formatted prompt
            prompt = user_prompt.format(
                subject=item["subject_name"],
                year=item["year_name"],
                learning_outcomes=outcomes_text,
            )
            formatted_prompts.append(prompt)

        # Process all curriculum items in a single batch
        logger.info(
            "Processing curriculum items for concept generation",
            count=len(curriculum_data),
        )
        concepts_results = batch_process_with_llm(
            data=curriculum_data,
            response_type=ConceptsResponse,
            system_prompt=system_prompt,
            user_prompt=formatted_prompts,
        )

        logger.info(
            "Successfully generated concepts results", count=len(concepts_results)
        )

        # Save to JSON file
        json_path = Path(__file__).parents[2] / "app" / "data" / "concepts.json"
        with open(json_path, "w") as f:
            serializable_data = [
                {
                    "subject_id": curriculum_data[i]["subject_id"],
                    "year_id": curriculum_data[i]["year_id"],
                    "concepts": result.model_dump()["concepts"],
                }
                for i, result in enumerate(concepts_results)
            ]
            json.dump(serializable_data, f, indent=2)

        logger.info("Concepts generation completed successfully")

    except Exception as e:
        logger.error("Failed to generate concepts", error=str(e))
        raise


if __name__ == "__main__":
    main()
