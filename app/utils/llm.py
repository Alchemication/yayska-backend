"""Utility functions for LLM-related operations."""

import asyncio
from enum import Enum
from typing import Any, AsyncGenerator, Generic, TypeVar

import litellm
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Set API keys for LiteLLM from your application settings
# Make sure GEMINI_API_KEY and ANTHROPIC_API_KEY are in your .env file
litellm.gemini_api_key = settings.GEMINI_API_KEY
litellm.anthropic_api_key = settings.ANTHROPIC_API_KEY
litellm.telemetry = False


class LLMMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str  # "user" or "assistant"
    content: str


class AIModel(str, Enum):
    """
    Enum for AI models, using liteLLM's provider prefix format.
    https://docs.litellm.ai/docs/providers
    """

    # Anthropic Models
    CLAUDE_HAIKU_3_5 = "anthropic/claude-3-5-haiku-20241022"
    CLAUDE_SONNET_3_7 = "anthropic/claude-3-7-sonnet-20250219"
    CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4-20250514"

    # Google Models
    GEMINI_FLASH_2_0_LITE = "gemini/gemini-2.0-flash-lite"
    GEMINI_FLASH_2_0 = "gemini/gemini-2.0-flash"
    GEMINI_FLASH_2_5 = "gemini/gemini-2.5-flash"
    GEMINI_PRO_2_5 = "gemini/gemini-2.5-pro"


class LLMResponse(BaseModel, Generic[T]):
    """Wrapper class to unify response format and provide token usage tracking."""

    content: T | str
    usage_metadata: dict | None = {}
    raw_response: Any = Field(None, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)


def _pydantic_to_tool_schema(model: type[T]) -> dict[str, Any]:
    """
    Convert a Pydantic model to an OpenAI-compatible tool schema for LiteLLM.

    Args:
        model: The Pydantic model class.

    Returns:
        A dictionary representing the tool schema.
    """
    schema = model.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name": schema.get("title", model.__name__),
            "description": schema.get(
                "description",
                f"Extract information for {schema.get('title', model.__name__)}",
            ),
            "parameters": schema,
        },
    }


async def get_completion(
    ai_model: AIModel,
    messages: list[LLMMessage],
    response_type: type[T] | None,
    system_prompt: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> LLMResponse[T]:
    """
    Run a single prompt through the LLM asynchronously with retry logic.

    Args:
        ai_model: The AI model to use.
        messages: The list of messages forming the conversation.
        response_type: Pydantic model for structured output, or None for string.
        system_prompt: The system prompt to use.
        temperature: The model temperature.
        max_tokens: The maximum number of tokens to generate.

    Returns:
        An LLMResponse object.
    """
    validation_error = False
    for attempt in range(3):
        try:
            current_temp = temperature
            if validation_error:
                current_temp = 0.1 + (attempt * 0.15)
                logger.warning(
                    "Retrying with increased temperature due to validation error",
                    attempt=attempt,
                    temperature=current_temp,
                )

            # Convert messages to the format expected by LiteLLM (same as OpenAI)
            api_messages = [msg.model_dump() for msg in messages]
            if system_prompt:
                api_messages.insert(0, {"role": "system", "content": system_prompt})

            # log messages
            logger.info("Sending messages to LLM", messages=api_messages)

            params: dict[str, Any] = {
                "model": ai_model.value,
                "messages": api_messages,
                "temperature": current_temp,
                "max_tokens": max_tokens,
            }

            if response_type:
                tool_schema = _pydantic_to_tool_schema(response_type)
                params["tools"] = [tool_schema]
                params["tool_choice"] = {
                    "type": "function",
                    "function": {"name": tool_schema["function"]["name"]},
                }

            response = await litellm.acompletion(**params)

            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            if response_type:
                tool_calls = response.choices[0].message.tool_calls
                if not tool_calls:
                    raise ValueError("No tool use block found in response")
                # Assuming one tool call for now as is the current implementation
                tool_call = tool_calls[0]
                args = tool_call.function.arguments
                content = response_type.model_validate_json(args)
            else:
                message_content = response.choices[0].message.content
                content = str(message_content) if message_content is not None else ""

            return LLMResponse(
                content=content, usage_metadata=usage, raw_response=response
            )

        except (ValidationError, ValueError, Exception) as e:
            # Check for common validation error patterns
            is_validation_err = isinstance(
                e, ValidationError
            ) or "No tool use block found" in str(e)

            if is_validation_err:
                validation_error = True
                error_type = "Validation error"
            else:
                error_type = "API error"

            if attempt == 2:
                logger.error(f"{error_type} failed after 3 attempts", error=str(e))
                raise

            # Implement backoff logic
            is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()
            backoff = 5 * (2**attempt) if is_rate_limit else 2

            logger.warning(
                f"Retrying after {error_type}",
                attempt=attempt + 1,
                backoff_seconds=backoff,
                error=str(e),
                model=ai_model.value,
            )
            await asyncio.sleep(backoff)

    raise Exception("LLM call failed after multiple retries")


async def get_completion_stream(
    ai_model: AIModel,
    messages: list[LLMMessage],
    system_prompt: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """
    Run a single prompt through the LLM asynchronously and stream the response.

    Args:
        ai_model: The AI model to use.
        messages: The list of messages forming the conversation.
        system_prompt: The system prompt to use.
        temperature: The model temperature.
        max_tokens: The maximum number of tokens to generate.

    Yields:
        String chunks of the response.
    """
    api_messages = [msg.model_dump() for msg in messages]
    if system_prompt:
        api_messages.insert(0, {"role": "system", "content": system_prompt})

    params: dict[str, Any] = {
        "model": ai_model.value,
        "messages": api_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    try:
        logger.info("Sending messages to LLM for streaming", messages=api_messages)
        response = await litellm.acompletion(**params)

        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    except Exception as e:
        logger.error(
            "LLM streaming call failed",
            error=str(e),
            model=ai_model.value,
        )
        # In a production scenario, you might want to yield a specific
        # error message to the user. For now, we'll just log and stop.
        # yield "An error occurred while generating the response."
        raise


async def get_batch_completions(
    ai_model: AIModel,
    data: list[
        dict[str, Any]
    ],  # Each dict should contain 'messages' and 'system_prompt'
    response_type: type[T] | None,
    max_concurrency: int = 50,
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> list[LLMResponse[T]]:
    """Process data in batches using LLM asynchronously.

    Args:
        ai_model: The AI model to use.
        data: List of data items to process. Each item is a dict containing
              'messages' (list[LLMMessage]) and an optional 'system_prompt'.
        response_type: Pydantic model for structured output or None.
        max_concurrency: The maximum number of concurrent requests.
        temperature: The model temperature.
        max_tokens: The maximum number of tokens to generate.

    Returns:
        A list of LLMResponse objects.
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _process_item(item: dict[str, Any]) -> LLMResponse[T]:
        async with semaphore:
            return await get_completion(
                ai_model,
                item["messages"],
                response_type,
                item.get("system_prompt"),
                temperature,
                max_tokens,
            )

    logger.info("Starting batch processing", total_items=len(data))
    tasks = [_process_item(item) for item in data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Batch processing completed.")

    # Filter out exceptions and log them
    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                "Batch item failed", item_index=i, error=str(result), data=data[i]
            )
        else:
            successful_results.append(result)

    return successful_results
