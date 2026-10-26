"""GitHub REST API integration built on HTTPX."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubRateLimitError,
    RepositoryNotFoundError,
)
from app.core.logging import get_logger, redact_url
from app.utils.github_urls import RepositoryRef

logger = get_logger(__name__)

RAW_ACCEPT = "application/vnd.github.raw+json"
JSON_ACCEPT = "application/vnd.github+json"

CONTRIBUTING_PATHS = (
    "CONTRIBUTING.md",
    ".github/CONTRIBUTING.md",
    "docs/CONTRIBUTING.md",
)

# Hosts from which issue screenshots may be downloaded (SSRF guard).
_IMAGE_HOST_ALLOWLIST = {
    "user-images.githubusercontent.com",
    "private-user-images.githubusercontent.com",
    "github.com",
    "raw.githubusercontent.com",
}

_IMAGE_URL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")

GOOD_FIRST_ISSUE_LABEL = "good first issue"
HELP_WANTED_LABEL = "help wanted"


def _map_status(status: int, url: str, remaining: str | None) -> None:
    if status < 400:
        return
    if status == 404:
        raise RepositoryNotFoundError(
            "Repository or resource not found on GitHub"
        )
    if status in (401, 403):
        if remaining == "0":
            raise GitHubRateLimitError(
                "GitHub rate limit reached; try again later"
            )
        raise GitHubAuthError("GitHub rejected the request (auth or abuse)")
    if status == 422:
        raise GitHubError("GitHub rejected the request payload")
    logger.warning("GitHub error status=%s url=%s", status, redact_url(url))
    raise GitHubError("GitHub request failed")


class GitHubService:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        api_base: str = "https://api.github.com",
        token: str = "",
    ):
        self._http = http
        self._api_base = api_base.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": JSON_ACCEPT, "X-GitHub-Api-Version": "2022-11-28"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self, method: str, path: str, *, accept: str = JSON_ACCEPT
    ) -> httpx.Response:
        url = f"{self._api_base}{path}"
        headers = self._headers()
        headers["Accept"] = accept
        try:
            response = await self._http.request(
                method, url, headers=headers, follow_redirects=True
            )
        except httpx.TimeoutException as exc:
            raise GitHubError("GitHub request timed out") from exc
        except httpx.HTTPError as exc:
            logger.warning("GitHub transport error: %s", type(exc).__name__)
            raise GitHubError("GitHub request failed") from exc

        remaining = response.headers.get("x-ratelimit-remaining")
        _map_status(response.status_code, url, remaining)
        return response

    async def get_repository(self, ref: RepositoryRef) -> dict[str, Any]:
        response = await self._request("GET", f"/repos/{ref.slug}")
        data = response.json()
        if data.get("private"):
            raise GitHubAuthError("Private repositories are not supported")
        return {
            "owner": ref.owner,
            "name": ref.name,
            "full_name": data.get("full_name", ref.slug),
            "description": data.get("description"),
            "default_branch": data.get("default_branch") or "main",
            "stargazers_count": data.get("stargazers_count", 0),
            "language": data.get("language"),
            "html_url": data.get("html_url", ref.https_url),
        }

    async def get_readme(self, ref: RepositoryRef) -> str | None:
        try:
            response = await self._request(
                "GET", f"/repos/{ref.slug}/readme", accept=RAW_ACCEPT
            )
        except RepositoryNotFoundError:
            return None
        return response.text

    async def get_contributing(self, ref: RepositoryRef) -> str | None:
        for path in CONTRIBUTING_PATHS:
            try:
                response = await self._request(
                    "GET",
                    f"/repos/{ref.slug}/contents/{path}",
                    accept=RAW_ACCEPT,
                )
            except RepositoryNotFoundError:
                continue
            return response.text
        return None

    async def get_tree_paths(self, ref: RepositoryRef, branch: str) -> list[str]:
        """Return all blob paths from the recursive git tree."""
        response = await self._request(
            "GET", f"/repos/{ref.slug}/git/trees/{branch}?recursive=1"
        )
        data = response.json()
        if data.get("truncated"):
            logger.warning("GitHub tree response truncated for %s", ref.slug)
        paths = [
            entry["path"]
            for entry in data.get("tree", [])
            if entry.get("type") == "blob" and entry.get("path")
        ]
        return paths

    async def list_issues_by_label(
        self, ref: RepositoryRef, label: str, count: int
    ) -> list[dict[str, Any]]:
        per_page = max(min(count * 2, 100), 1)
        response = await self._request(
            "GET",
            f"/repos/{ref.slug}/issues"
            f"?state=open&labels={quote(label)}&per_page={per_page}",
        )
        issues = [self._clean_issue(item) for item in response.json()]
        return [issue for issue in issues if issue is not None][:count]

    async def list_open_issues(
        self, ref: RepositoryRef, count: int
    ) -> list[dict[str, Any]]:
        per_page = max(min(count * 2, 100), 1)
        response = await self._request(
            "GET",
            f"/repos/{ref.slug}/issues?state=open&per_page={per_page}",
        )
        issues = [self._clean_issue(item) for item in response.json()]
        return [issue for issue in issues if issue is not None][:count]

    @staticmethod
    def _clean_issue(item: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize an issue payload; exclude pull requests."""
        if "pull_request" in item:
            return None
        body = item.get("body") or ""
        labels = [
            label.get("name", "")
            for label in item.get("labels", [])
            if isinstance(label, dict)
        ]
        return {
            "number": item.get("number", 0),
            "title": item.get("title", ""),
            "body": body,
            "labels": [label for label in labels if label],
            "url": item.get("html_url", ""),
            "author": (item.get("user") or {}).get("login"),
            "created_at": item.get("created_at"),
        }

    async def get_issue(self, ref: RepositoryRef, number: int) -> dict[str, Any]:
        response = await self._request(
            "GET", f"/repos/{ref.slug}/issues/{number}"
        )
        cleaned = self._clean_issue(response.json())
        if cleaned is None:
            raise GitHubError("Requested issue is a pull request")
        return cleaned

    async def download_image(self, url: str, max_bytes: int) -> bytes | None:
        """Download a screenshot referenced in an issue body.

        Only allow-listed GitHub asset hosts are followed.
        """
        if not url.lower().startswith("https://"):
            return None
        try:
            parts = httpx.URL(url)
        except httpx.InvalidURL:
            return None
        if parts.host not in _IMAGE_HOST_ALLOWLIST:
            return None
        try:
            response = await self._http.get(url, timeout=15.0)
        except httpx.HTTPError:
            logger.warning("Screenshot download failed: %s", type(url).__name__)
            return None
        if response.status_code != 200:
            return None
        data = response.content
        if len(data) > max_bytes:
            return None
        return data

    @staticmethod
    def extract_screenshot_urls(body: str, limit: int = 2) -> list[str]:
        """Find image asset URLs inside an issue body."""
        urls: list[str] = []
        for token in (body or "").replace(")", " ").replace('"', " ").split():
            if not token.startswith("http"):
                continue
            lower = token.lower().split("?")[0]
            if lower.endswith(_IMAGE_URL_SUFFIXES):
                urls.append(token)
            if len(urls) >= limit:
                break
        return urls
