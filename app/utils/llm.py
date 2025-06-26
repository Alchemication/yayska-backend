"""Utility functions for LLM-related operations."""

import asyncio
import os
import time
from enum import Enum
from typing import Any, TypeVar

from langchain.globals import set_llm_cache
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_community.cache import SQLiteCache
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
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
    GEMINI_FLASH_2_0_LITE = "gemini-2.0-flash-lite"
    GEMINI_FLASH_2_0 = "gemini-2.0-flash"
    GEMINI_FLASH_2_5 = "gemini-2.5-flash"
    GEMINI_PRO_2_5 = "gemini-2.5-pro-preview-05-06"


class LLMResponse:
    """Wrapper class to unify response format and provide token usage tracking."""

    def __init__(
        self,
        content: T | str,
        usage_metadata: dict | None = None,
        raw_response: Any = None,
    ):
        self.content = content
        self.usage_metadata = usage_metadata or {}
        self.raw_response = raw_response


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
    response_type: type[T] | None,
    temperature: float = 0.5,
    attempt: int = 0,
    validation_error: bool = False,
) -> Any:
    """Set up the LLM chain with retry logic.

    Args:
        response_type: The Pydantic model type for structured output (or None for unstructured)
        temperature: The temperature for the LLM
        attempt: Current retry attempt number
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
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
    else:
        raise ValueError(f"Invalid AI platform: {ai_platform}")

    # Configure structured output with raw response for token tracking
    if response_type is not None:
        logger.info("Using structured output", response_type=response_type.__name__)
        llm = llm.with_structured_output(response_type, include_raw=True)
    else:
        logger.info("Using unstructured output (str)")

    template = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{user_prompt}"),
        ]
    )
    logger.debug(
        "LLM chain configured",
        model=ai_model.value,
        temperature=temperature,
        attempt=attempt,
    )
    return template | llm


def _extract_response_and_usage(
    response: Any,
    response_type: type[T] | None,
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
) -> LLMResponse:
    """Extract the content and usage metadata from the response.

    Args:
        response: The raw response from the LLM
        response_type: The response type (None for unstructured)
        ai_platform: The AI platform used
        ai_model: The AI model used

    Returns:
        LLMResponse with unified interface
    """
    if response_type is not None:
        # Structured output with include_raw=True
        # Response format: {"parsed": <structured_data>, "raw": <AIMessage>, "parsing_error": None}
        content = response["parsed"]
        usage_metadata = getattr(response["raw"], "usage_metadata", {})
        raw_response = response["raw"]
    else:
        # Unstructured output - response is AIMessage
        content = response.content
        usage_metadata = getattr(response, "usage_metadata", {})
        raw_response = response

    # Add platform and model info
    if usage_metadata is None:
        usage_metadata = {}
    usage_metadata["ai_platform"] = ai_platform.value
    usage_metadata["ai_model"] = ai_model.value

    return LLMResponse(
        content=content, usage_metadata=usage_metadata, raw_response=raw_response
    )


def llm_batch(
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    data: list[dict[str, Any]],
    response_type: type[T] | None,
    max_concurrency: int = 50,
    chunk_size: int = 10,
    temperature: float = 0.5,
) -> list[LLMResponse]:
    """Process data in batches using LLM with retry logic.

    Args:
        ai_platform: The AI platform to use
        ai_model: The AI model to use
        data: List of data items to process
        response_type: The Pydantic model type for structured output or None for unstructured
        chunk_size: Size of chunks to process at once

    Returns:
        List of LLMResponse objects with unified interface
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
                    response_type,
                    temperature,
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

                # Extract content and usage metadata from each response
                processed_responses = [
                    _extract_response_and_usage(
                        response, response_type, ai_platform, ai_model
                    )
                    for response in chunk_responses
                ]
                responses.extend(processed_responses)
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


def llm_invoke(
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    data: dict[str, Any],
    response_type: type[T] | None,
    temperature: float = 0.5,
) -> LLMResponse:
    """Run a single prompt through the LLM.

    Args:
        ai_platform: The AI platform to use
        ai_model: The AI model to use
        data: The data to process
        response_type: The Pydantic model type for structured output or None for unstructured
        temperature: The temperature for the LLM

    Returns:
        LLMResponse with unified interface
    """
    validation_error = False
    for attempt in range(3):
        try:
            chain = setup_llm_chain(
                ai_platform,
                ai_model,
                response_type,
                temperature,
                attempt,
                validation_error,
            )
            response = chain.invoke(data)
            return _extract_response_and_usage(
                response, response_type, ai_platform, ai_model
            )
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
                temperature=temperature,
            )
            time.sleep(backoff)
    raise Exception("LLM invoke failed after multiple retries")


async def allm_invoke(
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    data: dict[str, Any],
    response_type: type[T] | None,
    temperature: float = 0.5,
) -> LLMResponse:
    """Run a single prompt through the LLM asynchronously.

    Args:
        ai_platform: The AI platform to use
        ai_model: The AI model to use
        data: The data to process
        response_type: The Pydantic model type for structured output or None for unstructured
        temperature: The temperature for the LLM

    Returns:
        LLMResponse with unified interface
    """
    validation_error = False
    for attempt in range(3):
        try:
            chain = setup_llm_chain(
                ai_platform,
                ai_model,
                response_type,
                temperature,
                attempt,
                validation_error,
            )
            response = await chain.ainvoke(data)
            return _extract_response_and_usage(
                response, response_type, ai_platform, ai_model
            )
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

            is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()

            if is_rate_limit:
                backoff = 5 * (2**attempt)
            else:
                backoff = 2

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
                temperature=temperature,
            )
            await asyncio.sleep(backoff)
    raise Exception("LLM call failed after multiple retries")
