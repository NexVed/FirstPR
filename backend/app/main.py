"""FirstPR FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai import gemma_provider, openai_compatible_provider
from app.ai.provider import AIProvider
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.db.supabase import create_supabase_client
from app.services.activity_service import ActivityService
from app.services.github_service import GitHubService
from app.services.plan_service import PlanService
from app.services.repository_service import RepositoryAnalysisService
from app.services.triage_service import TriageService

logger = get_logger(__name__)


def build_ai_provider(settings: Settings, http: httpx.AsyncClient) -> AIProvider | None:
    """Gemma first, then the OpenAI-compatible backend. Never a closed fallback."""
    if settings.gemini_api_key.strip():
        return gemma_provider.GemmaProvider(
            http,
            api_base=settings.gemma_api_base,
            api_key=settings.gemini_api_key,
            model=settings.gemma_model,
            timeout=settings.request_timeout_seconds,
        )
    if (
        settings.llm_base_url.strip()
        and settings.llm_model.strip()
        and settings.llm_api_key.strip()
    ):
        return openai_compatible_provider.OpenAICompatibleProvider(
            http,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout=settings.request_timeout_seconds,
        )
    return None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        http = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
        app.state.settings = settings
        app.state.http = http
        app.state.db = create_supabase_client(settings)
        app.state.ai = build_ai_provider(settings, http)
        app.state.github = GitHubService(
            http,
            api_base=settings.github_api_base,
            token=settings.github_token,
        )
        app.state.repository_service = RepositoryAnalysisService(
            settings=settings, github=app.state.github, ai=app.state.ai
        )
        app.state.plan_service = PlanService(
            settings=settings, github=app.state.github, ai=app.state.ai
        )
        app.state.triage_service = TriageService(
            settings=settings, github=app.state.github, ai=app.state.ai
        )
        app.state.activity_service = ActivityService()
        logger.info(
            "%s started (env=%s ai=%s)",
            settings.app_name,
            settings.app_env,
            settings.ai_provider_status(),
        )
        try:
            yield
        finally:
            await http.aclose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                }
            },
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", include_in_schema=False)
    async def root_health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
