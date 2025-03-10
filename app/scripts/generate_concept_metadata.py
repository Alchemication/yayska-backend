"""Script to generate concept metadata for the database.

This script generates additional metadata for each concept in the database.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from app.prompts.concept_metadata import (
    ConceptMetadataResponse,
    system_prompt,
    user_prompt,
)
from app.utils.db import execute_query, get_engine
from app.utils.llm import batch_process_with_llm, setup_llm_cache
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_curriculum_data(engine: Any) -> list[dict[str, Any]]:
    """Load concept data from the database.

    Args:
        engine: Database engine instance

    Returns:
        List of dictionaries containing the concept data
    """
    query = """
        SELECT
            c.id AS concept_id,
            s.subject_name,
            sy.year_name AS school_year,
            c.concept_name,
            c.concept_description,
            c.learning_objectives,
            c.strand_reference
        FROM
            concepts c
        JOIN
            subjects s ON c.subject_id = s.id
        JOIN
            school_years sy ON c.year_id = sy.id
        ORDER BY
            s.subject_name ASC,
            c.concept_name ASC
    """
    return execute_query(engine, query)


class MetadataFormat(Enum):
    """Formats for metadata serialization."""

    ARRAY = "array"
    OBJECT = "object"
    STRING = "string"


def serialize_enum_list(obj: Any) -> Any:
    """Serialize Enum values to strings in lists or dictionaries.

    Args:
        obj: The object to serialize

    Returns:
        Serialized object with Enum values converted to strings
    """
    if isinstance(obj, list):
        return [serialize_enum_list(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_enum_list(value) for key, value in obj.items()}
    elif isinstance(obj, Enum):
        return obj.value
    return obj


def main() -> None:
    """Main function to execute the concept metadata generation process."""
    try:
        # Create database engine
        engine = get_engine()

        # Retrieve curriculum data
        logger.info("Loading concept data from database")
        concepts = get_curriculum_data(engine)
        logger.info("Loaded concepts", count=len(concepts))

        # Set up LLM cache
        setup_llm_cache("concept_metadata")

        # Process all concepts in a single batch
        logger.info("Processing concepts for metadata generation", count=len(concepts))

        # Format prompts for each concept
        formatted_prompts = []
        for concept in concepts:
            prompt = user_prompt.format(
                subject=concept["subject_name"],
                year=concept["school_year"],
                concept_name=concept["concept_name"],
                concept_description=concept["concept_description"],
                learning_objectives=concept["learning_objectives"],
                strand_reference=concept["strand_reference"],
            )
            formatted_prompts.append(prompt)

        concept_metadata = batch_process_with_llm(
            data=concepts,
            response_type=ConceptMetadataResponse,
            system_prompt=system_prompt,
            user_prompt=formatted_prompts,
        )

        logger.info(
            "Successfully generated concept metadata", count=len(concept_metadata)
        )

        # Save to JSON file
        json_path = Path(__file__).parents[2] / "app" / "data" / "concept_metadata.json"
        with open(json_path, "w") as f:
            serializable_data = [
                {
                    "concepts": [
                        {
                            "concept_id": concepts[i]["concept_id"],
                            **serialize_enum_list(metadata.model_dump()),
                        }
                    ]
                }
                for i, metadata in enumerate(concept_metadata)
            ]
            json.dump(serializable_data, f, indent=2)

        logger.info("Concept metadata generation completed successfully")

    except Exception as e:
        logger.error("Failed to generate concept metadata", error=str(e))
        raise


if __name__ == "__main__":
    main()
