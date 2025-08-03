"""Utility functions for LLM-related operations using LiteLLM."""

import asyncio
import hashlib
import json
import os
import sqlite3
from enum import Enum
from typing import Any, AsyncGenerator, Generic, TypeVar

import litellm
from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Configure LiteLLM
litellm.telemetry = False
litellm.debug = False
litellm.drop_params = True


class AIModel(str, Enum):
    """
    Enum for AI models, using liteLLM's provider prefix format.
    https://docs.litellm.ai/docs/providers

    Note: reasoning_effort parameter is supported by OpenAI's o-series models
    (o3-mini, o4-mini, etc.) and controls the reasoning depth before responding.
    """

    # Anthropic Models
    CLAUDE_HAIKU_3_5 = "anthropic/claude-3-5-haiku-20241022"
    CLAUDE_SONNET_3_7 = (
        "anthropic/claude-3-7-sonnet-20250219"  # Supports reasoning_effort
    )
    CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4-20250514"  # Supports reasoning_effort

    # Google Models
    GEMINI_FLASH_2_0_LITE = "gemini/gemini-2.0-flash-lite"
    GEMINI_FLASH_2_0 = "gemini/gemini-2.0-flash"
    GEMINI_FLASH_2_5 = "gemini/gemini-2.5-flash"  # Supports reasoning_effort
    GEMINI_PRO_2_5 = "gemini/gemini-2.5-pro"  # Supports reasoning_effort

    # OpenAI Models
    GPT_4O = "openai/gpt-4o"
    GPT_4O_MINI = "openai/gpt-4o-mini"
    GPT_O3_MINI = "openai/o3-mini"  # Supports reasoning_effort
    GPT_O4_MINI = "openai/o4-mini"  # Supports reasoning_effort


class ReasoningEffort(str, Enum):
    """Enum for reasoning effort levels."""

    DISABLE = "disable"  # Only for Gemini models
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LLMCache:
    """A simple SQLite-based cache for LLM responses."""

    def __init__(self, cache_name: str):
        """
        Initialize the cache.

        Args:
            cache_name: The name of the cache, used as the database file name.
        """
        cache_dir = "cache"
        os.makedirs(cache_dir, exist_ok=True)
        self.db_path = os.path.join(cache_dir, f"{cache_name}.db")
        self._create_table()

    def _create_table(self):
        """Create the cache table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    response TEXT
                )
                """
            )

    def _get_cache_key(self, data: dict[str, Any]) -> str:
        """
        Generate a consistent hash for a given dictionary.

        Args:
            data: The dictionary to hash.

        Returns:
            A SHA-256 hash of the dictionary.
        """
        try:
            # Sort the dictionary to ensure consistent hash
            sorted_data_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(sorted_data_str.encode("utf-8")).hexdigest()
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to generate cache key: {e}")
            # Fallback to a simpler key generation
            fallback_str = str(sorted(data.items()))
            return hashlib.sha256(fallback_str.encode("utf-8")).hexdigest()

    def get(self, key_data: dict[str, Any]) -> Any | None:
        """
        Get a response from the cache.

        Args:
            key_data: The data to use for generating the cache key.

        Returns:
            The cached response or None if not found.
        """
        try:
            key = self._get_cache_key(key_data)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT response FROM cache WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached response: {e}")
            return None

    def set(self, key_data: dict[str, Any], response: Any):
        """
        Set a response in the cache.

        Args:
            key_data: The data to use for generating the cache key.
            response: The response to cache.
        """
        try:
            key = self._get_cache_key(key_data)
            serialized_response = json.dumps(response, default=str)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, response) VALUES (?, ?)",
                    (key, serialized_response),
                )
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    def __del__(self):
        """Close the connection when the object is destroyed."""
        # No connection to close since we use context managers
        pass


class LLMMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str  # "user", "assistant", or "system"
    content: str


class LLMResponse(BaseModel, Generic[T]):
    """
    Unified response format with support for structured output and reasoning content.
    """

    content: T | str
    reasoning_content: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw_response: Any = Field(None, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)


async def get_completion(
    ai_model: AIModel,
    messages: list[LLMMessage],
    response_type: type[T] | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    cache_name: str | None = None,
    reasoning_effort: ReasoningEffort | None = None,
) -> LLMResponse[T]:
    """
    Get a completion from an LLM with optional structured output and reasoning.

    Args:
        ai_model: The AI model to use.
        messages: The conversation messages.
        response_type: Pydantic model for structured output, or None for text.
        system_prompt: Optional system prompt.
        temperature: Model temperature (0.0 to 1.0).
        max_tokens: Maximum tokens to generate.
        cache_name: Optional cache name for SQLite caching.
        reasoning_effort: Reasoning depth for supported models.

    Returns:
        LLMResponse with content, optional reasoning, and usage data.
    """
    cache = LLMCache(cache_name) if cache_name else None

    # Prepare messages
    api_messages = [msg.model_dump() for msg in messages]
    if system_prompt:
        api_messages.insert(0, {"role": "system", "content": system_prompt})

    # Create cache key
    cache_key_data = {
        "model": ai_model.value,
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_type": f"{response_type.__module__}.{response_type.__name__}"
        if response_type
        else None,
        "reasoning_effort": reasoning_effort.value if reasoning_effort else None,
    }

    # Check cache
    if cache:
        cached_response = cache.get(cache_key_data)
        if cached_response:
            try:
                content = cached_response["content"]
                if response_type and isinstance(content, dict):
                    content = response_type.model_validate(content)
                return LLMResponse(
                    content=content,
                    reasoning_content=cached_response.get("reasoning_content"),
                    usage={"cached": True},
                )
            except Exception as e:
                logger.warning(f"Cache parsing failed: {e}")

    # Retry loop
    for attempt in range(3):
        try:
            params = {
                "model": ai_model.value,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add reasoning effort if supported
            if reasoning_effort:
                params["reasoning_effort"] = reasoning_effort.value

            # Add structured output if requested
            if response_type:
                params["response_format"] = response_type

            logger.info(
                f"LLM request: {len(api_messages)} messages to {ai_model.value}"
            )

            response = await litellm.acompletion(**params)
            message = response.choices[0].message

            # Parse content
            if response_type:
                content = response_type.model_validate_json(message.content)
            else:
                content = message.content or ""

            # Extract reasoning content if available
            reasoning_content = getattr(message, "reasoning_content", None)

            # Build usage metadata
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

            # Add reasoning tokens if available
            if hasattr(response.usage, "completion_tokens_details"):
                details = response.usage.completion_tokens_details
                if hasattr(details, "reasoning_tokens") and details.reasoning_tokens:
                    usage["reasoning_tokens"] = details.reasoning_tokens

            # Cache the response
            if cache:
                cache_data = {
                    "content": content.model_dump()
                    if isinstance(content, BaseModel)
                    else content,
                    "reasoning_content": reasoning_content,
                }
                cache.set(cache_key_data, cache_data)

            return LLMResponse(
                content=content,
                reasoning_content=reasoning_content,
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            if attempt == 2:
                logger.error(f"LLM call failed after 3 attempts: {e}")
                raise

            # Exponential backoff
            backoff = 2**attempt
            logger.warning(f"LLM error, retrying in {backoff}s: {e}")
            await asyncio.sleep(backoff)

    raise Exception("LLM call failed after retries")


async def get_completion_stream(
    ai_model: AIModel,
    messages: list[LLMMessage],
    system_prompt: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    reasoning_effort: ReasoningEffort | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream a completion from an LLM.

    Args:
        ai_model: The AI model to use.
        messages: The conversation messages.
        system_prompt: Optional system prompt.
        temperature: Model temperature (0.0 to 1.0).
        max_tokens: Maximum tokens to generate.
        reasoning_effort: Reasoning depth for supported models.

    Yields:
        String chunks of the response content.
    """
    # Prepare messages
    api_messages = [msg.model_dump() for msg in messages]
    if system_prompt:
        api_messages.insert(0, {"role": "system", "content": system_prompt})

    params = {
        "model": ai_model.value,
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    if reasoning_effort:
        params["reasoning_effort"] = reasoning_effort.value

    try:
        logger.info(f"LLM stream: {len(api_messages)} messages to {ai_model.value}")
        response = await litellm.acompletion(**params)

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"LLM streaming failed: {e}")
        raise


async def get_batch_completions(
    ai_model: AIModel,
    data: list[dict[str, Any]],
    response_type: type[T] | None = None,
    max_concurrency: int = 50,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    cache_name: str | None = None,
    reasoning_effort: ReasoningEffort | None = None,
) -> list[LLMResponse[T]]:
    """
    Process multiple completions concurrently.

    Args:
        ai_model: The AI model to use.
        data: List of items, each containing 'messages' and optionally 'system_prompt'.
        response_type: Pydantic model for structured output, or None for text.
        max_concurrency: Maximum concurrent requests.
        temperature: Model temperature (0.0 to 1.0).
        max_tokens: Maximum tokens to generate.
        cache_name: Optional cache name for SQLite caching.
        reasoning_effort: Reasoning depth for supported models.

    Returns:
        List of LLMResponse objects (exceptions are logged and filtered out).
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _process_item(item: dict[str, Any]) -> LLMResponse[T]:
        async with semaphore:
            return await get_completion(
                ai_model=ai_model,
                messages=item["messages"],
                response_type=response_type,
                system_prompt=item.get("system_prompt"),
                temperature=temperature,
                max_tokens=max_tokens,
                cache_name=cache_name,
                reasoning_effort=reasoning_effort,
            )

    logger.info(
        f"Batch processing {len(data)} items with {max_concurrency} concurrency"
    )

    tasks = [_process_item(item) for item in data]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successful results and log failures
    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Batch item {i} failed: {result}")
        else:
            successful_results.append(result)

    logger.info(f"Batch completed: {len(successful_results)}/{len(data)} successful")
    return successful_results
