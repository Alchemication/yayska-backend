from fastapi import APIRouter

from app.api.v1.endpoints import concepts, curriculum, education

api_router = APIRouter()

api_router.include_router(education.router, prefix="/education", tags=["education"])
api_router.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
api_router.include_router(concepts.router, prefix="/concepts", tags=["concepts"])
