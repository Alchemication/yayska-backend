"""Utility functions for LLM-related operations."""

import os
import time
from enum import Enum
from typing import Any, TypeVar

from langchain.globals import set_llm_cache
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_community.cache import SQLiteCache
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic_core import ValidationError
from tqdm import tqdm

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class AIPlatform(Enum):
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class AnthropicModel(Enum):
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"
    CLAUDE_SONNET_3_7 = "claude-3-7-sonnet-20250219"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"


class GoogleModel(Enum):
    GEMINI_FLASH_2_0 = "gemini-2.0-flash"
    GEMINI_FLASH_2_5 = "gemini-2.5-flash-preview-05-20"
    GEMINI_PRO_2_5 = "gemini-2.5-pro-preview-05-06"


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
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    system_prompt: str,
    user_prompt: str,
    response_type: type[T] | None,
    attempt: int = 0,
    validation_error: bool = False,
) -> Any:
    """Set up the LLM chain with retry logic.

    Args:
        system_prompt: The system prompt text
        user_prompt: The user prompt text or list of prompts
        attempt: Current retry attempt number
        response_type: The Pydantic model type for structured output (or None for unstructured)
        validation_error: Whether the previous attempt failed due to validation

    Returns:
        The configured LLM chain
    """
    temperature = 0.1 + (attempt * 0.15) if validation_error else 0.1
    if ai_platform == AIPlatform.ANTHROPIC:
        # validate model is an Anthropic model
        if not isinstance(ai_model, AnthropicModel):
            raise ValueError(f"Invalid Anthropic model: {ai_model}")
        logger.info("Using Anthropic model", model=ai_model.value)
        llm = ChatAnthropic(
            model=ai_model.value,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=temperature,
            max_tokens=4096,
            max_retries=3,
        )
    elif ai_platform == AIPlatform.GOOGLE:
        # validate model is a Google model
        if not isinstance(ai_model, GoogleModel):
            raise ValueError(f"Invalid Google model: {ai_model}")
        logger.info("Using Google model", model=ai_model.value)
        llm = ChatGoogleGenerativeAI(
            model=ai_model.value,
            api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            max_tokens=4096,
            max_retries=3,
        )
    else:
        raise ValueError(f"Invalid AI platform: {ai_platform}")
    if response_type is not None:
        logger.info("Using structured output", response_type=response_type.__name__)
        llm = llm.with_structured_output(response_type)
    else:
        logger.info("Using unstructured output (str)")
    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )
    logger.debug(
        "LLM chain configured",
        model=ai_model.value,
        temperature=temperature,
        attempt=attempt,
    )
    return template | llm


def batch_process_with_llm(
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    data: list[dict[str, Any]],
    system_prompt: str,
    user_prompt: str,
    response_type: type[T] | None,
    max_concurrency: int = 50,
    chunk_size: int = 10,
) -> list[T | str]:
    """Process data in batches using LLM with retry logic.

    Args:
        ai_platform: The AI platform to use
        ai_model: The AI model to use
        data: List of data items to process
        response_type: The Pydantic model type for structured output or None for unstructured
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
                    ai_platform,
                    ai_model,
                    system_prompt,
                    user_prompt,
                    response_type,
                    attempt,
                    validation_error,
                )
                logger.info(
                    "Processing chunk",
                    chunk_idx=chunk_idx + 1,
                    total_chunks=len(chunks),
                )
                chunk_responses = chain.batch(
                    chunk, config={"max_concurrency": max_concurrency}
                )
                if response_type is not None:
                    responses.extend(chunk_responses)
                else:
                    responses.extend([response.content for response in chunk_responses])
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
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    data: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    response_type: type[T] | None,
) -> T | str:
    """Run a single prompt through the LLM.

    Args:
        ai_platform: The AI platform to use
        ai_model: The AI model to use
        data: The data to process
        response_type: The Pydantic model type for structured output or None for unstructured
        system_prompt: The system prompt text
        user_prompt: The user prompt text

    Returns:
        The processed response
    """
    validation_error = False
    for attempt in range(3):
        try:
            chain = setup_llm_chain(
                ai_platform,
                ai_model,
                system_prompt,
                user_prompt,
                response_type,
                attempt,
                validation_error,
            )
            response = chain.invoke(data)
            if response_type is not None:
                return response
            else:
                return response.content
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
