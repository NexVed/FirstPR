"""Parse and validate GitHub repository URLs supplied by clients.

Only HTTPS GitHub URLs pointing at a plain owner/repository are accepted.
Credentials, extra path segments, unsupported hosts and plain HTTP are
rejected so user input can never redirect internal requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.core.exceptions import InvalidRepositoryURLError

ALLOWED_HOSTS = {"github.com", "www.github.com"}
_MAX_SEGMENT_LENGTH = 100
_ALLOWED_NAME_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


@dataclass(frozen=True)
class RepositoryRef:
    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def https_url(self) -> str:
        return f"https://github.com/{self.slug}"


def _validate_segment(value: str, label: str) -> str:
    if not value or len(value) > _MAX_SEGMENT_LENGTH:
        raise InvalidRepositoryURLError(f"Invalid {label} in repository URL")
    if not set(value) <= _ALLOWED_NAME_CHARS:
        raise InvalidRepositoryURLError(f"Invalid {label} in repository URL")
    if value.startswith(".") or value.endswith("."):
        raise InvalidRepositoryURLError(f"Invalid {label} in repository URL")
    return value


def parse_repository_url(raw_url: str) -> RepositoryRef:
    """Validate and normalize a user-supplied GitHub repository URL."""
    if not raw_url or not isinstance(raw_url, str):
        raise InvalidRepositoryURLError("Repository URL is required")

    url = raw_url.strip()
    if not url.lower().startswith("https://"):
        raise InvalidRepositoryURLError(
            "Repository URL must use HTTPS, e.g. https://github.com/owner/repo"
        )
    if "@" in url.split("://", 1)[1]:
        raise InvalidRepositoryURLError(
            "Repository URL must not contain credentials"
        )

    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise InvalidRepositoryURLError("Invalid repository URL") from exc

    if parts.hostname is None or parts.hostname.lower() not in ALLOWED_HOSTS:
        raise InvalidRepositoryURLError("Only github.com URLs are supported")

    path = parts.path.strip("/")
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) == 2:
        owner, name = segments
    elif len(segments) == 1 and segments[0].endswith(".git") and segments[0] != ".git":
        raise InvalidRepositoryURLError("Repository name is missing")
    elif len(segments) > 2:
        raise InvalidRepositoryURLError(
            "Repository URL must point to owner/repo only"
        )
    else:
        raise InvalidRepositoryURLError(
            "Repository URL must be https://github.com/owner/repo"
        )

    if name.endswith(".git"):
        name = name[: -len(".git")]

    owner = _validate_segment(owner, "owner")
    name = _validate_segment(name, "repository name")

    if parts.query or parts.fragment:
        raise InvalidRepositoryURLError(
            "Repository URL must not contain query or fragment"
        )

    return RepositoryRef(owner=owner, name=name)
