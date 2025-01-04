from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/subjects/{year_id}/learning_paths")
@cache(expire=300)  # Cache for 5 minutes (300 seconds)
async def get_subject_learning_paths(
    year_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    query = text("""
        SELECT 
            s.id as subject_id,
            s.subject_name,
            su.id as unit_id,
            su.unit_name,
            lo.id as outcome_id,
            lo.outcome_description,
            lo.complexity_level,
            c.id as concept_id,
            c.concept_name,
            c.concept_description
        FROM learning_outcomes lo
        JOIN school_years sy ON sy.id = lo.year_id 
        JOIN strand_units su ON su.id = lo.unit_id
        JOIN strands str ON str.id = su.strand_id
        JOIN subjects s ON s.id = str.subject_id
        JOIN concepts c ON c.outcome_id = lo.id
        WHERE sy.id = :year_id
        ORDER BY s.subject_name, lo.complexity_level, su.unit_name
    """)

    result = await db.execute(query, {"year_id": year_id})

    learning_paths = {}
    for row in result.mappings():
        subject_id = row["subject_id"]
        if subject_id not in learning_paths:
            learning_paths[subject_id] = {
                "id": subject_id,
                "subject_name": row["subject_name"],
                "learning_goals": {},
            }

        unit_id = row["unit_id"]
        if unit_id not in learning_paths[subject_id]["learning_goals"]:
            learning_paths[subject_id]["learning_goals"][unit_id] = {
                "id": unit_id,
                "topic": row["unit_name"],
                "what_child_will_learn": row["outcome_description"],
                "complexity_level": row["complexity_level"],
                "complexity_description": get_complexity_description(
                    row["complexity_level"]
                ),
                "key_concepts": [],
            }

        learning_paths[subject_id]["learning_goals"][unit_id]["key_concepts"].append(
            {
                "id": row["concept_id"],
                "name": row["concept_name"],
                "description": row["concept_description"],
            }
        )

    return {"subjects": list(learning_paths.values())}


def get_complexity_description(level: int) -> str:
    """Return parent-friendly description of complexity levels"""
    descriptions = {
        1: "Basic foundation - Essential starting point",
        2: "Building blocks - Important but straightforward",
        3: "Key skills - Requires good understanding",
        4: "Advanced concepts - May need extra attention",
        5: "Complex ideas - Might be challenging, take it step by step",
    }
    return descriptions.get(level, "Complexity level unknown")
