"""Script to generate monthly curriculum plans for the database.

This script generates a yearly curriculum plan divided into monthly plans for each school year.
"""

import json
from pathlib import Path
from typing import Any

from app.prompts.monthly_curriculum_plans import (
    YearlyPlanResponse,
    system_prompt,
    user_prompt,
)
from app.utils.db import execute_query, get_engine
from app.utils.llm import batch_process_with_llm, setup_llm_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_curriculum_data(engine: Any) -> list[dict[str, Any]]:
    """Load curriculum data from the database.

    Returns:
        list[dict[str, Any]]: List of dictionaries containing the curriculum data
    """
    query = """
        select
            sy.id as school_year_id,
            sy.year_name as school_year_name,
            c.id as concept_id,
            s.subject_name,
            c.concept_name,
            c.concept_description
        from concepts c
        join subjects s on c.subject_id = s.id
        join school_years sy on c.year_id = sy.id 
        order by 
            sy.id ASC,
            s.subject_name ASC,
            c.display_order ASC
    """
    return execute_query(engine, query)


def group_by_school_year(
    concepts: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group concepts by school year.

    Args:
        concepts: List of concept dictionaries

    Returns:
        Dict mapping school year IDs to lists of concepts
    """
    result = {}
    for concept in concepts:
        year_id = str(concept["school_year_id"])
        if year_id not in result:
            result[year_id] = []
        result[year_id].append(concept)
    return result


def format_concepts_list(concepts: list[dict[str, Any]]) -> str:
    """Format a list of concepts into a string for the prompt.

    Args:
        concepts: List of concept dictionaries

    Returns:
        Formatted string with concept details
    """
    # Group concepts by subject
    subjects = {}
    for concept in concepts:
        subject = concept["subject_name"]
        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append(concept)

    # Format the concepts list
    result = []
    for subject, subject_concepts in subjects.items():
        result.append(f"Subject: {subject}")
        for concept in subject_concepts:
            result.append(
                f"- Concept ID: {concept['concept_id']}, Name: {concept['concept_name']}, Description: {concept['concept_description']}"
            )
        result.append("")  # Empty line between subjects

    return "\n".join(result)


def main() -> None:
    """Main function to execute the monthly curriculum plan generation process."""
    try:
        # Create database engine
        engine = get_engine()

        # Retrieve curriculum data
        logger.info("Loading curriculum data from database...")
        concepts = get_curriculum_data(engine)
        logger.info("Loaded %d concepts", len(concepts))

        # Group concepts by school year
        year_concepts = group_by_school_year(concepts)
        logger.info("Grouped concepts into %d school years", len(year_concepts))

        # Set up LLM cache
        setup_llm_cache("monthly_curriculum_plans")

        # First, prepare all the data for batch processing
        batch_data = []
        formatted_prompts = []

        for year_id, year_concepts in year_concepts.items():
            # Format concepts list for the prompt
            concepts_list = format_concepts_list(year_concepts)

            # Get the year_name from the first concept in the list
            year_name = year_concepts[0]["school_year_name"]

            # Create formatted prompt for this school year
            formatted_prompt = user_prompt.replace("{concepts_list}", concepts_list)
            formatted_prompts.append(formatted_prompt)

            # Add to batch data
            batch_data.append(
                {"year_id": year_id, "year_name": year_name, "concepts": concepts_list}
            )

        # Now process all school years in a single batch
        logger.info("Processing all %d school years in a single batch", len(batch_data))
        yearly_plans = batch_process_with_llm(
            data=batch_data,
            response_type=YearlyPlanResponse,
            system_prompt=system_prompt,
            user_prompt=formatted_prompts,
        )

        logger.info("Successfully generated %d yearly plans", len(yearly_plans))

        # Save outcomes to JSON file
        json_path = (
            Path(__file__).parents[2] / "app" / "data" / "monthly_curriculum_plans.json"
        )
        with open(json_path, "w") as f:
            serializable_plans = [plan.model_dump() for plan in yearly_plans]
            json.dump(serializable_plans, f, indent=2)

        logger.info("Monthly curriculum plan generation completed successfully")

    except Exception as e:
        logger.error("Failed to generate monthly curriculum plans: %s", str(e))
        raise


if __name__ == "__main__":
    main()
