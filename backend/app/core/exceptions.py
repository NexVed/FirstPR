"""Application exception hierarchy.

Every error the API raises intentionally derives from AppError so that
response bodies stay structured and never leak internal details.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected, user-facing errors."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ConfigurationError(AppError):
    """A required integration is not configured or misconfigured."""

    status_code = 503
    code = "configuration_error"


class GitHubError(AppError):
    status_code = 502
    code = "github_error"


class RepositoryNotFoundError(GitHubError):
    status_code = 404
    code = "repository_not_found"


class GitHubAuthError(GitHubError):
    status_code = 502
    code = "github_auth_error"


class GitHubRateLimitError(GitHubError):
    status_code = 429
    code = "github_rate_limit"


class InvalidRepositoryURLError(AppError):
    status_code = 422
    code = "invalid_repository_url"


class AIError(AppError):
    status_code = 502
    code = "ai_error"


class AIProviderNotConfiguredError(ConfigurationError):
    code = "ai_provider_not_configured"


class AIModelResponseError(AIError):
    code = "ai_model_response_error"


class InvalidImageError(AppError):
    status_code = 422
    code = "invalid_image"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class DatabaseError(AppError):
    status_code = 502
    code = "database_error"
