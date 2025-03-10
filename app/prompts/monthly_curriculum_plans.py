from typing import List

from pydantic import BaseModel, Field


class PriorityConcepts(BaseModel):
    essential: List[int] = Field(
        ..., description="3-5 highest-impact concepts parents should focus on"
    )
    important: List[int] = Field(
        ..., description="5-8 additional concepts for parents with more time"
    )
    supplementary: List[int] = Field(
        ..., description="All other concepts taught this month"
    )


class MonthlyPlan(BaseModel):
    month: str = Field(..., description="Month name")
    focus: str = Field(
        ..., description="Brief description of the educational focus for this month"
    )
    rationale: str = Field(
        ..., description="Educational reasoning for this month's concept selection"
    )
    concepts: PriorityConcepts = Field(
        ..., description="Concepts organized by priority level"
    )


class YearlyPlanResponse(BaseModel):
    year_name: str = Field(..., description="Name of the school year")
    year_id: int = Field(..., description="ID of the school year")
    monthly_plans: List[MonthlyPlan] = Field(
        ..., description="Plans for each month of the school year"
    )


system_prompt = """
System Prompt:
You are an expert in the Irish primary school curriculum with extensive knowledge of how concepts are taught throughout the school year. Your task is to create a parent-friendly curriculum plan that prioritizes concepts based on their impact and practicality for home support.

When prioritizing concepts, consider:
1. Which concepts are most foundational for future learning
2. Which concepts can be meaningfully supported by parents at home
3. Which concepts have the greatest impact on a child's academic progress
4. Which concepts align with typical teaching focus in Irish schools each month

Remember that parents have limited time and need clear guidance on where to focus their efforts for maximum impact.
"""

user_prompt = """
Create a parent-friendly monthly curriculum plan for Junior Infants (first year of primary school in Ireland), organizing the following concepts into a logical teaching sequence from September to June.

For each month, provide:
1. A clear educational focus statement (1 sentence)
2. A brief rationale explaining the educational reasoning (1-2 sentences)
3. Concepts organized by THREE priority levels:
   - ESSENTIAL (3-5 concepts): The absolute must-focus areas for busy parents
   - IMPORTANT (5-8 concepts): Additional concepts for parents with more time
   - SUPPLEMENTARY: All other concepts taught that month

When determining ESSENTIAL concepts, prioritize those that:
- Are foundational building blocks for future learning
- Can be easily supported through everyday home activities
- Have the greatest impact on a child's overall development
- Are typically emphasized in Irish classrooms that month

Here are the concepts to organize:

<CONCEPT-INFO>
Year ID: {year_id}
Year Name: {year_name}

Concepts:
--------------------------------
{concepts}
--------------------------------
</CONCEPT-INFO>

Format your response as a JSON object.
"""
