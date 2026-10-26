from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from app.ai.schemas import ContributionPlanDraft, RepositoryConventions
from tests.conftest import FakeAIProvider, make_app

GITHUB = "https://api.github.test"


def github_routes():
    respx.get(f"{GITHUB}/repos/octocat/hello-world").mock(
        return_value=httpx.Response(
            200,
            json={
                "full_name": "octocat/hello-world",
                "description": "demo",
                "default_branch": "main",
                "stargazers_count": 1,
                "language": "Python",
                "html_url": "https://github.com/octocat/hello-world",
                "private": False,
            },
        )
    )
    respx.get(f"{GITHUB}/repos/octocat/hello-world/readme").mock(
        return_value=httpx.Response(200, text="# Hello")
    )
    respx.get(f"{GITHUB}/repos/octocat/hello-world/contents/CONTRIBUTING.md").mock(
        return_value=httpx.Response(404, json={})
    )
    respx.get(
        f"{GITHUB}/repos/octocat/hello-world/git/trees/main?recursive=1"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "src/handlers.py"},
                    {"type": "blob", "path": "docs/intro.md"},
                ],
            },
        )
    )
    respx.get(f"{GITHUB}/repos/octocat/hello-world/issues/101").mock(
        return_value=httpx.Response(
            200,
            json={
                "number": 101,
                "title": "Handle empty input",
                "labels": [{"name": "good first issue"}],
                "html_url": "https://github.com/octocat/hello-world/issues/101",
                "body": "Empty crash",
                "user": {"login": "alice"},
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
    )


def fake_ai_outputs():
    return {
        RepositoryConventions: {
            "setup_commands": [],
            "test_command": None,
            "lint_command": None,
            "pr_rules": [],
        },
        ContributionPlanDraft: {
            "overview": "Add input validation.",
            "setup_steps": ["Install per README"],
            "implementation_steps": ["Guard clause", "Add test"],
            "files_to_touch": ["src/handlers.py", "ghost.py"],
            "testing_strategy": "Run the suite.",
            "pr_checklist": ["Tests pass"],
            "estimated_difficulty": 2,
        },
    }


def test_create_plan_end_to_end():
    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    with respx.mock:
        github_routes()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/plans",
                json={
                    "repository_url": "https://github.com/octocat/hello-world",
                    "issue_number": 101,
                },
            )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["issue"]["number"] == 101
    assert body["plan"]["files_to_touch"] == ["src/handlers.py"], (
        "ghost paths must be validated away"
    )
    assert body["plan"]["estimated_difficulty"] == 2

    plans = app.state.fake_db.store.get("contribution_plans", [])
    assert len(plans) == 1
    assert plans[0]["issue_title"] == "Handle empty input"


def test_plan_reuses_latest_analysis_conventions():
    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    app.state.fake_db.store["repository_analyses"] = [
        {
            "id": "a1",
            "user_id": "user-1",
            "repository_url": "https://github.com/octocat/hello-world",
            "owner": "octocat",
            "name": "hello-world",
            "conventions": {"setup_commands": ["make dev"], "test_command": "make test", "lint_command": None, "pr_rules": []},
            "recommendations": [],
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    with respx.mock:
        github_routes()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/plans",
                json={
                    "repository_url": "https://github.com/octocat/hello-world",
                    "issue_number": 101,
                },
            )
    assert response.status_code == 200
    fake_ai = app.state.fake_ai
    conventions_calls = [
        call
        for call in fake_ai.calls
        if call[1] is RepositoryConventions
    ]
    assert conventions_calls == [], (
        "stored conventions should be reused, no extra AI call"
    )


def test_list_plans_returns_rows():
    app = make_app()
    app.state.fake_db.store["contribution_plans"] = [
        {
            "id": "p1",
            "user_id": "user-1",
            "repository_url": "https://github.com/octocat/hello-world",
            "issue_number": 101,
            "issue_title": "Handle empty input",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    with TestClient(app) as client:
        response = client.get("/api/v1/plans")
    assert response.status_code == 200
    assert response.json()["plans"][0]["issue_number"] == 101
