"""Script to generate metadata for concepts.

This script generates concept metadata for each concept in the curriculum.

Ideally this could be developed as a batch job to save on costs.
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict

from app.prompts.concept_metadata import (
    ConceptMetadataResponse,
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
    query = """
        SELECT 
            s.subject_name,
            c.id AS concept_id,
            c.year_id,
            sy.year_name,
            c.concept_name,
            c.concept_description,
            (
                SELECT array_agg(json_build_object(
                    'id', rc.id,
                    'concept_name', rc.concept_name,
                    'concept_description', rc.concept_description
                ) ORDER BY rc.display_order)
                FROM concepts rc
                WHERE rc.id != c.id  -- Exclude the current concept
                AND rc.subject_id = c.subject_id  -- Same subject
                AND rc.year_id = c.year_id  -- Same school year
            ) AS related_concepts
        FROM subjects s
        JOIN concepts c ON c.subject_id = s.id
        JOIN school_years sy ON sy.id = c.year_id 
        ORDER BY 
            s.id ASC,
            c.year_id ASC,
            c.display_order ASC
    """
    return execute_query(engine, query)


def serialize_enum_list(obj: Any) -> Any:
    """Recursively serialize objects, converting enums in lists to their values."""
    if isinstance(obj, list):
        return [serialize_enum_list(item) for item in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine
        engine = get_engine()

        # Retrieve curriculum data
        logger.info("Loading curriculum data from database...")
        concepts = get_curriculum_data(engine)
        logger.info("Loaded %d concepts", len(concepts))

        # Set up LLM cache
        setup_llm_cache("concept_metadata")

        # Generate concepts
        logger.info("Generating concept metadata...")
        concept_metadata = batch_process_with_llm(
            data=concepts,
            response_type=ConceptMetadataResponse,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Save outcomes to JSON file into the data folder
        json_path = Path(__file__).parents[2] / "app" / "data" / "concept_metadata.json"
        with open(json_path, "w") as f:
            serializable_concept_metadata = [
                {
                    **metadata.model_dump(),
                    "assessment_approaches": {
                        **metadata.assessment_approaches.model_dump(),
                        "suitable_types": serialize_enum_list(
                            metadata.assessment_approaches.suitable_types
                        ),
                    },
                }
                for metadata in concept_metadata
            ]
            json.dump(serializable_concept_metadata, f, indent=2)

        logger.info("Concept metadata generation completed successfully")

    except Exception as e:
        logger.error("Failed to generate concept metadata: %s", str(e))
        raise


if __name__ == "__main__":
    main()
