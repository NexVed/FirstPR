from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from app.ai.schemas import IssueDraft, ScreenshotAnalysis
from tests.conftest import PNG_BYTES, FakeAIProvider, make_app

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
    respx.get(
        f"{GITHUB}/repos/octocat/hello-world/git/trees/main?recursive=1"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "src/handlers.py"},
                    {"type": "blob", "path": "src/parser.py"},
                    {"type": "blob", "path": "README.md"},
                ],
            },
        )
    )
    issues_payload = [
        {
            "number": 50,
            "title": "TypeError when input is empty",
            "labels": [{"name": "good first issue"}],
            "html_url": "https://github.com/octocat/hello-world/issues/50",
            "body": "Crash traceback mentions parser",
            "user": {"login": "a"},
            "created_at": "2026-01-01T00:00:00Z",
        },
        {
            "number": 77,
            "title": "Unrelated styling bug",
            "labels": [],
            "html_url": "https://github.com/octocat/hello-world/issues/77",
            "body": "",
            "user": {"login": "b"},
            "created_at": "2026-01-02T00:00:00Z",
        },
        {
            "number": 78,
            "title": "PR not an issue",
            "labels": [],
            "html_url": "u",
            "body": "",
            "pull_request": {"url": "x"},
        },
    ]
    respx.get(url__startswith=f"{GITHUB}/repos/octocat/hello-world/issues").mock(
        return_value=httpx.Response(200, json=issues_payload)
    )


def fake_ai_outputs():
    return {
        ScreenshotAnalysis: {
            "summary": "A TypeError traceback is shown for empty input.",
            "visible_errors": [
                {
                    "error_type": "exception",
                    "message": "TypeError: cannot parse empty input in parser",
                    "location_hint": "parser.py",
                }
            ],
            "candidate_files": ["src/parser.py", "src/ghost.py"],
            "search_terms": ["parser", "typeerror", "empty"],
        },
        IssueDraft: {
            "title": "TypeError on empty input",
            "body": "## Steps to Reproduce\n1. Submit empty input.",
        },
    }


def test_triage_end_to_end():
    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    with respx.mock:
        github_routes()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/triage",
                data={"repository_url": "https://github.com/octocat/hello-world"},
                files={"image": ("bug.png", PNG_BYTES, "image/png")},
            )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["analysis"]["summary"].startswith("A TypeError")
    assert body["analysis"]["candidate_files"] == ["src/parser.py"], (
        "ghost paths validated against the real tree"
    )
    related = body["related_issues"]
    assert related and related[0]["number"] == 50
    assert all(item["number"] != 78 for item in related)
    assert body["draft"]["title"] == "TypeError on empty input"

    triages = app.state.fake_db.store.get("screenshot_triages", [])
    assert len(triages) == 1
    assert triages[0]["draft"]["title"] == "TypeError on empty input"

    fake_ai = app.state.fake_ai
    screenshot_calls = [call for call in fake_ai.calls if call[2]]
    assert len(screenshot_calls) == 1, "image sent exactly once (analysis call)"


def test_triage_rejects_oversized_image():
    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/triage",
            data={"repository_url": "https://github.com/octocat/hello-world"},
            files={"image": ("big.png", b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024), "image/png")},
        )
    assert response.status_code == 422
    assert "maximum" in response.json()["error"]["message"]


def test_triage_rejects_non_image():
    app = make_app(ai=FakeAIProvider(fake_ai_outputs()))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/triage",
            data={"repository_url": "https://github.com/octocat/hello-world"},
            files={"image": ("payload.txt", b"hello world", "text/plain")},
        )
    assert response.status_code == 422


def test_triage_note_is_optional_and_sanitized():
    outputs = fake_ai_outputs()
    app = make_app(ai=FakeAIProvider(outputs))
    with respx.mock:
        github_routes()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/triage",
                data={
                    "repository_url": "https://github.com/octocat/hello-world",
                    "note": "  crashed on my laptop  ",
                },
                files={"image": ("bug.png", PNG_BYTES, "image/png")},
            )
    assert response.status_code == 200
    triages = app.state.fake_db.store.get("screenshot_triages", [])
    assert triages[0]["note"] == "crashed on my laptop"
