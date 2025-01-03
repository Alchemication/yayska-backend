import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.database import get_db

logger = structlog.get_logger()

router = APIRouter()


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Simple query to check database connectivity
        result = await db.execute(text("SELECT 1"))
        await result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")
