"""Test suite for LLM utility functions."""

import asyncio
import os

import pytest
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.utils.llm import AIModel, LLMMessage, get_completion

# Load environment variables from .env file
load_dotenv()


# Define a simple Pydantic model for structured response testing
class UserInfo(BaseModel):
    """Represents user information."""

    name: str = Field(..., description="The user's name")
    age: int = Field(..., description="The user's age")


# Models to test against. Tuple format: (AIModel, API_KEY_NAME, expected_capital)
TEST_MODELS = [
    (AIModel.CLAUDE_HAIKU_3_5, "ANTHROPIC_API_KEY", "Dublin"),
    (AIModel.GEMINI_FLASH_2_0_LITE, "GEMINI_API_KEY", "Dublin"),
]

# Use model ID for cleaner test names in pytest output
MODEL_IDS = [model[0].value for model in TEST_MODELS]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ai_model, api_key_name, expected_capital", TEST_MODELS, ids=MODEL_IDS
)
async def test_get_completion_unstructured(ai_model, api_key_name, expected_capital):
    """Test a simple unstructured call to the LLM."""
    if not os.getenv(api_key_name):
        pytest.skip(f"{api_key_name} not set")

    response = await get_completion(
        ai_model=ai_model,
        system_prompt="You are a helpful assistant.",
        messages=[
            LLMMessage(role="user", content="Hello! What is the capital of Ireland?")
        ],
        response_type=None,
    )

    print(f"[{ai_model.value}] Unstructured Response:", response.content)
    assert isinstance(response.content, str)
    assert expected_capital in response.content
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("ai_model, api_key_name, _", TEST_MODELS, ids=MODEL_IDS)
async def test_get_completion_structured(ai_model, api_key_name, _):
    """Test a structured call using a Pydantic model."""
    if not os.getenv(api_key_name):
        pytest.skip(f"{api_key_name} not set")

    response = await get_completion(
        ai_model=ai_model,
        system_prompt="Extract the user's information as a JSON object.",
        messages=[
            LLMMessage(
                role="user", content="My name is John Doe and I am 30 years old."
            )
        ],
        response_type=UserInfo,
    )

    print(f"[{ai_model.value}] Structured Response:", response.content)
    assert isinstance(response.content, UserInfo)
    assert response.content.name == "John Doe"
    assert response.content.age == 30
    assert response.usage_metadata["input_tokens"] > 0
    assert response.usage_metadata["output_tokens"] > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("ai_model, api_key_name, _", TEST_MODELS, ids=MODEL_IDS)
async def test_get_completion_multi_turn(ai_model, api_key_name, _):
    """Test a multi-turn conversation."""
    if not os.getenv(api_key_name):
        pytest.skip(f"{api_key_name} not set")

    messages = [
        LLMMessage(role="user", content="My name is Adam."),
        LLMMessage(
            role="assistant",
            content="Nice to meet you, Adam! How can I help you today?",
        ),
        LLMMessage(role="user", content="What is my name?"),
    ]

    response = await get_completion(
        ai_model=ai_model,
        system_prompt="You are a helpful assistant. Remember the user's name.",
        messages=messages,
        response_type=None,
    )

    print(f"[{ai_model.value}] Multi-turn Response:", response.content)
    assert isinstance(response.content, str)
    assert "Adam" in response.content


if __name__ == "__main__":
    # To run these tests, you need to have your .env file in the root
    # with ANTHROPIC_API_KEY and GEMINI_API_KEY set.
    # You can run this file directly: `python -m tests.utils.test_llm`
    # Or use pytest: `pytest tests/utils/test_llm.py`

    async def run_tests():
        """Run all tests, iterating through the defined models."""
        # Manually iterate through models for direct script execution
        for model, key, capital in TEST_MODELS:
            print(f"--- Testing model: {model.value} ---")
            if os.getenv(key):
                await test_get_completion_unstructured(model, key, capital)
                await test_get_completion_structured(model, key, None)
                await test_get_completion_multi_turn(model, key, None)
                print(f"--- Tests for {model.value} passed ---")
            else:
                print(f"--- Skipping tests for {model.value} ({key} not set) ---")
            print("\n")

    asyncio.run(run_tests())

    print("All test runs complete!")
