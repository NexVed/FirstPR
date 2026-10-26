"""Pydantic schemas validated against every model response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RepositoryConventions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    setup_commands: list[str] = Field(default_factory=list)
    test_command: str | None = None
    lint_command: str | None = None
    pr_rules: list[str] = Field(default_factory=list)
    analysis_warning: str | None = None


class IssueRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(ge=1)
    title: str
    difficulty: int = Field(ge=1, le=5)
    files: list[str] = Field(default_factory=list, max_length=4)
    approach: str = ""
    first_step: str = ""
    screenshots_analyzed: bool = False

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        return value


class IssueRecommendationBatch(BaseModel):
    """Wrapper used when scoring multiple issues in a single call."""

    model_config = ConfigDict(extra="forbid")

    recommendations: list[IssueRecommendation] = Field(min_length=1)


class VisibleError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_type: str = ""
    message: str
    location_hint: str | None = None


class ScreenshotAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    visible_errors: list[VisibleError] = Field(default_factory=list)
    candidate_files: list[str] = Field(default_factory=list, max_length=20)
    search_terms: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("summary")
    @classmethod
    def summary_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("summary must not be empty")
        return value


class IssueDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    body: str

    @field_validator("title", "body")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("draft fields must not be empty")
        return value


class ContributionPlanDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str
    setup_steps: list[str] = Field(default_factory=list)
    implementation_steps: list[str] = Field(min_length=1)
    files_to_touch: list[str] = Field(default_factory=list, max_length=10)
    testing_strategy: str = ""
    pr_checklist: list[str] = Field(default_factory=list)
    estimated_difficulty: int = Field(ge=1, le=5)
