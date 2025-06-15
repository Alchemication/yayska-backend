from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    children,
    concepts,
    curriculum,
    education,
    events,
    health,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(education.router, prefix="/education", tags=["education"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
api_router.include_router(children.router, prefix="/children", tags=["children"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
