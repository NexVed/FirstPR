from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from app.ai.schemas import (
    IssueRecommendationBatch,
    RepositoryConventions,
)
from tests.conftest import PNG_BYTES, make_app

GITHUB = "https://api.github.test"


def github_routes():
    respx.get(f"{GITHUB}/repos/octocat/hello-world").mock(
        return_value=httpx.Response(
            200,
            json={
                "full_name": "octocat/hello-world",
                "description": "demo",
                "default_branch": "main",
                "stargazers_count": 12,
                "language": "Python",
                "html_url": "https://github.com/octocat/hello-world",
                "private": False,
            },
        )
    )
    respx.get(f"{GITHUB}/repos/octocat/hello-world/readme").mock(
        return_value=httpx.Response(200, text="# Hello\n\nInstall: pip install -e .")
    )
    respx.get(f"{GITHUB}/repos/octocat/hello-world/contents/CONTRIBUTING.md").mock(
        return_value=httpx.Response(200, text="Run tests: pytest")
    )
    respx.get(
        f"{GITHUB}/repos/octocat/hello-world/git/trees/main?recursive=1"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "README.md"},
                    {"type": "blob", "path": "src/handlers.py"},
                    {"type": "blob", "path": "src/handlers_test.py"},
                    {"type": "blob", "path": "package-lock.json"},
                    {"type": "blob", "path": "node_modules/x/index.js"},
                    {"type": "blob", "path": "assets/logo.png"},
                ],
            },
        )
    )
    issues_payload = [
        {
            "number": 101,
            "title": "Handle empty input",
            "labels": [{"name": "good first issue"}],
            "html_url": "https://github.com/octocat/hello-world/issues/101",
            "body": "See screenshot https://user-images.githubusercontent.com/u/s1.png",
            "user": {"login": "alice"},
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "number": 102,
            "title": "Improve docs",
            "labels": [{"name": "good first issue"}],
            "html_url": "https://github.com/octocat/hello-world/issues/102",
            "body": "",
            "user": {"login": "bob"},
            "created_at": "2026-01-02T00:00:00Z",
        },
    ]
    respx.get(
        url__startswith=f"{GITHUB}/repos/octocat/hello-world/issues"
    ).mock(return_value=httpx.Response(200, json=issues_payload))
    respx.get("https://user-images.githubusercontent.com/u/s1.png").mock(
        return_value=httpx.Response(200, content=PNG_BYTES)
    )


def fake_ai_outputs():
    return {
        RepositoryConventions: {
            "setup_commands": ["pip install -e ."],
            "test_command": "pytest",
            "lint_command": None,
            "pr_rules": ["One change per PR"],
        },
        IssueRecommendationBatch: {
            "recommendations": [
                {
                    "issue_number": 101,
                    "title": "Ignored - server uses GitHub title",
                    "difficulty": 2,
                    "files": ["src/handlers.py", "invented/path.py"],
                    "approach": "Add a guard clause.",
                    "first_step": "Open src/handlers.py.",
                    "screenshots_analyzed": True,
                },
                {
                    "issue_number": 102,
                    "title": "Improve docs",
                    "difficulty": 1,
                    "files": [],
                    "approach": "Update README.",
                    "first_step": "Edit README.md.",
                    "screenshots_analyzed": False,
                },
                {
                    "issue_number": 999,
                    "title": "Hallucinated",
                    "difficulty": 1,
                    "files": [],
                    "approach": "",
                    "first_step": "",
                    "screenshots_analyzed": False,
                },
            ]
        },
    }


def test_analyze_end_to_end():
    from tests.conftest import FakeAIProvider

    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    with respx.mock:
        github_routes()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/repositories/analyze",
                json={
                    "repository_url": "https://github.com/octocat/hello-world",
                    "issues": 6,
                    "top": 3,
                },
            )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["repository"]["full_name"] == "octocat/hello-world"
    assert body["conventions"]["test_command"] == "pytest"

    recs = body["recommendations"]
    numbers = [rec["issue_number"] for rec in recs]
    assert 999 not in numbers, "hallucinated issue numbers must be dropped"
    assert numbers == [102, 101], "sorted easiest first"

    rec101 = next(rec for rec in recs if rec["issue_number"] == 101)
    assert rec101["title"] == "Handle empty input", "title comes from GitHub"
    assert rec101["files"] == ["src/handlers.py"], "invented paths filtered"
    assert rec101["screenshots_analyzed"] is True
    assert rec101["url"].endswith("/issues/101")

    rec102 = next(rec for rec in recs if rec["issue_number"] == 102)
    assert rec102["screenshots_analyzed"] is False

    assert "test-service-key" not in str(body)


def test_analyze_persists_analysis():
    from tests.conftest import FakeAIProvider

    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    with respx.mock:
        github_routes()
        with TestClient(app) as client:
            client.post(
                "/api/v1/repositories/analyze",
                json={"repository_url": "https://github.com/octocat/hello-world"},
            )
    analyses = app.state.fake_db.store.get("repository_analyses", [])
    assert len(analyses) == 1
    assert analyses[0]["owner"] == "octocat"
    assert analyses[0]["recommendations"][0]["files"] == []
    activity = app.state.fake_db.store.get("activity_history", [])
    assert activity and activity[0]["activity_type"] == "repository_analyzed"


def test_analyze_requires_auth():
    from app.api.deps import get_current_user

    app = make_app()
    app.dependency_overrides.pop(get_current_user)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/octocat/hello-world"},
        )
    assert response.status_code == 401
