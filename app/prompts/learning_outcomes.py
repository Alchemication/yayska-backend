from pydantic import BaseModel, Field


class LearningOutcome(BaseModel):
    """Represents a single learning outcome for a specific year level."""

    unit_id: int = Field(..., description="Provided Strand Unit ID")
    year_id: int = Field(..., description="School year ID from the provided mapping")
    description: str = Field(..., description="Clear, measurable outcome description")
    prerequisites: str = Field(
        ..., description="Concise description of prerequisites before this outcome"
    )
    complexity_level: int = Field(
        ..., ge=1, le=5, description="Complexity level from 1-5"
    )


class LearningOutcomesResponse(BaseModel):
    """Represents the complete response from the LLM for learning outcomes."""

    reasoning: str = Field(
        ...,
        description="Concise explanation of progression logic and developmental considerations",
    )
    learning_outcomes: list[LearningOutcome] = Field(
        ..., description="List of learning outcomes"
    )


system_prompt = """
You are an expert in the Irish Primary School curriculum design with deep understanding of educational progression and child development. Your task is to generate appropriate learning outcomes that:
1. Follow official curriculum guidelines
2. Show clear progression across years
3. Are measurable and observable
4. Are appropriate for the age group
5. Build upon previous knowledge

Provide your response in JSON format with reasoning and structured learning outcomes. Keep the learning outcomes specific but not too granular, as they will be further broken down into concepts later.
"""

user_prompt = """
Generate learning outcomes for:
- Education Level: Primary
- Curriculum Area: {area_name}
- Subject: {subject_name}
- Strand: {strand_name}
- Strand Unit: {unit_name}
- Strand Unit ID: {unit_id}

These learning outcomes will be used by an AI tutor to:
- Assess student understanding
- Track progress
- Identify gaps in knowledge
- Provide targeted practice

Therefore, each learning outcome should be:
- Clearly measurable through digital assessment
- Specific enough for automated evaluation
- Have clear success criteria
- Testable through various question types (multiple choice, numerical input, etc.)

Available School Years:
{{
    "Junior Infants": 1,
    "Senior Infants": 2,
    "First Class": 3,
    "Second Class": 4,
    "Third Class": 5,
    "Fourth Class": 6,
    "Fifth Class": 7,
    "Sixth Class": 8
}}
"""
