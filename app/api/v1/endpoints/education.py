from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.get("/education-levels")
async def get_education_levels(db: AsyncSession = Depends(get_db)) -> dict:
    """Get all education levels (Primary, Secondary)."""
    query = text("""
        SELECT id, level_name 
        FROM education_levels 
        ORDER BY id
    """)
    result = await db.execute(query)
    return {"education_levels": [dict(row) for row in result.mappings()]}


@router.get("/education-levels/{level_id}/years")
async def get_school_years(level_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """Get school years for a specific education level."""
    query = text("""
        SELECT id, year_name, year_order
        FROM school_years
        WHERE level_id = :level_id
        ORDER BY year_order
    """)
    result = await db.execute(query, {"level_id": level_id})
    return {"school_years": [dict(row) for row in result.mappings()]}