from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/subjects")
async def get_subjects(year_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Get all subjects with their curriculum areas."""
    query = text("""
        SELECT s.id, s.subject_name, ca.area_name
        FROM subjects s
        JOIN curriculum_areas ca ON s.area_id = ca.id
        ORDER BY ca.area_name, s.subject_name
    """)
    result = await db.execute(query)
    return {"subjects": [dict(row) for row in result.mappings()]}


@router.get("/subjects/{subject_id}/strands")
async def get_strands(subject_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Get all strands for a specific subject."""
    query = text("""
        SELECT id, strand_name
        FROM strands
        WHERE subject_id = :subject_id
        ORDER BY strand_name
    """)
    result = await db.execute(query, {"subject_id": subject_id})
    return {"strands": [dict(row) for row in result.mappings()]}


@router.get("/strands/{strand_id}/units")
async def get_strand_units(strand_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Get all units for a specific strand."""
    query = text("""
        SELECT id, unit_name
        FROM strand_units
        WHERE strand_id = :strand_id
        ORDER BY unit_name
    """)
    result = await db.execute(query, {"strand_id": strand_id})
    return {"strand_units": [dict(row) for row in result.mappings()]}
