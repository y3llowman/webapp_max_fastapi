from fastapi import APIRouter

from app.api.routes import company, settings, tasks, users

api_router = APIRouter(prefix="/api")
api_router.include_router(users.router)
api_router.include_router(company.router)
api_router.include_router(tasks.router)
api_router.include_router(settings.router)
