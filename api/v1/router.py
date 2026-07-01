from fastapi import APIRouter

from .routes import media

api_router = APIRouter()
api_router.include_router(media.router, prefix="/media", tags=["media"])