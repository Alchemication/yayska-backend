"""Script to generate learning outcomes in the database.

This script generates learning outcomes for each year level and unit in the curriculum.

Ideally this could be developed as a batch job to save on costs.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from langchain.globals import set_llm_cache
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_community.cache import SQLiteCache
from sqlalchemy import create_engine, text
from tqdm import tqdm

from app.config import settings
from app.prompts.learning_outcomes import (
    LearningOutcomesResponse,
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
            ca.id AS area_id,
            ca.area_name,
            s.id AS subject_id,
            s.subject_name,
            st.id AS strand_id,
            st.strand_name,
            su.id AS unit_id,
            su.unit_name
        FROM curriculum_areas ca
        JOIN subjects s ON s.area_id = ca.id
        JOIN strands st ON st.subject_id = s.id
        JOIN strand_units su ON su.strand_id = st.id
        ORDER BY 
            ca.area_name,
            s.subject_name,
            st.strand_name,
            su.unit_name
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row) for row in result.mappings()]


def generate_learning_outcomes(data: dict[str, Any]) -> list[LearningOutcomesResponse]:
    """Use LLM to generate learning outcomes for each year level and unit in the curriculum.

    Args:
        data: Dictionary containing the curriculum data
    """
    # chunk data into smaller pieces
    chunk_size = 5
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    # set up cache
    os.makedirs(".cache", exist_ok=True)
    cache = SQLiteCache(database_path=".cache/learning_outcomes.db")
    set_llm_cache(cache)

    # set up LLM
    llm = ChatAnthropic(
        model=settings.ANTHROPIC_CLAUDE_3_5_SONNET,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0.1,
        max_tokens=4096,
        max_retries=3,
    )
    structured_llm = llm.with_structured_output(LearningOutcomesResponse)
    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    chain = template | structured_llm

    # generate learning outcomes
    learning_outcomes = []
    for chunk in tqdm(chunks):
        responses = chain.batch(chunk, config={"max_concurrency": 50})
        learning_outcomes.extend(responses)

    return learning_outcomes


def main() -> None:
    """Main function to execute the data loading process."""
    try:
        # Create database engine with synchronous URL
        engine = create_engine(get_sync_database_url())

        # Retrieve curriculum data
        logger.info("Loading master data from JSON file...")
        data = get_curriculum_data(engine)

        # Generate learning outcomes
        logger.info("Generating learning outcomes...")
        outcomes = generate_learning_outcomes(data)

        # Save outcomes to JSON file into the data folder
        json_path = (
            Path(__file__).parents[2] / "app" / "data" / "learning_outcomes.json"
        )
        with open(json_path, "w") as f:
            # Convert Pydantic objects to dictionaries using model_dump()
            serializable_outcomes = [outcome.model_dump() for outcome in outcomes]
            json.dump(serializable_outcomes, f, indent=2)

        logger.info("Learning outcomes generation completed successfully")

    except Exception as e:
        logger.error("Failed to generate learning outcomes: %s", str(e))
        raise


if __name__ == "__main__":
    main()
