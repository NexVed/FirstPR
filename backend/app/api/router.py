"""Route modules for the FirstPR API."""

from fastapi import APIRouter

from app.api.routes import (
    activity,
    dashboard,
    health,
    plans,
    repositories,
    triage,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(repositories.router)
api_router.include_router(plans.router)
api_router.include_router(triage.router)
api_router.include_router(activity.router)
