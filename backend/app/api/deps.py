"""FastAPI dependencies shared by all routes."""

from __future__ import annotations

import httpx
from fastapi import Depends, Request
from fastapi.security.utils import get_authorization_scheme_param
from supabase import Client

from app.ai.provider import AIProvider
from app.core.config import Settings
from app.core.exceptions import (
    AIProviderNotConfiguredError,
    AuthenticationError,
)
from app.core.security import AuthUser, verify_supabase_token


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_db_client(request: Request) -> Client:
    return request.app.state.db


def get_ai_provider(request: Request) -> AIProvider:
    provider = request.app.state.ai
    if provider is None:
        raise AIProviderNotConfiguredError(
            "No AI provider is configured. Set GEMINI_API_KEY (Gemma) or "
            "LLM_BASE_URL, LLM_MODEL and LLM_API_KEY (OpenAI-compatible)."
        )
    return provider


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    authorization = request.headers.get("Authorization", "")
    scheme, token = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError(
            "Missing bearer token; sign in through Supabase auth"
        )
    return verify_supabase_token(
        token,
        jwt_secret=settings.supabase_jwt_secret,
        supabase_url=settings.supabase_url,
    )


def get_repository_service(request: Request):
    return request.app.state.repository_service


def get_github_service(request: Request):
    return request.app.state.github


def get_plan_service(request: Request):
    return request.app.state.plan_service


def get_triage_service(request: Request):
    return request.app.state.triage_service


def get_activity_service(request: Request):
    return request.app.state.activity_service
