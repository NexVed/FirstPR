from fastapi.testclient import TestClient

from tests.conftest import make_app


def test_root_health_is_public():
    app = make_app()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_v1_health_reports_provider_status():
    app = make_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ai_provider"] in {"gemma", "openai_compatible", "none"}
    assert body["database"] == "configured"


def test_health_does_not_leak_secrets():
    app = make_app()
    with TestClient(app) as client:
        body = client.get("/api/v1/health").json()
    serialized = str(body)
    for secret in ("test-service-key", "gh-test-token", "test-jwt-secret"):
        assert secret not in serialized
