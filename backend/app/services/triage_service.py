"""Screenshot triage pipeline: exactly two fixed AI calls."""

from __future__ import annotations

import re
from typing import Any

from app.ai import prompts
from app.ai.provider import AIProvider, ImageInput
from app.ai.schemas import IssueDraft, ScreenshotAnalysis
from app.core.logging import get_logger
from app.db import repositories as db
from app.services.github_service import (
    GOOD_FIRST_ISSUE_LABEL,
    HELP_WANTED_LABEL,
    GitHubService,
)
from app.services.retrieval_service import filter_tree_paths
from app.utils.github_urls import parse_repository_url
from app.utils.images import validate_image
from app.utils.path_validation import validate_paths

logger = get_logger(__name__)

TOKEN_PATTERN = re.compile(r"[a-z0-9]{4,}")
MAX_RELATED_ISSUES = 5
RELATED_ISSUE_THRESHOLD = 3


def match_related_issues(
    analysis: ScreenshotAnalysis,
    issues: list[dict[str, Any]],
    *,
    limit: int = MAX_RELATED_ISSUES,
) -> list[dict[str, Any]]:
    """Deterministically score existing issues against the triage analysis."""
    terms: set[str] = {term.lower().strip() for term in analysis.search_terms}
    for error in analysis.visible_errors:
        terms.update(TOKEN_PATTERN.findall(error.message.lower()))
    terms = {term for term in terms if len(term) >= 4}

    scored: list[tuple[int, dict[str, Any]]] = []
    for issue in issues:
        title = (issue.get("title") or "").lower()
        labels = " ".join(issue.get("labels", []) or []).lower()
        body = (issue.get("body") or "")[:600].lower()
        score = 0
        for term in terms:
            if term in title:
                score += 3
            elif term in labels:
                score += 2
            elif term in body:
                score += 1
        if score >= RELATED_ISSUE_THRESHOLD:
            scored.append((score, issue))

    scored.sort(key=lambda item: (-item[0], item[1].get("number", 0)))
    return [
        {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue.get("url", ""),
            "score": score,
        }
        for score, issue in scored[:limit]
    ]


class TriageService:
    def __init__(
        self,
        *,
        settings,
        github: GitHubService,
        ai: AIProvider,
    ):
        self._settings = settings
        self._github = github
        self._ai = ai

    async def triage(
        self,
        *,
        user_id: str,
        repository_url: str,
        image: ImageInput,
        note: str | None,
        client=None,
    ) -> dict[str, Any]:
        ref = parse_repository_url(repository_url)

        metadata = await self._github.get_repository(ref)
        tree_paths = await self._github.get_tree_paths(
            ref, metadata["default_branch"]
        )
        _, valid_paths = filter_tree_paths(tree_paths)

        issues = await self._gather_issues(ref)

        analysis = await self._ai.generate_json(
            prompts.build_triage_prompt(note=note),
            ScreenshotAnalysis,
            images=[image],
        )

        candidate_files = validate_paths(
            analysis.candidate_files,
            valid_paths,
            limit=10,
        )
        analysis = analysis.model_copy(update={"candidate_files": candidate_files})

        related = match_related_issues(analysis, issues)

        draft = await self._ai.generate_json(
            prompts.build_issue_draft_prompt(analysis=analysis, related_issues=related),
            IssueDraft,
        )

        response = {
            "repository": metadata,
            "analysis": analysis,
            "related_issues": related,
            "draft": draft,
        }

        if client is not None:
            row = db.insert_triage(
                client,
                {
                    "user_id": user_id,
                    "repository_url": ref.https_url,
                    "note": note,
                    "analysis": analysis.model_dump(),
                    "related_issues": related,
                    "draft": draft.model_dump(),
                },
            )
            response["id"] = row.get("id")
            response["created_at"] = row.get("created_at")

        return response

    async def _gather_issues(self, ref) -> list[dict[str, Any]]:
        known: set[int] = set()
        issues: list[dict[str, Any]] = []
        for label in (GOOD_FIRST_ISSUE_LABEL, HELP_WANTED_LABEL):
            fetched = await self._github.list_issues_by_label(ref, label, 10)
            for issue in fetched:
                if issue["number"] not in known:
                    known.add(issue["number"])
                    issues.append(issue)
        general = await self._github.list_open_issues(ref, 30)
        for issue in general:
            if issue["number"] not in known:
                known.add(issue["number"])
                issues.append(issue)
        return issues


def image_from_upload(data: bytes, *, max_bytes: int) -> ImageInput:
    mime = validate_image(data, max_bytes=max_bytes)
    return ImageInput(mime_type=mime, data=data)


def clean_note(note: str | None) -> str | None:
    if note is None:
        return None
    note = note.strip()
    return note[:500] or None
