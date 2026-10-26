"""Contribution plan pipeline: one fixed AI call per plan."""

from __future__ import annotations

from typing import Any

from app.ai import prompts
from app.ai.provider import AIProvider
from app.ai.schemas import ContributionPlanDraft, RepositoryConventions
from app.core.logging import get_logger
from app.db import repositories as db
from app.services.github_service import GitHubService
from app.services.retrieval_service import filter_tree_paths, rank_candidate_paths
from app.utils.github_urls import parse_repository_url
from app.utils.path_validation import validate_paths

logger = get_logger(__name__)


class PlanService:
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

    async def generate_plan(
        self,
        *,
        user_id: str,
        repository_url: str,
        issue_number: int,
        client=None,
    ) -> dict[str, Any]:
        ref = parse_repository_url(repository_url)

        metadata = await self._github.get_repository(ref)
        issue = await self._github.get_issue(ref, issue_number)
        readme = await self._github.get_readme(ref)
        contributing = await self._github.get_contributing(ref)
        tree_paths = await self._github.get_tree_paths(
            ref, metadata["default_branch"]
        )
        relevant_paths, valid_paths = filter_tree_paths(tree_paths)

        conventions = await self._load_conventions(
            client=client,
            user_id=user_id,
            repository_url=ref.https_url,
            metadata=metadata,
            readme=readme,
            contributing=contributing,
        )

        context_paths = rank_candidate_paths(
            issue,
            relevant_paths,
            limit=self._settings.candidate_paths_per_issue,
        )

        draft = await self._ai.generate_json(
            prompts.build_plan_prompt(
                repo_name=metadata["full_name"],
                issue={
                    "number": issue["number"],
                    "title": issue["title"],
                    "labels": issue["labels"],
                    "body_excerpt": (issue.get("body") or "")[:800],
                },
                conventions=conventions.model_dump(),
                context_paths=context_paths,
            ),
            ContributionPlanDraft,
        )

        files = validate_paths(draft.files_to_touch, valid_paths, limit=10)
        draft = draft.model_copy(update={"files_to_touch": files})

        response = {
            "repository": metadata,
            "issue": {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["url"],
            },
            "plan": draft,
        }

        if client is not None:
            row = db.insert_plan(
                client,
                {
                    "user_id": user_id,
                    "repository_url": ref.https_url,
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "plan": draft.model_dump(),
                },
            )
            response["id"] = row.get("id")
            response["created_at"] = row.get("created_at")

        return response

    async def _load_conventions(
        self,
        *,
        client,
        user_id: str,
        repository_url: str,
        metadata: dict[str, Any],
        readme: str | None,
        contributing: str | None,
    ) -> RepositoryConventions:
        """Reuse the conventions from the user's latest analysis when present."""
        if client is not None:
            latest = db.get_latest_analysis_for_repo(
                client, user_id, repository_url
            )
            stored = (latest or {}).get("conventions")
            if isinstance(stored, dict):
                try:
                    return RepositoryConventions.model_validate(stored)
                except Exception:
                    logger.info("Stored conventions invalid; regenerating")

        return await self._ai.generate_json(
            prompts.build_conventions_prompt(
                repo_name=metadata["full_name"],
                repo_description=metadata.get("description"),
                readme=prompts.truncate_document(readme or ""),
                contributing=prompts.truncate_document(contributing or ""),
            ),
            RepositoryConventions,
        )
