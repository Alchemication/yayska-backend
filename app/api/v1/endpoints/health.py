import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.database import get_db
from app.schemas.health_schema import HealthCheck

logger = structlog.get_logger()

router = APIRouter()


@router.get("", response_model=HealthCheck)
async def health_check(session: AsyncSession = Depends(get_db)) -> HealthCheck:
    """
    Health check endpoint that also verifies database connectivity.
    """
    try:
        # Test database connection
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = "unhealthy"

    return HealthCheck(
        status="healthy",
        database_status=db_status,
    )
