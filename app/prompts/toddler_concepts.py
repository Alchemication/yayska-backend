from pydantic import BaseModel, Field


class DevelopmentalConcept(BaseModel):
    """Developmental milestone concept for pre-school children."""

    subject_id: int = Field(..., description="Developmental domain ID")
    year_id: int = Field(..., description="Age range ID")
    concept_name: str = Field(..., description="Clear, parent-friendly milestone name")
    concept_description: str = Field(
        ..., description="What parents should observe - jargon-free description"
    )
    learning_objectives: list[str] = Field(
        ..., description="Observable behaviors/skills that indicate mastery"
    )
    display_order: int = Field(
        ..., description="Typical developmental sequence within age range"
    )
    strand_reference: str = Field(
        default="", description="Empty for pre-school - no formal curriculum"
    )


class DevelopmentalConceptsResponse(BaseModel):
    """Complete response for generating age-appropriate developmental concepts."""

    reasoning: str = Field(
        ...,
        description="Explanation of typical development patterns for this age/domain",
    )
    concepts: list[DevelopmentalConcept] = Field(
        ..., description="List of key developmental milestones"
    )


system_prompt = """
You are an expert in early childhood development and making developmental milestones accessible to busy Irish parents.
Your role is to identify essential developmental concepts that parents should observe and gently support at home.

Key principles:
1. Focus on observable, meaningful milestones - not tiny increments
2. Each concept should represent significant developmental progress
3. Consider individual variation - some children develop faster/slower
4. Emphasize what parents can naturally observe during daily routines
5. Keep cultural context relevant to modern Irish families

Remember: Parents want to support their child's development without creating pressure or anxiety, but they also want to teach their child to be independent and resilient.
"""

user_prompt = """
Generate essential developmental concepts for busy parents to observe:
- Age Range: $area_name
- Age Range ID: $year_id
- Developmental Domain: $subject_name
- Domain ID: $subject_id

Requirements:
1. Number of Concepts: 4-6 key milestones per age range
2. Each concept must be:
   - A significant developmental leap (not small steps)
   - Observable during normal family life (meals, play, outings)
   - Achievable by most children in this age range
   - Supportive of future learning and independence

3. Focus on answering:
   - What major development should I watch for in my $area_name child?
   - How can I recognize this milestone in everyday situations?
   - How can I naturally encourage this development?
   
4. Consider typical Irish family life: busy schedules, extended family involvement, outdoor play culture.
"""
