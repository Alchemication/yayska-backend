"""Test suite for LLM utility functions."""

import asyncio
import os

import pytest
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.utils.llm import (
    AIPlatform,
    AnthropicModel,
    GoogleModel,
    LLMMessage,
    allm_invoke,
)

# Load environment variables from .env file
load_dotenv()


# Define a simple Pydantic model for structured response testing
class UserInfo(BaseModel):
    """Represents user information."""

    name: str = Field(..., description="The user's name")
    age: int = Field(..., description="The user's age")


@pytest.mark.asyncio
async def test_anthropic_unstructured_invoke():
    """Test a simple unstructured call to Anthropic."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    response = await allm_invoke(
        ai_platform=AIPlatform.ANTHROPIC,
        ai_model=AnthropicModel.CLAUDE_HAIKU_3_5,
        system_prompt="You are a helpful assistant.",
        messages=[
            LLMMessage(role="user", content="Hello! What is the capital of Ireland?")
        ],
        response_type=None,
    )

    print("Anthropic Unstructured Response:", response.content)
    assert isinstance(response.content, str)
    assert "Dublin" in response.content
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0


@pytest.mark.asyncio
async def test_anthropic_structured_invoke():
    """Test a structured call to Anthropic using a Pydantic model."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    response = await allm_invoke(
        ai_platform=AIPlatform.ANTHROPIC,
        ai_model=AnthropicModel.CLAUDE_HAIKU_3_5,
        system_prompt="Extract the user's information as a JSON object.",
        messages=[
            LLMMessage(
                role="user", content="My name is John Doe and I am 30 years old."
            )
        ],
        response_type=UserInfo,
    )

    print("Anthropic Structured Response:", response.content)
    assert isinstance(response.content, UserInfo)
    assert response.content.name == "John Doe"
    assert response.content.age == 30
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0


@pytest.mark.asyncio
async def test_google_unstructured_invoke():
    """Test a simple unstructured call to Google."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    response = await allm_invoke(
        ai_platform=AIPlatform.GOOGLE,
        ai_model=GoogleModel.GEMINI_FLASH_2_0_LITE,
        system_prompt="You are a helpful assistant.",
        messages=[
            LLMMessage(role="user", content="Hello! What is the capital of France?")
        ],
        response_type=None,
    )

    print("Google Unstructured Response:", response.content)
    assert isinstance(response.content, str)
    assert "Paris" in response.content
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0


@pytest.mark.asyncio
async def test_google_structured_invoke():
    """Test a structured call to Google using a Pydantic model."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    response = await allm_invoke(
        ai_platform=AIPlatform.GOOGLE,
        ai_model=GoogleModel.GEMINI_FLASH_2_0_LITE,
        system_prompt="Extract the user's information as a JSON object.",
        messages=[
            LLMMessage(
                role="user", content="My name is Jane Doe and I am 25 years old."
            )
        ],
        response_type=UserInfo,
    )

    print("Google Structured Response:", response.content)
    assert isinstance(response.content, UserInfo)
    assert response.content.name == "Jane Doe"
    assert response.content.age == 25
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0


@pytest.mark.asyncio
async def test_anthropic_multi_turn_invoke():
    """Test a multi-turn conversation with Anthropic."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    messages = [
        LLMMessage(role="user", content="My name is Adam."),
        LLMMessage(
            role="assistant",
            content="Nice to meet you, Adam! How can I help you today?",
        ),
        LLMMessage(role="user", content="What is my name?"),
    ]

    response = await allm_invoke(
        ai_platform=AIPlatform.ANTHROPIC,
        ai_model=AnthropicModel.CLAUDE_HAIKU_3_5,
        system_prompt="You are a helpful assistant. Remember user's name.",
        messages=messages,
        response_type=None,
    )

    print("Anthropic Multi-turn Response:", response.content)
    assert isinstance(response.content, str)
    assert "Adam" in response.content


@pytest.mark.asyncio
async def test_google_multi_turn_invoke():
    """Test a multi-turn conversation with Google."""
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    messages = [
        LLMMessage(role="user", content="My name is Jane."),
        LLMMessage(
            role="assistant",
            content="Nice to meet you, Jane! How can I help you today?",
        ),
        LLMMessage(role="user", content="What is my name?"),
    ]

    response = await allm_invoke(
        ai_platform=AIPlatform.GOOGLE,
        ai_model=GoogleModel.GEMINI_FLASH_2_0_LITE,
        system_prompt="You are a helpful assistant. Remember the user's name.",
        messages=messages,
        response_type=None,
    )

    print("Google Multi-turn Response:", response.content)
    assert isinstance(response.content, str)
    assert "Jane" in response.content


if __name__ == "__main__":
    # To run these tests, you need to have your .env file in the root
    # with ANTHROPIC_API_KEY and GEMINI_API_KEY set.
    # You can run this file directly: `python -m tests.utils.test_llm`
    # Or use pytest: `pytest tests/utils/test_llm.py`
    asyncio.run(test_anthropic_unstructured_invoke())
    asyncio.run(test_anthropic_structured_invoke())
    asyncio.run(test_google_unstructured_invoke())
    asyncio.run(test_google_structured_invoke())
    asyncio.run(test_anthropic_multi_turn_invoke())
    asyncio.run(test_google_multi_turn_invoke())

    print("All tests passed!")
