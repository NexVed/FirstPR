"""Contribution plan schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.schemas import ContributionPlanDraft


class PlanCreateRequest(BaseModel):
    repository_url: str
    issue_number: int = Field(ge=1)


class PlanResponse(BaseModel):
    id: str | None = None
    repository: dict
    issue: dict
    plan: ContributionPlanDraft
    created_at: datetime | None = None


class PlanListItem(BaseModel):
    id: str
    repository_url: str
    issue_number: int
    issue_title: str
    created_at: datetime | None = None


class PlanListResponse(BaseModel):
    plans: list[PlanListItem]
