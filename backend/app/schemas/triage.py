"""Screenshot triage schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.ai.schemas import ScreenshotAnalysis, VisibleError


class RelatedIssue(BaseModel):
    number: int
    title: str
    url: str = ""
    score: int


class IssueDraftOut(BaseModel):
    title: str
    body: str


class TriageResponse(BaseModel):
    id: str | None = None
    repository: dict
    analysis: ScreenshotAnalysis
    related_issues: list[RelatedIssue]
    draft: IssueDraftOut
    created_at: datetime | None = None


__all__ = [
    "TriageResponse",
    "RelatedIssue",
    "IssueDraftOut",
    "VisibleError",
]
