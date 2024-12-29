"""Script to generate metadata for concepts.

This script generates concept metadata for each concept in the curriculum.

Ideally this could be developed as a batch job to save on costs.
"""

import json
import logging
import os
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict

from langchain.globals import set_llm_cache
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_community.cache import SQLiteCache
from pydantic_core import ValidationError
from sqlalchemy import create_engine, text
from tqdm import tqdm

from app.config import settings
from app.prompts.concept_metadata import (
    ConceptMetadataResponse,
    system_prompt,
    user_prompt,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_sync_database_url() -> str:
    """Convert async database URL to sync format.

    Returns:
        str: Synchronous database URL
    """
    # Replace async driver with sync driver
    return str(settings.DATABASE_URI).replace("postgresql+asyncpg://", "postgresql://")


def get_curriculum_data(engine: Any) -> Dict[str, Any]:
    """Load curriculum data from the database.

    Returns:
        Dict[str, Any]: Dictionary containing the curriculum data
    """
    query = """
        SELECT 
            ca.area_name,
            s.subject_name,
            st.strand_name,
            su.unit_name,
            lo.outcome_description,
            c.id AS concept_id,
            c.concept_name,
            c.concept_description,
            (
                SELECT array_agg(json_build_object(
                    'id', rc.id,
                    'concept_name', rc.concept_name,
                    'concept_description', rc.concept_description
                ) ORDER BY rc.id)
                FROM concepts rc
                WHERE rc.outcome_id = lo.id 
                AND rc.id != c.id
            ) AS related_concepts
        FROM curriculum_areas ca
        JOIN subjects s ON s.area_id = ca.id
        JOIN strands st ON st.subject_id = s.id
        JOIN strand_units su ON su.strand_id = st.id
        JOIN learning_outcomes lo ON lo.unit_id = su.id
        JOIN concepts c ON c.outcome_id = lo.id
        ORDER BY 
            ca.area_name,
            s.subject_name,
            st.strand_name,
            su.unit_name,
            lo.outcome_description,
            c.concept_name
        """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row) for row in result.mappings()]


def generate_concept_metadata(data: dict[str, Any]) -> list[ConceptMetadataResponse]:
    """Use LLM to generate metadata for each concept in the curriculum.

    Args:
        data: Dictionary containing the curriculum data
    """
    # chunk data into smaller pieces
    chunk_size = 5
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    # set up cache
    os.makedirs(".cache", exist_ok=True)
    cache = SQLiteCache(database_path=".cache/concept_metadata.db")
    set_llm_cache(cache)

    def setup_llm_chain(attempt: int, validation_error: bool = False) -> Any:
        """Set up the LLM chain.

        Args:
            attempt: Current retry attempt number
            validation_error: Whether the previous attempt failed due to validation
        """
        temperature = 0.1 + (attempt * 0.15) if validation_error else 0.1
        llm = ChatAnthropic(
            model=settings.ANTHROPIC_CLAUDE_3_5_SONNET,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=temperature,
            max_tokens=4096,
            max_retries=3,
        )
        structured_llm = llm.with_structured_output(ConceptMetadataResponse)
        template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )
        chain = template | structured_llm
        return chain

    # generate concepts
    concept_metadata = []
    for chunk in tqdm(chunks):
        validation_error = False
        for attempt in range(3):  # max 3 manual retries with backoff
            try:
                chain = setup_llm_chain(attempt, validation_error)
                responses = chain.batch(chunk, config={"max_concurrency": 50})
                concept_metadata.extend(responses)
                break
            except (ValidationError, Exception) as e:
                if isinstance(e, ValidationError):
                    validation_error = True

                if attempt == 2:
                    error_msg = (
                        "Validation failed"
                        if isinstance(e, ValidationError)
                        else "Failed to process chunk"
                    )
                    logger.error(f"{error_msg} after 3 attempts: {str(e)}")
                    raise

                backoff = 5 + (attempt * 2.5)
                error_type = (
                    "Validation error" if isinstance(e, ValidationError) else "Attempt"
                )
                logger.warning(
                    f"{error_type} on attempt {attempt + 1}, retrying with higher temperature in {backoff} seconds: {str(e)}"
                )
                time.sleep(backoff)

    return concept_metadata


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
        # Create database engine with synchronous URL
        engine = create_engine(get_sync_database_url())

        # Retrieve curriculum data
        logger.info("Loading master data from JSON file...")
        data = get_curriculum_data(engine)

        # Generate concepts
        logger.info("Generating concept metadata...")
        concept_metadata = generate_concept_metadata(data)

        # Save outcomes to JSON file into the data folder
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
