from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/units/{unit_id}/concepts")
async def get_unit_concepts(
    unit_id: int, year_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get concepts for a specific unit and school year, including metadata.
    """
    query = text("""
        SELECT 
            c.id,
            c.concept_name,
            c.concept_description,
            c.difficulty_level,
            cm.why_important,
            cm.difficulty_stats,
            cm.parent_guide,
            cm.real_world,
            cm.learning_path,
            cm.time_guide,
            cm.assessment_approaches,
            cm.irish_language_support
        FROM concepts c
        JOIN learning_outcomes lo ON c.outcome_id = lo.id
        LEFT JOIN concept_metadata cm ON c.id = cm.concept_id
        WHERE lo.unit_id = :unit_id AND lo.year_id = :year_id
        ORDER BY c.difficulty_level
    """)
    result = await db.execute(query, {"unit_id": unit_id, "year_id": year_id})
    return {"concepts": [dict(row) for row in result.mappings()]}


@router.get("/units/{unit_id}/learning-outcomes")
async def get_unit_learning_outcomes(
    unit_id: int, year_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get learning outcomes for a specific unit and school year.
    Includes the outcome description, prerequisites, and complexity level.
    """
    query = text("""
        SELECT 
            lo.id,
            lo.outcome_description,
            lo.prerequisite_knowledge,
            lo.complexity_level,
            su.unit_name,
            s.strand_name
        FROM learning_outcomes lo
        JOIN strand_units su ON lo.unit_id = su.id
        JOIN strands s ON su.strand_id = s.id
        WHERE lo.unit_id = :unit_id 
        AND lo.year_id = :year_id
        ORDER BY lo.complexity_level
    """)
    result = await db.execute(query, {"unit_id": unit_id, "year_id": year_id})
    return {"learning_outcomes": [dict(row) for row in result.mappings()]}
