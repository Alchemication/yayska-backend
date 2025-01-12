"""Utility functions for LLM-related operations."""

import logging
import os
import time
from typing import Any, TypeVar

from langchain.globals import set_llm_cache
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_community.cache import SQLiteCache
from pydantic_core import ValidationError
from tqdm import tqdm

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_sync_database_url() -> str:
    """Convert async database URL to sync format.

    Returns:
        str: Synchronous database URL
    """
    return str(settings.DATABASE_URI).replace("postgresql+asyncpg://", "postgresql://")


def setup_llm_cache(cache_name: str) -> None:
    """Set up SQLite cache for LLM responses.

    Args:
        cache_name: Name of the cache file
    """
    os.makedirs(".cache", exist_ok=True)
    cache = SQLiteCache(database_path=f".cache/{cache_name}.db")
    set_llm_cache(cache)


def setup_llm_chain(
    response_type: type[T],
    system_prompt: str,
    user_prompt: str,
    attempt: int = 0,
    validation_error: bool = False,
) -> Any:
    """Set up the LLM chain with retry logic.

    Args:
        response_type: The Pydantic model type for structured output
        system_prompt: The system prompt text
        user_prompt: The user prompt text
        attempt: Current retry attempt number
        validation_error: Whether the previous attempt failed due to validation

    Returns:
        The configured LLM chain
    """
    temperature = 0.1 + (attempt * 0.15) if validation_error else 0.1
    llm = ChatAnthropic(
        model=settings.ANTHROPIC_CLAUDE_3_5_SONNET,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=temperature,
        max_tokens=4096,
        max_retries=3,
    )
    structured_llm = llm.with_structured_output(response_type)
    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    return template | structured_llm


def batch_process_with_llm(
    data: list[dict[str, Any]],
    response_type: type[T],
    system_prompt: str,
    user_prompt: str,
    chunk_size: int = 10,
) -> list[T]:
    """Process data in batches using LLM with retry logic.

    Args:
        data: List of data items to process
        response_type: The Pydantic model type for structured output
        system_prompt: The system prompt text
        user_prompt: The user prompt text
        chunk_size: Size of chunks to process at once

    Returns:
        List of processed responses
    """
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    responses = []

    for chunk in tqdm(chunks):
        validation_error = False
        for attempt in range(3):
            try:
                chain = setup_llm_chain(
                    response_type, system_prompt, user_prompt, attempt, validation_error
                )
                chunk_responses = chain.batch(chunk, config={"max_concurrency": 50})
                responses.extend(chunk_responses)
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

    return responses
