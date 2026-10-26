"""Repository analysis pipeline: GitHub data + two fixed AI calls."""

from __future__ import annotations

from typing import Any

from app.ai import prompts
from app.ai.provider import AIProvider, ImageInput
from app.ai.schemas import (
    IssueRecommendation,
    IssueRecommendationBatch,
    RepositoryConventions,
)
from app.core.exceptions import AIError
from app.core.logging import get_logger
from app.db import repositories as db
from app.db.supabase import has_service_role_key
from app.services.github_service import (
    GOOD_FIRST_ISSUE_LABEL,
    HELP_WANTED_LABEL,
    GitHubService,
)
from app.services.retrieval_service import filter_tree_paths, rank_candidate_paths
from app.utils.github_urls import parse_repository_url
from app.utils.images import validate_image
from app.utils.path_validation import validate_paths

logger = get_logger(__name__)

MAX_SCREENSHOTS = 2


class RepositoryAnalysisService:
    def __init__(
        self,
        *,
        settings,
        github: GitHubService,
        ai: AIProvider | None,
    ):
        self._settings = settings
        self._github = github
        self._ai = ai

    async def analyze(
        self,
        *,
        user_id: str,
        repository_url: str,
        issue_count: int,
        top: int,
        client=None,
    ) -> dict[str, Any]:
        ref = parse_repository_url(repository_url)
        logger.info("Repository analysis started: %s", ref.slug)
        metadata = await self._github.get_repository(ref)
        logger.info("Repository metadata loaded: %s", ref.slug)
        readme = await self._github.get_readme(ref)
        contributing = await self._github.get_contributing(ref)
        tree_paths = await self._github.get_tree_paths(
            ref, metadata["default_branch"]
        )
        logger.info("Repository tree loaded: %s (%d paths)", ref.slug, len(tree_paths))
        relevant_paths, valid_paths = filter_tree_paths(tree_paths)

        issues = await self._github.list_issues_by_label(
            ref, GOOD_FIRST_ISSUE_LABEL, issue_count
        )
        if len(issues) < issue_count:
            fallback = await self._github.list_issues_by_label(
                ref,
                HELP_WANTED_LABEL,
                issue_count - len(issues),
            )
            known = {issue["number"] for issue in issues}
            issues.extend(
                issue for issue in fallback if issue["number"] not in known
            )
        if not issues:
            issues = await self._github.list_open_issues(ref, issue_count)
        logger.info("Repository issues loaded: %s (%d issues)", ref.slug, len(issues))

        if self._ai is None:
            conventions = RepositoryConventions(
                analysis_warning="AI suggestions were unavailable during this scan. Analyze the repository again to retry."
            )
        else:
            try:
                conventions = await self._ai.generate_json(
                    prompts.build_conventions_prompt(
                        repo_name=metadata["full_name"],
                        repo_description=metadata.get("description"),
                        readme=prompts.truncate_document(readme or ""),
                        contributing=prompts.truncate_document(contributing or ""),
                    ),
                    RepositoryConventions,
                )
            except AIError as exc:
                logger.warning("Repository conventions unavailable for %s: %s", ref.slug, exc)
                conventions = RepositoryConventions(
                    analysis_warning="Repository scanned, but AI suggestions are temporarily unavailable. Try analyzing it again later."
                )
        logger.info("Repository conventions generated: %s", ref.slug)

        screenshots = await self._collect_screenshots(issues)
        candidate_paths = {
            issue["number"]: rank_candidate_paths(
                issue,
                relevant_paths,
                limit=self._settings.candidate_paths_per_issue,
            )
            for issue in issues
        }

        recommendations = []
        if issues and not conventions.analysis_warning:
            try:
                batch = await self._ai.generate_json(
                    prompts.build_issue_scoring_prompt(
                        repo_name=metadata["full_name"],
                        conventions=conventions.model_dump(),
                        issues=[
                            {
                                "number": issue["number"],
                                "title": issue["title"],
                                "labels": issue["labels"],
                                "body_excerpt": (issue.get("body") or "")[:400],
                            }
                            for issue in issues
                        ],
                        candidate_paths=candidate_paths,
                        screenshot_context={
                            number: (
                                f"{len(images)} screenshot(s) from this issue are "
                                "attached to this request, in issue order."
                            )
                            for number, images in screenshots.items()
                        },
                    ),
                    IssueRecommendationBatch,
                    images=[image for images in screenshots.values() for image in images],
                )
                logger.info("Repository issues scored: %s", ref.slug)
                recommendations = self._build_recommendations(
                    issues=issues,
                    batch=batch,
                    valid_paths=valid_paths,
                    screenshots=screenshots,
                )
            except AIError as exc:
                logger.warning("Repository scoring unavailable for %s: %s", ref.slug, exc)
                conventions.analysis_warning = "Repository scanned, but AI suggestions are temporarily unavailable. Try analyzing it again later."
        recommendations.sort(key=lambda item: item["difficulty"])
        recommendations = recommendations[:top]

        response = {
            "repository": metadata,
            "conventions": conventions,
            "recommendations": recommendations,
        }

        if client is not None and has_service_role_key(self._settings.supabase_key):
            logger.info("Saving repository analysis: %s", ref.slug)
            try:
                row = db.insert_analysis(
                    client,
                    {
                        "user_id": user_id,
                        "repository_url": ref.https_url,
                        "owner": ref.owner,
                        "name": ref.name,
                        "conventions": conventions.model_dump(),
                        "recommendations": recommendations,
                    },
                )
                response["id"] = row.get("id")
                response["created_at"] = row.get("created_at")
            except Exception as exc:
                logger.warning("Could not save repository analysis for %s: %s", ref.slug, type(exc).__name__)
                conventions.analysis_warning = "Repository scanned but could not be saved. Check the backend Supabase service-role key."
        else:
            warning = "Repository scanned but not saved. Set SUPABASE_KEY in backend/.env to the Supabase service-role key."
            if conventions.analysis_warning:
                conventions.analysis_warning += " " + warning
            else:
                conventions.analysis_warning = warning

        logger.info("Repository analysis completed: %s", ref.slug)

        return response

    async def _collect_screenshots(
        self, issues: list[dict[str, Any]]
    ) -> dict[int, list[ImageInput]]:
        screenshots: dict[int, list[ImageInput]] = {}
        budget = MAX_SCREENSHOTS
        max_bytes = self._settings.max_upload_bytes
        for issue in issues:
            if budget <= 0:
                break
            for url in GitHubService.extract_screenshot_urls(issue.get("body") or ""):
                if budget <= 0:
                    break
                data = await self._github.download_image(url, max_bytes)
                if data is None:
                    continue
                try:
                    mime = validate_image(data, max_bytes=max_bytes)
                except Exception:
                    logger.info("Skipping invalid issue screenshot")
                    continue
                screenshots.setdefault(issue["number"], []).append(
                    ImageInput(mime_type=mime, data=data)
                )
                budget -= 1
        return screenshots

    def _build_recommendations(
        self,
        *,
        issues: list[dict[str, Any]],
        batch: IssueRecommendationBatch,
        valid_paths: set[str],
        screenshots: dict[int, list[ImageInput]],
    ) -> list[IssueRecommendation]:
        by_number = {issue["number"]: issue for issue in issues}
        scored = {
            recommendation.issue_number: recommendation
            for recommendation in batch.recommendations
            if recommendation.issue_number in by_number
        }

        recommendations: list[dict[str, Any]] = []
        for number, issue in by_number.items():
            scored_item = scored.get(number)
            files = validate_paths(
                list(scored_item.files) if scored_item else [],
                valid_paths,
                limit=4,
            )
            recommendation = IssueRecommendation(
                issue_number=number,
                title=issue["title"],
                difficulty=scored_item.difficulty if scored_item else 3,
                files=files,
                approach=(scored_item.approach if scored_item else ""),
                first_step=(scored_item.first_step if scored_item else ""),
                screenshots_analyzed=number in screenshots,
            )
            payload = recommendation.model_dump()
            payload["url"] = issue.get("url", "")
            payload["labels"] = issue.get("labels", [])
            recommendations.append(payload)
        return recommendations
