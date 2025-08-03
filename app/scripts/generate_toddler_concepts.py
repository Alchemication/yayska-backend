"""Script to generate toddler concepts for the database.

This script generates toddler concepts for each learning outcome in the curriculum.

Ideally this could be developed as a batch job to save on costs.
"""

import asyncio
import json
from pathlib import Path
from string import Template
from typing import Any

from app.prompts.toddler_concepts import (
    DevelopmentalConceptsResponse,
    system_prompt,
    user_prompt,
)
from app.utils.db import execute_query, get_engine
from app.utils.llm import AIModel, LLMMessage, ReasoningEffort, get_batch_completions
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_data(engine: Any) -> list[dict[str, Any]]:
    """Load toddler curriculum data from the database.

    Args:
        engine: Database engine instance

    Returns:
        List of dictionaries containing the toddler curriculum data
    """
    school_years_query = """
        SELECT sy.id as year_id, sy.year_name
        FROM school_years sy
        JOIN education_levels e ON e.id = sy.level_id
        WHERE e.id = 3 -- Pre-School Development
        GROUP BY 1, 2
        ORDER BY year_id ASC
    """
    subjects_query = """
        SELECT 
            s.id AS subject_id,
            s.subject_name,
            s.introduction_year_id,
            c.area_name
        FROM subjects s
        join curriculum_areas c on c.id = s.area_id
        where c.id = 7 -- Early Development
        ORDER BY s.subject_name ASC
    """

    # Execute all queries
    school_years = execute_query(engine, school_years_query)
    subjects = execute_query(engine, subjects_query)

    # Combine the data
    curriculum_data = []
    for subject in subjects:
        subject_id = subject["subject_id"]
        subject_name = subject["subject_name"]
        introduction_year_id = subject["introduction_year_id"]
        area_name = subject["area_name"]

        # Group by school year
        for year in school_years:
            year_id = year["year_id"]
            year_name = year["year_name"]

            if year_id >= introduction_year_id:
                curriculum_data.append(
                    {
                        "subject_id": subject_id,
                        "subject_name": subject_name,
                        "year_id": year_id,
                        "year_name": year_name,
                        "area_name": area_name,
                    }
                )

    return curriculum_data


async def generate(data: list[dict[str, Any]]) -> list[Any]:
    """Generate developmental concepts using LLM in batches.

    Args:
        data: List of curriculum data items containing area_name, year_id, etc.

    Returns:
        List of LLM responses containing generated concepts
    """
    logger.info("Preparing batch data for LLM generation")

    # Prepare batch data for LLM
    template = Template(user_prompt)
    batch_data = []

    for item in data:
        try:
            formatted_prompt = template.substitute(**item)
            batch_data.append(
                {
                    "messages": [LLMMessage(role="user", content=formatted_prompt)],
                    "system_prompt": system_prompt,
                }
            )
        except KeyError as e:
            logger.error(
                "Missing template variable in data item", item=item, error=str(e)
            )
            raise

    logger.info("Starting LLM batch generation", batch_size=len(batch_data))

    # Generate with batch processing and caching
    results = await get_batch_completions(
        ai_model=AIModel.GEMINI_FLASH_2_5,
        data=batch_data,
        response_type=DevelopmentalConceptsResponse,
        max_concurrency=3,
        temperature=0.5,
        reasoning_effort=ReasoningEffort.DISABLE,
        cache_name="toddler_concepts",
    )

    logger.info("LLM batch generation completed", results_count=len(results))
    return results


def main() -> None:
    """Main function to execute the concept generation process."""
    try:
        # Create database engine
        engine = get_engine()

        # Retrieve curriculum data
        logger.info("Loading data from database")
        data = get_data(engine)[:2]
        logger.info("Loaded data entries", count=len(data))

        # Preview the data structure
        if data:
            logger.info("Sample data item", sample=data[0])

        # Generate with LLM
        logger.info("Starting generation with LLM")
        llm_results = asyncio.run(generate(data))

        if not llm_results:
            raise Exception("No results generated")

        logger.info("Successfully generated results", count=len(llm_results))

        # Save to JSON file
        json_path = Path(__file__).parents[2] / "app" / "data" / "toddler_concepts.json"
        with open(json_path, "w") as f:
            serializable_data = [
                {
                    "subject_id": data[i]["subject_id"],
                    "year_id": data[i]["year_id"],
                    "area_name": data[i]["area_name"],
                    "subject_name": data[i]["subject_name"],
                    "concepts": result.content.model_dump()["concepts"]
                    if hasattr(result.content, "model_dump")
                    else result.content,
                    "reasoning": result.content.model_dump()["reasoning"]
                    if hasattr(result.content, "model_dump")
                    else "",
                }
                for i, result in enumerate(llm_results)
            ]
            json.dump(serializable_data, f, indent=2)

        logger.info(
            "Concepts generation completed successfully", output_file=str(json_path)
        )

    except Exception as e:
        logger.error("Failed to generate toddler concepts", error=str(e))
        raise


if __name__ == "__main__":
    main()
