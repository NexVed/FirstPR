"""Activity history recording and dashboard aggregation."""

from __future__ import annotations

from typing import Any

from app.db import repositories as db

ACTIVITY_ANALYSIS = "repository_analyzed"
ACTIVITY_PLAN = "plan_created"
ACTIVITY_TRIAGE = "triage_created"


class ActivityService:
    def record(
        self,
        client,
        *,
        user_id: str,
        activity_type: str,
        summary: dict[str, Any],
        entity_id: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "activity_type": activity_type,
            "summary": summary,
        }
        if entity_id:
            payload["entity_id"] = entity_id
        try:
            db.insert_activity(client, payload)
        except Exception:  # activity must never break the main flow
            pass

    def dashboard(self, client, *, user_id: str) -> dict[str, Any]:
        return {
            "total_analyses": db.count_rows(client, "repository_analyses", user_id),
            "total_plans": db.count_rows(client, "contribution_plans", user_id),
            "total_triages": db.count_rows(client, "screenshot_triages", user_id),
            "recent_activity": self.list(client, user_id=user_id, limit=10),
        }

    def list(
        self, client, *, user_id: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        return db.list_activity(client, user_id, limit=limit)
