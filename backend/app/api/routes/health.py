"""Health check endpoint (public)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings

router = APIRouter()


@router.get("/health", tags=["health"])
async def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "ai_provider": settings.ai_provider_status(),
        "database": "configured",
    }
