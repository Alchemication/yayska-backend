"""Utility functions for LLM-related operations."""

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
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def get_sync_database_url() -> str:
    """Convert async database URL to sync format.

    Returns:
        Synchronous database URL
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
    logger.info("LLM cache configured", cache_name=cache_name)


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
        user_prompt: The user prompt text or list of prompts
        attempt: Current retry attempt number
        validation_error: Whether the previous attempt failed due to validation

    Returns:
        The configured LLM chain
    """
    temperature = 0.1 + (attempt * 0.15) if validation_error else 0.1
    llm = ChatAnthropic(
        model=settings.ANTHROPIC_CLAUDE_3_7_SONNET,
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
    logger.debug(
        "LLM chain configured",
        model=settings.ANTHROPIC_CLAUDE_3_7_SONNET,
        temperature=temperature,
        attempt=attempt,
    )
    return template | structured_llm


def batch_process_with_llm(
    data: list[dict[str, Any]],
    response_type: type[T],
    system_prompt: str,
    user_prompt: str | list[str],
    chunk_size: int = 10,
) -> list[T]:
    """Process data in batches using LLM with retry logic.

    Args:
        data: List of data items to process
        response_type: The Pydantic model type for structured output
        system_prompt: The system prompt text
        user_prompt: The user prompt text or list of prompts
        chunk_size: Size of chunks to process at once

    Returns:
        List of processed responses
    """
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    responses = []

    logger.info(
        "Starting batch processing with LLM",
        total_items=len(data),
        chunks=len(chunks),
        chunk_size=chunk_size,
    )

    for chunk_idx, chunk in enumerate(tqdm(chunks)):
        validation_error = False
        for attempt in range(3):
            try:
                chain = setup_llm_chain(
                    response_type, system_prompt, user_prompt, attempt, validation_error
                )
                logger.info(
                    "Processing chunk",
                    chunk_idx=chunk_idx + 1,
                    total_chunks=len(chunks),
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
                    logger.error(
                        error_msg, chunk_idx=chunk_idx + 1, error=str(e), attempts=3
                    )
                    raise

                # Check if it's a rate limit error (429)
                is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()

                # Use exponential backoff only for rate limit errors
                if is_rate_limit:
                    backoff = 5 * (2**attempt)  # Exponential: 5, 10, 20...
                else:
                    backoff = 2  # Fixed short delay for other errors

                error_type = (
                    "Validation error"
                    if isinstance(e, ValidationError)
                    else "Rate limit error"
                    if is_rate_limit
                    else "Error"
                )

                logger.warning(
                    f"Retrying after {error_type}",
                    attempt=attempt + 1,
                    chunk_idx=chunk_idx + 1,
                    backoff_seconds=backoff,
                    error=str(e),
                    temperature=0.1 + ((attempt + 1) * 0.15)
                    if validation_error
                    else 0.1,
                )
                time.sleep(backoff)

    logger.info("Batch processing completed", total_responses=len(responses))
    return responses


def run_with_llm(
    response_type: type[T],
    system_prompt: str,
    user_prompt: str,
) -> T:
    """Run a single prompt through the LLM.

    Args:
        response_type: The Pydantic model type for structured output
        system_prompt: The system prompt text
        user_prompt: The user prompt text

    Returns:
        The processed response
    """
    validation_error = False
    for attempt in range(3):
        try:
            chain = setup_llm_chain(
                response_type, system_prompt, user_prompt, attempt, validation_error
            )
            logger.info("Processing single prompt")
            return chain.invoke({})
        except (ValidationError, Exception) as e:
            if isinstance(e, ValidationError):
                validation_error = True

            if attempt == 2:
                error_msg = (
                    "Validation failed"
                    if isinstance(e, ValidationError)
                    else "Failed to process prompt"
                )
                logger.error(error_msg, error=str(e), attempts=3)
                raise

            # Check if it's a rate limit error (429)
            is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()

            # Use exponential backoff only for rate limit errors
            if is_rate_limit:
                backoff = 5 * (2**attempt)  # Exponential: 5, 10, 20...
            else:
                backoff = 2  # Fixed short delay for other errors

            error_type = (
                "Validation error"
                if isinstance(e, ValidationError)
                else "Rate limit error"
                if is_rate_limit
                else "Error"
            )

            logger.warning(
                f"Retrying after {error_type}",
                attempt=attempt + 1,
                backoff_seconds=backoff,
                error=str(e),
                temperature=0.1 + ((attempt + 1) * 0.15) if validation_error else 0.1,
            )
            time.sleep(backoff)
