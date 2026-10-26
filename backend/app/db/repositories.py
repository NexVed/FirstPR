"""Typed data access over Supabase PostgREST tables.

All functions take the client explicitly so callers (and tests) can swap
the backend without touching service logic.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import DatabaseError, NotFoundError


def _execute(query):
    try:
        response = query.execute()
    except Exception as exc:  # postgrest/storage errors of any shape
        raise DatabaseError("Database operation failed") from exc
    if getattr(response, "error", None):
        raise DatabaseError("Database operation failed")
    return getattr(response, "data", None) or []


def upsert_user_profile(client, profile: dict[str, Any]) -> dict[str, Any]:
    data = _execute(
        client.table("user_profiles").upsert(profile, on_conflict="id")
    )
    return data[0] if data else profile


def get_user_profile(client, user_id: str) -> dict[str, Any] | None:
    data = _execute(
        client.table("user_profiles").select("*").eq("id", user_id).limit(1)
    )
    return data[0] if data else None


def insert_analysis(client, payload: dict[str, Any]) -> dict[str, Any]:
    data = _execute(client.table("repository_analyses").insert(payload))
    if not data:
        raise DatabaseError("Failed to persist analysis")
    return data[0]


def get_analysis(client, user_id: str, analysis_id: str) -> dict[str, Any]:
    data = _execute(
        client.table("repository_analyses")
        .select("*")
        .eq("id", analysis_id)
        .eq("user_id", user_id)
        .limit(1)
    )
    if not data:
        raise NotFoundError("Analysis not found")
    return data[0]


def list_analyses(
    client, user_id: str, *, limit: int = 20
) -> list[dict[str, Any]]:
    return _execute(
        client.table("repository_analyses")
        .select("id,repository_url,owner,name,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )


def get_latest_analysis_for_repo(
    client, user_id: str, repository_url: str
) -> dict[str, Any] | None:
    data = _execute(
        client.table("repository_analyses")
        .select("*")
        .eq("user_id", user_id)
        .eq("repository_url", repository_url)
        .order("created_at", desc=True)
        .limit(1)
    )
    return data[0] if data else None


def insert_plan(client, payload: dict[str, Any]) -> dict[str, Any]:
    data = _execute(client.table("contribution_plans").insert(payload))
    if not data:
        raise DatabaseError("Failed to persist plan")
    return data[0]


def get_plan(client, user_id: str, plan_id: str) -> dict[str, Any]:
    data = _execute(
        client.table("contribution_plans")
        .select("*")
        .eq("id", plan_id)
        .eq("user_id", user_id)
        .limit(1)
    )
    if not data:
        raise NotFoundError("Plan not found")
    return data[0]


def list_plans(client, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    return _execute(
        client.table("contribution_plans")
        .select("id,repository_url,issue_number,issue_title,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )


def insert_triage(client, payload: dict[str, Any]) -> dict[str, Any]:
    data = _execute(client.table("screenshot_triages").insert(payload))
    if not data:
        raise DatabaseError("Failed to persist triage")
    return data[0]


def insert_activity(client, payload: dict[str, Any]) -> dict[str, Any]:
    data = _execute(client.table("activity_history").insert(payload))
    return data[0] if data else payload


def list_activity(
    client, user_id: str, *, limit: int = 30
) -> list[dict[str, Any]]:
    return _execute(
        client.table("activity_history")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )


def count_rows(client, table: str, user_id: str) -> int:
    try:
        response = (
            client.table(table)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        raise DatabaseError("Database operation failed") from exc
    return getattr(response, "count", 0) or 0
