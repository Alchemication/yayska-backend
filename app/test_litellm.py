#!/usr/bin/env python3
"""
Test script for the new simplified LLM utilities.
Demonstrates text responses, structured responses, and reasoning capabilities.
"""

import asyncio

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.utils.llm import AIModel, LLMMessage, ReasoningEffort, get_completion

# Load environment variables
load_dotenv()


class MathResponse(BaseModel):
    """Example structured response for math problems."""

    calculation: str = Field(..., description="The step-by-step calculation")
    result: float = Field(..., description="The numerical result")
    is_prime: bool = Field(..., description="Whether the result is a prime number")
    explanation: str = Field(..., description="Explanation of the primality check")


async def test_text_response():
    """Test basic text response without structure."""
    print("🧪 Testing text response...")

    messages = [LLMMessage(role="user", content="What is 2 + 2? Keep it brief.")]

    response = await get_completion(
        ai_model=AIModel.CLAUDE_HAIKU_3_5,
        messages=messages,
        temperature=0.1,
    )

    print(f"✅ Content: {response.content}")
    print(f"📊 Usage: {response.usage}")
    print()


async def test_structured_response():
    """Test structured response with Pydantic model."""
    print("🧪 Testing structured response...")

    messages = [
        LLMMessage(
            role="user",
            content="What is 15 + 27? Then multiply by 1.33334. Is the result prime?",
        )
    ]

    response = await get_completion(
        ai_model=AIModel.CLAUDE_HAIKU_3_5,
        messages=messages,
        response_type=MathResponse,
        temperature=0.1,
    )

    print(f"✅ Structured content: {response.content}")
    print(f"📊 Usage: {response.usage}")
    print()


async def test_reasoning_model():
    """Test reasoning model with reasoning_effort."""
    print("🧪 Testing reasoning model...")

    messages = [
        LLMMessage(
            role="user",
            content="What is 15 + 27? Then multiply by 1.33334. Is the result prime? Think carefully.",
        )
    ]

    response = await get_completion(
        ai_model=AIModel.CLAUDE_SONNET_3_7,  # Supports reasoning
        messages=messages,
        response_type=MathResponse,
        reasoning_effort=ReasoningEffort.MEDIUM,
        temperature=0.1,
    )

    print(f"✅ Structured content: {response.content}")
    if response.reasoning_content:
        print(f"🧠 Reasoning (truncated): {response.reasoning_content[:200]}...")
    print(f"📊 Usage: {response.usage}")
    print()


async def test_caching():
    """Test caching functionality."""
    print("🧪 Testing caching...")

    messages = [LLMMessage(role="user", content="What is the capital of France?")]

    # First call - should hit the API
    response1 = await get_completion(
        ai_model=AIModel.CLAUDE_HAIKU_3_5,
        messages=messages,
        cache_name="test_cache",
    )

    # Second call - should hit cache
    response2 = await get_completion(
        ai_model=AIModel.CLAUDE_HAIKU_3_5,
        messages=messages,
        cache_name="test_cache",
    )

    print(f"✅ First response usage: {response1.usage}")
    print(f"✅ Second response usage: {response2.usage}")
    print(f"✅ Cache hit: {'cached' in response2.usage}")
    print()


async def main():
    """Run all tests."""
    print("=== LLM Utils Test Suite ===\n")

    try:
        await test_text_response()
        await test_structured_response()
        await test_reasoning_model()
        await test_caching()
        print("🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
