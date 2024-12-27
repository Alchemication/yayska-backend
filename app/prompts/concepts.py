from pydantic import BaseModel, Field


class Concept(BaseModel):
    """Represents a single concept for a specific year level."""

    learning_outcome_id: int = Field(..., description="Provided Learning Outcome ID")
    concept_name: str = Field(..., description="Cannonical concept name")
    concept_description: str = Field(
        ..., description="Short concept description, easy to understand"
    )
    complexity_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="""Complexity level from 1-5, where 1 is the simplest and 5 is 
            typically extremely complex for the age group""",
    )


class ConceptsResponse(BaseModel):
    """Represents the complete response from the LLM for generating concepts."""

    reasoning: str = Field(
        ...,
        description="Concise explanation of progression logic and developmental considerations",
    )
    concepts: list[Concept] = Field(..., description="List of concepts")


system_prompt = """
You are an expert in breaking down educational learning outcomes into specific, teachable concepts.
Your task is to identify key concepts that will be presented in an educational app for parents to support their child's learning.
Each concept should be clear, engaging, and practical.

Provide your response in JSON format with reasoning and structured concepts.
"""

user_prompt = """
Generate concepts for:
- Education Level: Primary
- Curriculum Area: {area_name}
- Subject: {subject_name}
- Strand: {strand_name}
- Strand Unit: {unit_name}
- Learning Outcome: {outcome_description}
- Learning Outcome ID: {outcome_id}

Generate a list of specific concepts that will be presented in the app. Each concept should be:
- Specific and measurable
- Appropriate for the year level
- Clearly related to the learning outcome
- Suitable for interactive learning
- Engaging for both parents and children
- Occassionaly fun and entertaining
"""
