from pydantic import BaseModel

from app.utils.llm import AIPlatform, GoogleModel, llm_invoke


class Joke(BaseModel):
    emoji: str
    joke: str


def test_llm():
    result = llm_invoke(
        ai_platform=AIPlatform.GOOGLE,
        ai_model=GoogleModel.GEMINI_FLASH_2_0_LITE,
        data={"name": "John", "age": 30},
        system_prompt="You are a helpful assistant.",
        user_prompt="Tell me a joke about a {name} who is {age} years old.",
        response_type=Joke,
        temperature=0.6,
    )
    print(result.content)
    print(result.usage_metadata)


if __name__ == "__main__":
    test_llm()
