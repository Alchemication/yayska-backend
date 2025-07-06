from fastapi import APIRouter, Depends

# from fastapi_cache.decorator import cache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.deps import CurrentUser

router = APIRouter()


@router.get("/subjects/{year_id}/learning-paths")
# @cache(expire=300)  # Cache for 5 minutes (300 seconds)
async def get_subject_learning_paths(
    year_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
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
    all_concept_ids = set()

    for row in result.mappings():
        subject_id = row["subject_id"]
        concept_id = row["concept_id"]
        all_concept_ids.add(concept_id)

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
                "id": concept_id,
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

    # Fetch user interactions for the concept IDs
    user_interactions_data = {}

    if all_concept_ids:
        concept_ids_list = list(all_concept_ids)

        # Fetch user interactions
        interactions_query = text("""
            SELECT 
                (interaction_context->'concept_id')::text::integer as concept_id,
                interaction_type
            FROM user_interactions
            WHERE user_id = :user_id
            AND interaction_context->>'concept_id' IS NOT NULL
            AND (interaction_context->'concept_id')::text::integer = ANY(:concept_ids)
            AND interaction_type IN ('CONCEPT_STUDIED', 'AI_CHAT_ENGAGED')
        """)

        interactions_result = await db.execute(
            interactions_query,
            {"user_id": current_user["id"], "concept_ids": concept_ids_list},
        )

        # Process user interactions
        interactions = interactions_result.mappings().all()
        for interaction in interactions:
            concept_id = interaction["concept_id"]
            interaction_type = interaction["interaction_type"]

            if concept_id not in user_interactions_data:
                user_interactions_data[concept_id] = {
                    "previously_studied": False,
                    "previously_discussed": False,
                }

            if interaction_type == "CONCEPT_STUDIED":
                user_interactions_data[concept_id]["previously_studied"] = True
            elif interaction_type == "AI_CHAT_ENGAGED":
                user_interactions_data[concept_id]["previously_discussed"] = True

    # Add interaction flags to each concept
    for subject in subjects.values():
        for concept in subject["concepts"]:
            concept_id = concept["id"]
            interaction_data = user_interactions_data.get(
                concept_id,
                {"previously_studied": False, "previously_discussed": False},
            )
            concept["previously_studied"] = interaction_data["previously_studied"]
            concept["previously_discussed"] = interaction_data["previously_discussed"]

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
