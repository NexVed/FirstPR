"""Supabase client factory."""

from __future__ import annotations

import base64
import json

from supabase import create_client, Client, ClientOptions

from app.core.config import Settings
from app.core.exceptions import ConfigurationError


def has_service_role_key(key: str) -> bool:
    if key.startswith("sb_secret_"):
        return True
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims.get("role") == "service_role"
    except (IndexError, ValueError, TypeError):
        return False


def create_supabase_client(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise ConfigurationError(
            "Supabase is not configured; set SUPABASE_URL and SUPABASE_KEY"
        )
    return create_client(
        settings.supabase_url,
        settings.supabase_key,
        options=ClientOptions(postgrest_client_timeout=20),
    )
