from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FirstPR API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    frontend_origin: str = "http://localhost:3000"

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""

    gemini_api_key: str = ""
    gemma_model: str = "gemma-4-26b-a4b-it"

    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    github_token: str = ""

    max_upload_size_mb: int = 4
    request_timeout_seconds: float = 30.0
    log_level: str = "INFO"

    github_api_base: str = "https://api.github.com"
    gemma_api_base: str = (
        "https://generativelanguage.googleapis.com/v1beta/models"
    )

    app_version: str = "0.1.0"
    issue_page_size: int = 10
    candidate_paths_per_issue: int = Field(default=40, ge=5, le=100)

    @model_validator(mode="after")
    def validate_required(self) -> "Settings":
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", self.supabase_url),
                ("SUPABASE_KEY", self.supabase_key),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                "Missing required configuration: " + ", ".join(missing)
            )
        if not self.supabase_jwt_secret.strip():
            raise ValueError(
                "Missing required configuration: SUPABASE_JWT_SECRET"
            )
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def ai_provider_status(self) -> str:
        if self.gemini_api_key.strip():
            return "gemma"
        if (
            self.llm_base_url.strip()
            and self.llm_model.strip()
            and self.llm_api_key.strip()
        ):
            return "openai_compatible"
        return "none"

    def has_ai_provider(self) -> bool:
        return self.ai_provider_status() != "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()
