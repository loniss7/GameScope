from fastapi import APIRouter

from app.api.routes.games import router as games_router

api_router = APIRouter()
api_router.include_router(games_router)
