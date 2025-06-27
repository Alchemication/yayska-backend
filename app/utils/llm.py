"""Utility functions for LLM-related operations."""

import asyncio
from enum import Enum
from typing import Any, Generic, TypeVar, cast

import google.generativeai as genai
from anthropic import AsyncAnthropic
from anthropic.types import Message
from google.generativeai.protos import FunctionCall
from google.generativeai.types import GenerateContentResponse
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str  # "user" or "assistant"
    content: str


class AIPlatform(Enum):
    """Enum for AI platforms."""

    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class AnthropicModel(Enum):
    """Enum for Anthropic models."""

    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"
    CLAUDE_SONNET_3_7 = "claude-3-7-sonnet-20250219"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"


class GoogleModel(Enum):
    """Enum for Google models."""

    GEMINI_FLASH_2_0_LITE = "gemini-2.0-flash-lite"
    GEMINI_FLASH_2_0 = "gemini-2.0-flash"
    GEMINI_FLASH_2_5 = "gemini-2.5-flash"
    GEMINI_PRO_2_5 = "gemini-2.5-pro-preview-05-06"


class LLMResponse(BaseModel, Generic[T]):
    """Wrapper class to unify response format and provide token usage tracking."""

    content: T | str
    usage_metadata: dict | None = {}
    raw_response: Any = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


def _pydantic_to_tool_schema(model: type[T]) -> dict[str, Any]:
    """Convert a Pydantic model to an Anthropic tool schema.

    Args:
        model: The Pydantic model class.

    Returns:
        A dictionary representing the tool schema.
    """
    schema = model.model_json_schema()
    return {
        "name": schema.get("title", model.__name__),
        "description": schema.get(
            "description", f"Extract {schema.get('title', model.__name__)}"
        ),
        "input_schema": schema,
    }


async def _invoke_anthropic(
    client: AsyncAnthropic,
    model_name: str,
    system_prompt: str | None,
    messages: list[LLMMessage],
    response_type: type[T] | None,
    temperature: float,
    max_tokens: int,
) -> LLMResponse[T]:
    """Invoke an Anthropic model.

    Args:
        client: The AsyncAnthropic client.
        model_name: The name of the model to use.
        system_prompt: The system prompt.
        messages: The list of messages in the conversation.
        response_type: The Pydantic model for structured output.
        temperature: The model temperature.
        max_tokens: The maximum number of tokens to generate.

    Returns:
        An LLMResponse object.
    """
    api_messages = [message.model_dump() for message in messages]

    params: dict[str, Any] = {
        "model": model_name,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": api_messages,
    }
    if system_prompt:
        params["system"] = system_prompt

    if response_type:
        tool_schema = _pydantic_to_tool_schema(response_type)
        params["tools"] = [tool_schema]
        params["tool_choice"] = {"type": "tool", "name": tool_schema["name"]}

    response: Message = await client.messages.create(**params)
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    if response_type:
        tool_use = next(
            (block for block in response.content if block.type == "tool_use"), None
        )
        if not tool_use:
            raise ValueError("No tool use block found in response")
        content = response_type.model_validate(tool_use.input)
    else:
        content = response.content[0].text

    return LLMResponse(content=content, usage_metadata=usage, raw_response=response)


async def allm_invoke(
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
    messages: list[LLMMessage],
    response_type: type[T] | None,
    system_prompt: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> LLMResponse[T]:
    """Run a single prompt through the LLM asynchronously with retry logic.

    Args:
        ai_platform: The AI platform to use.
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

            if ai_platform == AIPlatform.ANTHROPIC:
                if not isinstance(ai_model, AnthropicModel):
                    raise ValueError(f"Invalid Anthropic model: {ai_model}")
                client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                return await _invoke_anthropic(
                    client,
                    ai_model.value,
                    system_prompt,
                    messages,
                    response_type,
                    current_temp,
                    max_tokens,
                )

            if ai_platform == AIPlatform.GOOGLE:
                if not isinstance(ai_model, GoogleModel):
                    raise ValueError(f"Invalid Google model: {ai_model}")
                genai.configure(api_key=settings.GEMINI_API_KEY)

                tool_config = None
                tools = None
                if response_type:
                    tools = [response_type]
                    tool_config = {
                        "function_calling_config": {
                            # "mode" can be "auto", "any", or "none"
                            "mode": "any",
                            "allowed_function_names": [
                                response_type.model_json_schema().get(
                                    "title", response_type.__name__
                                )
                            ],
                        }
                    }

                model = genai.GenerativeModel(
                    ai_model.value,
                    generation_config={
                        "temperature": current_temp,
                        "max_output_tokens": max_tokens,
                    },
                    system_instruction=system_prompt,
                    tools=tools,
                    tool_config=tool_config,
                )

                # Convert messages to the format expected by the Google API
                api_messages = []
                for msg in messages:
                    # Google uses 'model' for the assistant's role
                    role = "model" if msg.role == "assistant" else "user"
                    api_messages.append({"role": role, "parts": [msg.content]})

                response: GenerateContentResponse = await model.generate_content_async(
                    api_messages
                )

                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }

                if response_type:
                    if (
                        not response.candidates
                        or not response.candidates[0].content.parts
                        or not response.candidates[0].content.parts[0].function_call
                    ):
                        text_response = response.text
                        logger.error(
                            "Google model failed to return a function call.",
                            response_text=text_response,
                        )
                        raise ValueError(
                            f"No function call found in response. Model returned: '{text_response}'"
                        )

                    function_call = cast(
                        FunctionCall,
                        response.candidates[0].content.parts[0].function_call,
                    )
                    args = {key: val for key, val in function_call.args.items()}
                    content = response_type.model_validate(args)
                else:
                    content = response.text

                return LLMResponse(
                    content=content, usage_metadata=usage, raw_response=response
                )

            raise ValueError(f"Invalid AI platform: {ai_platform}")

        except (ValidationError, ValueError, Exception) as e:
            if (
                isinstance(e, ValidationError)
                or "No tool use block found" in str(e)
                or "No function call found" in str(e)
            ):
                validation_error = True
                error_type = "Validation error"
            else:
                error_type = "API error"

            if attempt == 2:
                logger.error(f"{error_type} failed after 3 attempts", error=str(e))
                raise

            is_rate_limit = "429" in str(e) or "rate limit" in str(e).lower()
            backoff = 5 * (2**attempt) if is_rate_limit else 2

            logger.warning(
                f"Retrying after {error_type}",
                attempt=attempt + 1,
                backoff_seconds=backoff,
                error=str(e),
            )
            await asyncio.sleep(backoff)

    raise Exception("LLM call failed after multiple retries")


async def allm_batch(
    ai_platform: AIPlatform,
    ai_model: AnthropicModel | GoogleModel,
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
        ai_platform: The AI platform to use.
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
            return await allm_invoke(
                ai_platform,
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
