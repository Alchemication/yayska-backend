from pydantic import BaseModel, Field


class Concept(BaseModel):
    """Represents a key milestone or concept that parents should monitor."""

    subject_id: int = Field(..., description="Subject ID")
    year_id: int = Field(..., description="School Year ID")
    concept_name: str = Field(..., description="Clear, parent-friendly concept name")
    concept_description: str = Field(
        ..., description="Brief, jargon-free description for parents"
    )
    learning_objectives: list[str] = Field(
        ..., description="Key skills or understanding the child should demonstrate"
    )
    display_order: int = Field(
        ..., description="Suggested order within the year's curriculum"
    )
    strand_reference: str = Field(
        ..., description="Optional reference to curriculum strand for teachers"
    )


class ConceptsResponse(BaseModel):
    """Represents the complete response for generating year-level concepts."""

    reasoning: str = Field(
        ..., description="Explanation of how concepts build through the year"
    )
    concepts: list[Concept] = Field(..., description="List of key concepts")


system_prompt = """
You are an expert in making the Irish primary curriculum accessible to parents.
Your role is to identify the absolute essential concepts that parents should track in their child's learning journey.

Key principles:
1. Less is more - focus only on major milestone concepts
2. Each concept should represent a significant leap in understanding
3. Concepts should be observable at home
4. Focus on foundational skills that impact future learning
5. Consider concepts that might cause learning difficulties

Remember: Parents should be able to keep all concepts in mind without feeling overwhelmed.
"""

user_prompt = """
Generate the essential concepts parents should monitor for:
- Education Level: Primary
- Subject: {subject_name}
- Subject ID: {subject_id}
- Year: {year_name}

Specific Requirements:
1. Number of Concepts:
   - Junior/Senior Infants: 3-4 concepts
   - 1st/2nd Class: 4-5 concepts
   - 3rd/4th Class: 5-6 concepts
   - 5th/6th Class: 6-7 concepts

2. Each concept must be:
   - A major milestone (not a small stepping stone)
   - Observable through everyday activities
   - Potentially challenging for some students

3. Focus on answering:
   - What MUST a {year_name} student understand in {subject_name}?
   - How can parents observe and support this learning?
   - What might be challenging for students?
"""
