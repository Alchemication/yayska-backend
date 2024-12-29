from enum import Enum

from pydantic import BaseModel, Field


class WhyImportant(BaseModel):
    practical_value: str = Field(
        ...,
        description="Brief, honest assessment of real-world usefulness in Irish context. Max 2 sentences. Keep it concise.",
    )
    future_learning: str = Field(
        ...,
        description="Key future applications, being realistic about importance. Max 2 sentences",
    )
    modern_relevance: str = Field(
        ...,
        description="Concise and critical view of concept's relevance in digital age (e.g., 'Less crucial with calculators but important for estimation').",
    )


class DifficultyStats(BaseModel):
    challenge_rate: int = Field(
        ...,
        description="Realistic rating (1-10) of difficulty, don't default to 7",
        ge=1,
        le=10,
    )
    common_barriers: list[str] = Field(
        ..., description="Top 3 most critical challenges, be specific", max_items=3
    )
    reassurance: str = Field(
        ...,
        description="Brief, concise, honest encouragement with Irish context (e.g., 'Like getting used to euro after pounds, it takes time but clicks')",
    )


class ParentGuide(BaseModel):
    key_points: list[str] = Field(
        ..., description="3 essential points parents must understand", max_items=3
    )
    quick_tips: list[str] = Field(
        ..., description="3 specific, actionable practice ideas", max_items=3
    )


class RealWorld(BaseModel):
    examples: list[str] = Field(
        ...,
        description="1-3 concrete examples from Irish daily life (shops, sports, weather, etc.)",
        max_items=3,
    )
    practice_ideas: list[str] = Field(
        ...,
        description="1-3 specific, detailed activities possible in typical Irish home",
        max_items=3,
    )
    irish_context: str = Field(
        ...,
        description="Concisely, how this concept appears specifically in Irish life or culture",
    )


class LearningPath(BaseModel):
    prerequisites: list[int] = Field(
        ..., description="IDs of concepts that should be mastered before this one"
    )
    success_indicators: list[str] = Field(
        ...,
        description="Observable signs that show a student has mastered this concept",
    )


class TimeEstimate(BaseModel):
    minutes_per_session: int = Field(
        ...,
        description="Recommended minutes per learning/practice session",
        ge=5,
        le=60,
    )
    sessions_per_week: int = Field(
        ..., description="Recommended number of sessions per week", ge=1, le=7
    )
    weeks_to_master: int = Field(
        ..., description="Estimated weeks needed to master the concept", ge=1, le=12
    )


class TimeGuide(BaseModel):
    quick_learner: TimeEstimate = Field(
        ...,
        description="Time estimates for students who typically grasp concepts quickly",
    )
    typical_learner: TimeEstimate = Field(
        ..., description="Time estimates for average-paced learners"
    )
    additional_support: TimeEstimate = Field(
        ..., description="Time estimates for students needing more support and practice"
    )


class AssessmentType(Enum):
    MULTIPLE_CHOICE = "multiple_choice"  # Best for testing specific knowledge points
    TRUE_FALSE = "true_false"  # Good for checking basic understanding
    FILL_GAP = "fill_gap"  # Useful for numbers and specific terms
    OPEN_DIALOGUE = "open_dialogue"  # For explaining understanding and reasoning
    PROBLEM_SOLVING = "problem_solving"  # For applying concept to real situations


class AssessmentApproaches(BaseModel):
    suitable_types: list[AssessmentType] = Field(
        ...,
        description="Only include assessment types that are genuinely effective for this concept, minimum 1, maximum 3",
    )
    reasoning: str = Field(
        ...,
        description="Very concise explanation of why these specific types work best. One sentence per type.",
    )


class IrishTerm(BaseModel):
    english: str = Field(..., description="Term in English")
    irish: str = Field(..., description="Term in Irish")
    pronunciation: str = Field(
        ..., description="Simple pronunciation guide in English phonetics"
    )
    example: str = Field(
        ..., description="Short example of usage in a classroom context"
    )


class IrishLanguageSupport(BaseModel):
    educational_terms: list[IrishTerm] = Field(
        ..., description="Essential educational vocabulary for this concept"
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
"""

user_prompt = """
Generate comprehensive metadata for this mathematical concept:

Context:
- Education Level: Primary
- Curriculum Area: {area_name}
- Subject: {subject_name}
- Strand: {strand_name}
- Strand Unit: {unit_name}
- Learning Outcome: {outcome_description}
- Concept: {concept_name}
- Concept ID: {concept_id}
- Concept Description: {concept_description}

Available Related Concepts (within same Learning Outcome):
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
