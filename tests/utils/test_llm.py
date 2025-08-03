"""Test suite for LLM utility functions."""

import asyncio
import os

import litellm
import pytest
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.utils.llm import AIModel, LLMMessage, ReasoningEffort, get_completion

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
    (AIModel.GPT_4O_MINI, "OPENAI_API_KEY", "Dublin"),
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
    assert response.usage["prompt_tokens"] > 0
    assert response.usage["completion_tokens"] > 0


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
    assert response.usage["prompt_tokens"] > 0
    assert response.usage["completion_tokens"] > 0


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


@pytest.mark.asyncio
async def test_caching_functionality():
    """Test that caching works correctly for both string and Pydantic responses."""
    # Use the fastest/cheapest model for caching tests
    ai_model = AIModel.GEMINI_FLASH_2_0_LITE
    api_key_name = "GEMINI_API_KEY"

    if not os.getenv(api_key_name):
        pytest.skip(f"{api_key_name} not set")

    import time

    test_timestamp = str(int(time.time()))  # Unique timestamp for this test run

    # Test 1: String response caching
    print("Testing string response caching...")
    messages_str = [
        LLMMessage(role="user", content=f"Say exactly: 'Cache test {test_timestamp}'")
    ]

    # First call - should hit API
    response1 = await get_completion(
        ai_model=ai_model,
        messages=messages_str,
        response_type=None,
        cache_name=f"test_string_cache_{test_timestamp}",
    )

    # Second call - should hit cache
    response2 = await get_completion(
        ai_model=ai_model,
        messages=messages_str,
        response_type=None,
        cache_name=f"test_string_cache_{test_timestamp}",
    )

    # Assertions for string caching
    assert isinstance(response1.content, str)
    assert isinstance(response2.content, str)
    assert response1.content == response2.content
    assert response1.usage.get("cached") != True  # First call not cached
    assert response2.usage.get("cached") == True  # Second call cached
    print("✅ String caching test passed!")

    # Test 2: Pydantic response caching
    print("Testing Pydantic response caching...")
    messages_pyd = [
        LLMMessage(
            role="user",
            content=f"My name is Test User {test_timestamp} and I am 25 years old.",
        )
    ]

    # First call - should hit API
    response3 = await get_completion(
        ai_model=ai_model,
        system_prompt="Extract the user's information as a JSON object.",
        messages=messages_pyd,
        response_type=UserInfo,
        cache_name=f"test_pydantic_cache_{test_timestamp}",
    )

    # Second call - should hit cache
    response4 = await get_completion(
        ai_model=ai_model,
        system_prompt="Extract the user's information as a JSON object.",
        messages=messages_pyd,
        response_type=UserInfo,
        cache_name=f"test_pydantic_cache_{test_timestamp}",
    )

    # Assertions for Pydantic caching
    assert isinstance(response3.content, UserInfo)
    assert isinstance(response4.content, UserInfo)
    assert response3.content.name == response4.content.name
    assert response3.content.age == response4.content.age
    assert f"Test User {test_timestamp}" in response3.content.name
    assert response3.usage.get("cached") != True  # First call not cached
    assert response4.usage.get("cached") == True  # Second call cached
    print("✅ Pydantic caching test passed!")

    # Test 3: Cache isolation
    print("Testing cache isolation...")
    messages_iso = [
        LLMMessage(role="user", content=f"Say 'isolation test {test_timestamp}'")
    ]

    # Call with different cache name - should NOT be cached
    response5 = await get_completion(
        ai_model=ai_model,
        messages=messages_iso,
        response_type=None,
        cache_name=f"different_cache_{test_timestamp}",
    )

    assert response5.usage.get("cached") != True  # Should not be cached
    print("✅ Cache isolation test passed!")


@pytest.mark.asyncio
async def test_reasoning_effort_parameter():
    """Test the reasoning_effort parameter with a model that supports it."""
    # Use GPT_O4_MINI which supports reasoning_effort
    ai_model = AIModel.GPT_O4_MINI
    api_key_name = "OPENAI_API_KEY"

    # O-series models don't support temperature<1.0. Only temperature=1 is supported. To drop unsupported openai params from the call, set `litellm.drop_params = True`
    litellm.drop_params = True

    if not os.getenv(api_key_name):
        pytest.skip(f"{api_key_name} not set")

    # Test with different reasoning effort levels
    for effort in [ReasoningEffort.LOW, ReasoningEffort.MEDIUM]:
        response = await get_completion(
            ai_model=ai_model,
            system_prompt="You are a helpful assistant. Please think through your response carefully.",
            messages=[
                LLMMessage(
                    role="user", content="Solve this step by step: What is 15 * 23 + 7?"
                )
            ],
            response_type=None,
            reasoning_effort=effort,
        )

        print(
            f"[{ai_model.value}] Reasoning effort '{effort}' Response:",
            response.content,
        )
        assert isinstance(response.content, str)
        assert "352" in response.content  # Expected answer: 15 * 23 + 7 = 345 + 7 = 352
        assert response.usage["prompt_tokens"] > 0
        assert response.usage["completion_tokens"] > 0

    # Test that reasoning_effort is included in cache key (different efforts should be cached separately)
    import time

    test_timestamp = str(int(time.time()))

    messages = [
        LLMMessage(
            role="user", content=f"Say exactly: 'Reasoning test {test_timestamp}'"
        )
    ]

    # First call with "low" reasoning effort
    response_low = await get_completion(
        ai_model=ai_model,
        messages=messages,
        response_type=None,
        reasoning_effort=ReasoningEffort.LOW,
        cache_name=f"reasoning_cache_{test_timestamp}",
    )

    # Second call with "high" reasoning effort - should NOT be cached
    response_high = await get_completion(
        ai_model=ai_model,
        messages=messages,
        response_type=None,
        reasoning_effort=ReasoningEffort.HIGH,
        cache_name=f"reasoning_cache_{test_timestamp}",
    )

    # Third call with "low" reasoning effort again - should be cached
    response_low_cached = await get_completion(
        ai_model=ai_model,
        messages=messages,
        response_type=None,
        reasoning_effort=ReasoningEffort.LOW,
        cache_name=f"reasoning_cache_{test_timestamp}",
    )

    # Assertions
    assert response_low.usage.get("cached") != True  # First low call not cached
    assert (
        response_high.usage.get("cached") != True
    )  # High call not cached (different key)
    assert response_low_cached.usage.get("cached") == True  # Second low call cached

    print("✅ Reasoning effort parameter test passed!")


if __name__ == "__main__":
    # To run these tests, you need to have your .env file in the root
    # with ANTHROPIC_API_KEY and GEMINI_API_KEY set.
    # You can run this file directly: `python -m tests.utils.test_llm`
    # Or use pytest: `pytest tests/utils/test_llm.py`

    async def run_tests():
        """Run all tests, iterating through the defined models."""
        # Test caching functionality first
        print("--- Testing caching functionality ---")
        if os.getenv("GEMINI_API_KEY"):
            await test_caching_functionality()
            print("--- Caching tests passed ---\n")
        else:
            print("--- Skipping caching tests (GEMINI_API_KEY not set) ---\n")

        # Test reasoning effort functionality
        print("--- Testing reasoning effort functionality ---")
        if os.getenv("OPENAI_API_KEY"):
            await test_reasoning_effort_parameter()
            print("--- Reasoning effort tests passed ---\n")
        else:
            print("--- Skipping reasoning effort tests (OPENAI_API_KEY not set) ---\n")

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
