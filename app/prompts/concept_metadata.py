from enum import Enum

from pydantic import BaseModel, Field


class WhyImportant(BaseModel):
    practical_value: str = Field(
        ...,
        description="One clear sentence about how this helps in daily life. Use examples like 'Helps with shopping' or 'Essential for reading timetables'.",
    )
    future_learning: str = Field(
        ...,
        description="One sentence linking to next year's learning or secondary school. Example: 'Foundation for fractions in 4th class'.",
    )
    modern_relevance: str = Field(
        ...,
        description="One honest sentence about usefulness with modern technology. Example: 'Still important despite calculators for quick estimates in shops'.",
    )


class DifficultyStats(BaseModel):
    challenge_rate: int = Field(
        ...,
        description="Rate 1-10 where 1='Most kids get it quickly' and 10='Most kids need extra help'. Be realistic, not every concept is difficult.",
        ge=1,
        le=10,
    )
    common_barriers: list[str] = Field(
        ...,
        description="2-3 specific obstacles parents can watch for. Each max 8 words.",
        max_items=3,
    )
    reassurance: str = Field(
        ...,
        description="One encouraging sentence with specific Irish context. Example: 'Like learning GAA rules - confusing at first but makes sense with practice'.",
    )


class ParentGuide(BaseModel):
    key_points: list[str] = Field(
        ...,
        description="3 must-know points for parents. Each max 10 words.",
        max_items=3,
    )
    quick_tips: list[str] = Field(
        ...,
        description="3 five-minute activities parents can do anywhere. Each max 12 words.",
        max_items=3,
    )


class RealWorld(BaseModel):
    examples: list[str] = Field(
        ...,
        description="2 everyday Irish examples. Use shops, sports, or daily routines. Each max 8 words.",
        max_items=2,
    )
    practice_ideas: list[str] = Field(
        ...,
        description="2 activities using items found in most Irish homes. Each max 12 words.",
        max_items=2,
    )
    irish_context: str = Field(
        ...,
        description="One sentence linking to Irish life. Example: 'Used when following recipes for traditional Irish dishes'.",
    )


class LearningPath(BaseModel):
    prerequisites: list[int] = Field(
        ..., description="Only list crucial prerequisite concept IDs, max 3"
    )
    success_indicators: list[str] = Field(
        ...,
        description="3 clear signs a child has mastered this. Each max 10 words.",
        max_items=3,
    )


class TimeEstimate(BaseModel):
    minutes_per_session: int = Field(
        ...,
        description="Realistic practice time that maintains child's attention",
        ge=5,
        le=30,
    )
    sessions_per_week: int = Field(
        ..., description="Manageable number of sessions for busy families", ge=1, le=5
    )
    weeks_to_master: int = Field(
        ...,
        description="Realistic weeks needed, considering school holidays",
        ge=1,
        le=8,
    )


class TimeGuide(BaseModel):
    quick_learner: TimeEstimate = Field(
        ...,
        description="For children who usually grasp new ideas quickly",
    )
    typical_learner: TimeEstimate = Field(
        ..., description="For most children in the class"
    )
    additional_support: TimeEstimate = Field(
        ..., description="For children who benefit from extra practice time"
    )


class AssessmentType(Enum):
    MULTIPLE_CHOICE = "multiple_choice"  # Best for testing specific knowledge points
    TRUE_FALSE = "true_false"  # Good for checking basic understanding
    FILL_GAP = "fill_gap"  # Useful for numbers and specific terms
    OPEN_DIALOGUE = "open_dialogue"  # For explaining understanding and reasoning
    PROBLEM_SOLVING = "problem_solving"  # For applying concept to real situations


class AssessmentApproaches(BaseModel):
    suitable_types: list[AssessmentType] = Field(
        ..., description="Choose 1-2 most parent-friendly assessment types", max_items=2
    )
    reasoning: str = Field(
        ...,
        description="One clear sentence explaining how parents can check understanding at home",
    )


class IrishTerm(BaseModel):
    english: str = Field(..., description="Common term in English")
    irish: str = Field(..., description="Term in Irish")
    pronunciation: str = Field(
        ..., description="Simple pronunciation using rhyming English words"
    )
    example: str = Field(..., description="Short, practical example max 8 words")


class IrishLanguageSupport(BaseModel):
    educational_terms: list[IrishTerm] = Field(
        ...,
        description="Only 2-3 most essential terms needed for homework help",
        max_items=3,
    )


class ConceptMetadataResponse(BaseModel):
    concept_id: int = Field(..., description="ID of the concept")
    why_important: WhyImportant
    difficulty_stats: DifficultyStats
    parent_guide: ParentGuide
    real_world: RealWorld
    learning_path: LearningPath
    time_guide: TimeGuide
    assessment_approaches: AssessmentApproaches
    irish_language_support: IrishLanguageSupport


system_prompt = """
You are an expert educational content developer with deep understanding of:
- The Irish primary education curriculum
- Irish cultural context and educational values
- Irish everyday life and practical applications
- Irish sense of humour and communication style

When generating content:
- Be honest about a concept's real-world usefulness
- Include subtle Irish humor where appropriate
- Reference Irish-specific contexts (shops like Dunnes, SuperValu; local sports; Irish weather)
- Challenge traditional views if a topic is less relevant in modern life
- Consider both English and Irish-medium education contexts

When rating difficulty:
1-3: Most students grasp quickly with minimal practice
4-6: Requires regular practice but achievable for most
7-8: Challenging concept requiring sustained effort
9-10: Complex concept that many students struggle with

Keep all responses very concise and practical. Avoid educational jargon unless absolutely necessary.

"Treat parents as busy people who need quick, practical information. If something can be said in fewer words, do it."
"""

user_prompt = """
Generate comprehensive metadata for this concept:

Context:
- Education Level: Primary
- Subject: {subject_name}
- School Year: {year_name}
- Concept: {concept_name}
- Concept ID: {concept_id}
- Concept Description: {concept_description}

Available Related Concepts (within same Subject and School Year):
{related_concepts}

Available assessment types:
- MULTIPLE_CHOICE: Best for testing specific knowledge points and understanding of concepts with clear, distinct options
- TRUE_FALSE: Good for checking basic understanding and common misconceptions
- FILL_GAP: Useful for numbers, specific terms, and completing patterns or sequences
- OPEN_DIALOGUE: For explaining understanding, reasoning, and deeper comprehension
- PROBLEM_SOLVING: For applying concept to real situations and demonstrating practical understanding

Requirements:
1. All content must be age-appropriate for the specified education level
2. Assessment questions should be clearly written and suitable for digital/AI implementation
3. Time estimates should be realistic and specific
4. Irish language support should include only essential vocabulary and phrases
5. Examples should be practical and relevant to Irish context
6. Prerequisites should reference specific concept IDs from the provided list
7. All fields in the Pydantic model must be populated with relevant, specific content

Please provide the metadata following the exact structure defined in the Pydantic model, ensuring all fields are populated with high-quality, relevant content.
"""
