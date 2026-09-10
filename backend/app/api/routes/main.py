from fastapi import APIRouter

from app.api.routes import users

api_router = APIRouter(prefix="/api")
api_router.include_router(users.router)
