"""Repository analysis request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.ai.schemas import RepositoryConventions
from app.schemas.common import ErrorResponse  # noqa: F401 (re-export)


class AnalyzeRequest(BaseModel):
    repository_url: str
    issues: int = Field(default=6, ge=1, le=20)
    top: int = Field(default=3, ge=1, le=10)


class RepositorySummary(BaseModel):
    owner: str
    name: str
    full_name: str
    description: str | None = None
    default_branch: str
    stargazers_count: int = 0
    language: str | None = None
    html_url: str


class RecommendationOut(BaseModel):
    issue_number: int
    title: str
    url: str = ""
    labels: list[str] = Field(default_factory=list)
    difficulty: int
    files: list[str]
    approach: str
    first_step: str
    screenshots_analyzed: bool


class AnalysisResponse(BaseModel):
    id: str | None = None
    repository: RepositorySummary
    conventions: RepositoryConventions
    recommendations: list[RecommendationOut]
    created_at: datetime | None = None


class AnalysisListItem(BaseModel):
    id: str
    repository_url: str
    owner: str
    name: str
    created_at: datetime | None = None


class AnalysisListResponse(BaseModel):
    analyses: list[AnalysisListItem]


class AnalysisDetailResponse(AnalysisResponse):
    raw: dict[str, Any] | None = None
