from fastapi import APIRouter, Depends

# from fastapi_cache.decorator import cache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/subjects/{year_id}/learning_paths")
# @cache(expire=300)  # Cache for 5 minutes (300 seconds)
async def get_subject_learning_paths(
    year_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    query = text("""
        SELECT 
            s.id as subject_id,
            s.subject_name,
            c.id as concept_id,
            c.concept_name,
            c.concept_description,
            c.learning_objectives,
            c.display_order,
            cm.difficulty_stats->>'level' as complexity_level
        FROM concepts c
        JOIN subjects s ON s.id = c.subject_id
        LEFT JOIN concept_metadata cm ON cm.concept_id = c.id
        WHERE c.year_id = :year_id
        ORDER BY s.id, c.id 
    """)

    result = await db.execute(query, {"year_id": year_id})

    subjects = {}
    for row in result.mappings():
        subject_id = row["subject_id"]
        if subject_id not in subjects:
            subjects[subject_id] = {
                "id": subject_id,
                "name": row["subject_name"],
                "concepts": [],
            }

        complexity_level = (
            int(row["complexity_level"]) if row["complexity_level"] else 1
        )

        subjects[subject_id]["concepts"].append(
            {
                "id": row["concept_id"],
                "name": row["concept_name"],
                "description": row["concept_description"],
                "complexity": {
                    "level": complexity_level,
                    "description": get_complexity_description(complexity_level),
                },
                "learning_objectives": row["learning_objectives"]
                if row["learning_objectives"]
                else [],
                "display_order": row["display_order"],
            }
        )

    response = []
    for subject in subjects.values():
        response.append(subject)

    return {"subjects": response}


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
