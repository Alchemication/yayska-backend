from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    chats,
    children,
    concepts,
    curriculum,
    education,
    events,
    health,
    user_interactions,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["Curriculum"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["Concepts"])
api_router.include_router(children.router, prefix="/children", tags=["Children"])
api_router.include_router(education.router, prefix="/education", tags=["Education"])
api_router.include_router(chats.router, prefix="/chats", tags=["Chats"])
api_router.include_router(
    user_interactions.router, prefix="/user-interactions", tags=["User Interactions"]
)
