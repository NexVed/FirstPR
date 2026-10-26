"""Dashboard and activity schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ActivityItem(BaseModel):
    id: str | None = None
    activity_type: str
    summary: dict[str, Any] = {}
    entity_id: str | None = None
    created_at: datetime | None = None


class ActivityListResponse(BaseModel):
    activity: list[ActivityItem]


class DashboardResponse(BaseModel):
    total_analyses: int
    total_plans: int
    total_triages: int
    recent_activity: list[ActivityItem]
