from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/{concept_id}/metadata")
async def get_concept_metadata(
    concept_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get detailed metadata for a specific concept.

    Args:
        concept_id: The ID of the concept
        db: Database session dependency

    Returns:
        Dictionary containing all metadata fields for the concept

    Raises:
        HTTPException: If concept is not found
    """
    query = text("""
        SELECT 
            c.id as concept_id,
            c.concept_name,
            c.concept_description,
            cm.why_important,
            cm.difficulty_stats,
            cm.parent_guide,
            cm.real_world,
            cm.learning_path,
            cm.time_guide,
            cm.assessment_approaches,
            cm.irish_language_support
        FROM concepts c
        LEFT JOIN concept_metadata cm ON c.id = cm.concept_id
        WHERE c.id = :concept_id
    """)

    result = await db.execute(query, {"concept_id": concept_id})
    metadata = result.mappings().first()

    if not metadata:
        raise HTTPException(
            status_code=404, detail=f"Concept with id {concept_id} not found"
        )

    return dict(metadata)
