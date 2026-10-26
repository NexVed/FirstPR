from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import AIProvider
from app.core.config import Settings
from app.core.security import AuthUser
from app.main import create_app
from app.services.plan_service import PlanService
from app.services.repository_service import RepositoryAnalysisService
from app.services.triage_service import TriageService


class FakeResult:
    def __init__(self, data: list[dict[str, Any]]):
        self.data = data
        self.error = None
        self.count = len(data)


class FakeQuery:
    def __init__(self, store: dict[str, list], table: str, mode: str):
        self._store = store
        self._table = table
        self._mode = mode  # "write" or "read"
        self._payload: Any = None
        self._filters: list[tuple[str, Any]] = []
        self._order_column: str | None = None
        self._order_desc = False
        self._limit: int | None = None

    def insert(self, payload):
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        return self.insert(payload)

    def update(self, payload):
        self._payload = payload
        return self

    def select(self, *columns, **kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, column, desc=False):
        self._order_column = column
        self._order_desc = desc
        return self

    def limit(self, count):
        self._limit = count
        return self

    def execute(self) -> FakeResult:
        if self._mode == "write":
            rows = self._store.setdefault(self._table, [])
            payload = dict(self._payload)
            if isinstance(payload, list):
                for row in payload:
                    self._stamp(row)
                rows.extend(payload)
                result = [dict(row) for row in payload]
            else:
                self._stamp(payload)
                rows.append(payload)
                result = [dict(payload)]
            return FakeResult(result)

        rows = self._store.get(self._table, [])
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        if self._order_column:
            rows = sorted(
                rows,
                key=lambda row: row.get(self._order_column) or "",
                reverse=self._order_desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return FakeResult([dict(row) for row in rows])

    @staticmethod
    def _stamp(row: dict[str, Any]) -> None:
        row.setdefault("id", str(uuid.uuid4()))
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())


class FakeSupabase:
    """Minimal stand-in for the supabase-py client."""

    def __init__(self):
        self.store: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.store, name, mode="write")

    def read(self, name: str) -> FakeQuery:
        return FakeQuery(self.store, name, mode="read")


class FakeAIProvider(AIProvider):
    """Returns canned validated outputs keyed by response model."""

    name = "fake"

    def __init__(self, outputs: dict[type, dict] | None = None):
        self.outputs = outputs or {}
        self.calls: list[tuple[str, type, list | None]] = []

    async def generate_json(self, prompt, response_model, images=None):
        self.calls.append((prompt, response_model, images))
        canned = self.outputs.get(response_model)
        if canned is None:
            raise AssertionError(
                f"No canned output configured for {response_model.__name__}"
            )
        return response_model.model_validate(canned)


TEST_USER = AuthUser(
    user_id="user-1", email="dev@example.com", full_name="Dev Tester"
)


def base_settings() -> Settings:
    return Settings(
        app_env="test",
        supabase_url="http://supabase.test",
        supabase_key="test-service-key",
        supabase_jwt_secret="test-jwt-secret",
        github_token="gh-test-token",
        request_timeout_seconds=5,
        frontend_origin="http://localhost:5173",
    )


def make_app(settings: Settings | None = None, ai: FakeAIProvider | None = None):
    settings = settings or base_settings()
    app = create_app(settings)

    fake_db = FakeSupabase()
    fake_ai = ai or FakeAIProvider()
    app.dependency_overrides[get_current_user_dep()] = lambda: TEST_USER
    app.dependency_overrides[db_dep()] = lambda: fake_db
    app.dependency_overrides[ai_dep()] = lambda: fake_ai

    def repository_service(request):
        return RepositoryAnalysisService(
            settings=settings, github=request.app.state.github, ai=fake_ai
        )

    def plan_service(request):
        return PlanService(
            settings=settings, github=request.app.state.github, ai=fake_ai
        )

    def triage_service(request):
        return TriageService(
            settings=settings, github=request.app.state.github, ai=fake_ai
        )

    app.dependency_overrides[repo_service_dep()] = repository_service
    app.dependency_overrides[plan_service_dep()] = plan_service
    app.dependency_overrides[triage_service_dep()] = triage_service
    app.state.fake_db = fake_db
    app.state.fake_ai = fake_ai
    return app


def get_current_user_dep():
    from app.api.deps import get_current_user

    return get_current_user


def db_dep():
    from app.api.deps import get_db_client

    return get_db_client


def ai_dep():
    from app.api.deps import get_ai_provider

    return get_ai_provider


def repo_service_dep():
    from app.api.deps import get_repository_service

    return get_repository_service


def plan_service_dep():
    from app.api.deps import get_plan_service

    return get_plan_service


def triage_service_dep():
    from app.api.deps import get_triage_service

    return get_triage_service


@pytest.fixture
def fake_db():
    return FakeSupabase()


@pytest.fixture
def test_client():
    app = make_app()
    with TestClient(app) as client:
        yield client, app


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDAT\x08\xd7c"
    b"\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)
