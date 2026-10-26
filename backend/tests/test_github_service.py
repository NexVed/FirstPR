from __future__ import annotations

import httpx
import pytest
import respx

from app.core.exceptions import (
    GitHubRateLimitError,
    RepositoryNotFoundError,
)
from app.services.github_service import GitHubService
from app.utils.github_urls import parse_repository_url


def make_service() -> GitHubService:
    return GitHubService(
        httpx.AsyncClient(), api_base="https://api.github.test", token="t"
    )


def repo_payload() -> dict:
    return {
        "full_name": "octocat/hello-world",
        "description": "demo",
        "default_branch": "main",
        "stargazers_count": 5,
        "language": "Python",
        "html_url": "https://github.com/octocat/hello-world",
        "private": False,
    }


async def test_get_repository_returns_metadata():
    service = make_service()
    with respx.mock:
        respx.get("https://api.github.test/repos/octocat/hello-world").mock(
            return_value=httpx.Response(200, json=repo_payload())
        )
        metadata = await service.get_repository(
            parse_repository_url("https://github.com/octocat/hello-world")
        )
    assert metadata["full_name"] == "octocat/hello-world"
    assert metadata["default_branch"] == "main"


async def test_missing_repository_raises_404():
    service = make_service()
    with respx.mock:
        respx.get("https://api.github.test/repos/octocat/hello-world").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        with pytest.raises(RepositoryNotFoundError):
            await service.get_repository(
                parse_repository_url("https://github.com/octocat/hello-world")
            )


async def test_rate_limit_raises_specialized_error():
    service = make_service()
    with respx.mock:
        respx.get("https://api.github.test/repos/octocat/hello-world").mock(
            return_value=httpx.Response(
                403,
                json={"message": "API rate limit exceeded"},
                headers={"x-ratelimit-remaining": "0"},
            )
        )
        with pytest.raises(GitHubRateLimitError):
            await service.get_repository(
                parse_repository_url("https://github.com/octocat/hello-world")
            )


async def test_list_issues_excludes_pull_requests():
    service = make_service()
    issues_payload = [
        {"number": 1, "title": "Bug A", "labels": [], "html_url": "u1", "body": ""},
        {
            "number": 2,
            "title": "PR",
            "labels": [],
            "html_url": "u2",
            "body": "",
            "pull_request": {"url": "x"},
        },
        {"number": 3, "title": "Bug B", "labels": [], "html_url": "u3", "body": ""},
    ]
    with respx.mock:
        respx.get(url__startswith="https://api.github.test/repos/octocat/hello-world/issues").mock(
            return_value=httpx.Response(200, json=issues_payload)
        )
        issues = await service.list_issues_by_label(
            parse_repository_url("https://github.com/octocat/hello-world"),
            "good first issue",
            count=5,
        )
    numbers = [issue["number"] for issue in issues]
    assert numbers == [1, 3]


async def test_get_tree_paths_returns_blob_paths():
    service = make_service()
    tree_payload = {
        "tree": [
            {"type": "blob", "path": "src/app.py"},
            {"type": "tree", "path": "src"},
            {"type": "blob", "path": "README.md"},
        ],
        "truncated": False,
    }
    with respx.mock:
        respx.get(
            "https://api.github.test/repos/octocat/hello-world/git/trees/main?recursive=1"
        ).mock(return_value=httpx.Response(200, json=tree_payload))
        paths = await service.get_tree_paths(
            parse_repository_url("https://github.com/octocat/hello-world"), "main"
        )
    assert paths == ["src/app.py", "README.md"]


async def test_get_contributing_falls_back_through_paths():
    service = make_service()
    with respx.mock:
        respx.get("https://api.github.test/repos/octocat/hello-world/contents/CONTRIBUTING.md").mock(
            return_value=httpx.Response(404, json={})
        )
        respx.get(
            "https://api.github.test/repos/octocat/hello-world/contents/.github/CONTRIBUTING.md"
        ).mock(return_value=httpx.Response(200, text="# Contributing"))
        text = await service.get_contributing(
            parse_repository_url("https://github.com/octocat/hello-world")
        )
    assert text == "# Contributing"


async def test_extract_screenshot_urls_finds_images():
    body = (
        "Screenshot: https://user-images.githubusercontent.com/1/a.png\n"
        "log: https://example.com/file.txt\n"
        "also https://user-images.githubusercontent.com/1/b.jpg?raw=true"
    )
    urls = GitHubService.extract_screenshot_urls(body)
    assert len(urls) == 2
    assert urls[0].endswith(".png")
    assert "b.jpg" in urls[1]


async def test_download_image_rejects_unknown_host():
    service = make_service()
    data = await service.download_image("https://evil.example.com/x.png", 1024)
    assert data is None
