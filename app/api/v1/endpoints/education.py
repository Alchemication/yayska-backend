import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = structlog.get_logger()

router = APIRouter()


@router.get("/education-levels")
async def get_education_levels(db: AsyncSession = Depends(get_db)):
    try:
        query = text("""
            SELECT id, level_name
            FROM education_levels
            ORDER BY id
        """)
        result = await db.execute(query)
        return {"education_levels": [dict(row) for row in result.mappings()]}
    except Exception as e:
        logger.error(
            "Database connection error",
            error=str(e),
        )
        raise HTTPException(
            status_code=503, detail="Database connection error. Please try again later."
        )


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
