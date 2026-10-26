from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_ai_provider, get_current_user
from app.core.exceptions import (
    AIProviderNotConfiguredError,
    InvalidRepositoryURLError,
)
from app.utils.github_urls import parse_repository_url
from tests.conftest import make_app

VALID_URLS = [
    "https://github.com/owner/repo",
    "https://github.com/owner/repo/",
    "https://github.com/owner/repo.git",
    "https://www.github.com/owner/repo",
]

INVALID_URLS = [
    "http://github.com/owner/repo",
    "https://gitlab.com/owner/repo",
    "https://github.com/owner/repo/tree/main",
    "https://github.com/owner/repo/issues/1",
    "https://user:pass@github.com/owner/repo",
    "https://github.com/owner/",
    "https://github.com/",
    "https://github.com/owner/repo?tab=readme",
    "",
    "https://github.com/owner/re%20po",
]


@pytest.mark.parametrize("url", VALID_URLS)
def test_valid_repository_urls_normalize(url):
    ref = parse_repository_url(url)
    assert ref.https_url == "https://github.com/owner/repo"


@pytest.mark.parametrize("url", INVALID_URLS)
def test_invalid_repository_urls_rejected(url):
    with pytest.raises(InvalidRepositoryURLError):
        parse_repository_url(url)


def test_protected_endpoint_requires_token():
    from app.api.deps import get_current_user as dep

    app = make_app()
    app.dependency_overrides.pop(dep)
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_protected_endpoint_rejects_garbage_token():
    from app.api.deps import get_current_user as dep

    app = make_app()
    app.dependency_overrides.pop(dep)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"}
        )
    assert response.status_code == 401


def test_users_me_returns_token_identity():
    app = make_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "user-1"
    assert body["display_name"] == "Dev Tester"


def test_ai_endpoint_returns_503_without_provider():
    app = make_app()
    app.dependency_overrides.pop(get_ai_provider)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/octocat/hello-world"},
        )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "ai_provider_not_configured"
    assert "GEMINI_API_KEY" in body["error"]["message"]


def test_settings_reject_missing_supabase():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(supabase_url="", supabase_key="")


def test_settings_accept_openai_compatible_without_gemma():
    settings = Settings(
        supabase_url="http://s.test",
        supabase_key="k",
        supabase_jwt_secret="s",
        llm_base_url="http://localhost:11434",
        llm_model="gemma3",
        llm_api_key="llm-key",
    )
    assert settings.ai_provider_status() == "openai_compatible"


def test_dashboard_and_activity_flow():
    app = make_app()
    app.state.fake_db.store["activity_history"] = [
        {
            "id": "act-1",
            "user_id": "user-1",
            "activity_type": "repository_analyzed",
            "summary": {"repository": "octocat/hello-world"},
            "entity_id": None,
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    with TestClient(app) as client:
        dashboard = client.get("/api/v1/dashboard").json()
        activity = client.get("/api/v1/activity").json()

    assert dashboard["recent_activity"][0]["activity_type"] == "repository_analyzed"
    assert activity["activity"][0]["id"] == "act-1"
