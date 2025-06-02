from pydantic import BaseModel

from app.utils.llm import AIPlatform, GoogleModel, batch_process_with_llm


class Joke(BaseModel):
    emoji: str
    joke: str


def test_llm():
    result = batch_process_with_llm(
        ai_platform=AIPlatform.GOOGLE,
        ai_model=GoogleModel.GEMINI_FLASH_2_5,
        data=[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
        system_prompt="You are a helpful assistant.",
        user_prompt="Tell me a joke about a {name} who is {age} years old.",
        response_type=Joke,
    )
    print(result)


if __name__ == "__main__":
    test_llm()
