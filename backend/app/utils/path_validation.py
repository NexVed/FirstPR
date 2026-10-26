"""Validate and normalize file paths suggested by models against the real tree."""

from __future__ import annotations

import posixpath


def normalize_path(path: str) -> str:
    """Normalize a repository-relative path or return '' if unusable."""
    if not path or not isinstance(path, str):
        return ""
    cleaned = path.strip().replace("\\", "/")
    cleaned = cleaned.lstrip("./")
    cleaned = posixpath.normpath(cleaned).replace("\\", "/")
    if cleaned in (".", "", "/"):
        return ""
    if cleaned.startswith("../") or cleaned.startswith("/"):
        return ""
    return cleaned


def validate_paths(
    candidates: list[str], valid_paths: set[str], *, limit: int
) -> list[str]:
    """Return unique, normalized paths that exist in the repository tree."""
    validated: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = normalize_path(candidate)
        if not normalized or normalized in seen:
            continue
        if normalized in valid_paths:
            seen.add(normalized)
            validated.append(normalized)
            if len(validated) >= limit:
                break
    return validated
