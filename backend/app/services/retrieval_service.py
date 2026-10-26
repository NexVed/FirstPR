"""Keyword-based candidate path retrieval from a filtered repository tree."""

from __future__ import annotations

import posixpath
import re

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "when", "while", "from",
    "into", "after", "before", "should", "would", "could", "have", "has",
    "not", "but", "are", "was", "were", "will", "does", "did", "issue",
    "bug", "error", "fail", "failed", "fix", "broken", "crash", "new",
    "add", "support", "using", "use", "can", "get", "set",
}

EXCLUDED_DIRECTORIES = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    "out",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    ".next",
    ".nuxt",
    ".cache",
    "target",
    ".terraform",
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff",
    ".svgz", ".avif", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".ogg",
    ".pdf", ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".jar", ".woff",
    ".woff2", ".ttf", ".eot", ".otf", ".psd", ".ai", ".exe", ".dll", ".so",
    ".dylib", ".o", ".a", ".pyc", ".pyo", ".class", ".bin", ".dat",
}

GENERATED_SUFFIXES = (".min.js", ".min.css", ".d.ts", ".map", ".snap")

LOCKFILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "npm-shrinkwrap.json",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
    "go.sum",
    "bun.lockb",
    "deno.lock",
    "uv.lock",
    "flake.lock",
}

SOURCE_DIRECTORIES = ("src", "lib", "app", "packages", "internal", "server", "core")
IGNORED_DIRECTORIES = ("docs", "doc", "test", "tests", "spec", "examples", "changelog", ".github")


def filter_tree_paths(paths: list[str]) -> tuple[list[str], set[str]]:
    """Split a raw tree into candidate-relevant paths and the full valid set."""
    relevant: list[str] = []
    valid: set[str] = set()
    for path in paths:
        valid.add(path)
        if _is_relevant(path):
            relevant.append(path)
    return relevant, valid


def _is_relevant(path: str) -> bool:
    segments = path.split("/")
    filename = segments[-1]
    lowered = [segment.lower() for segment in segments]
    lowered_name = filename.lower()

    if any(directory in EXCLUDED_DIRECTORIES for directory in lowered[:-1]):
        return False
    if lowered_name in LOCKFILES:
        return False
    extension = posixpath.splitext(lowered_name)[1]
    if extension in IMAGE_EXTENSIONS:
        return False
    if lowered_name.endswith(GENERATED_SUFFIXES):
        return False
    if lowered_name in ("changelog", "changelog.md", "license", "license.md", "notice"):
        return False
    if any(lowered_name.startswith(prefix) for prefix in ("CHANGELOG", "LICENSE", "NOTICE")):
        return False
    return True


def rank_candidate_paths(
    issue: dict, relevant_paths: list[str], *, limit: int
) -> list[str]:
    """Rank repository paths by keyword overlap with an issue."""
    terms = _issue_terms(issue)
    if not terms:
        return relevant_paths[:limit]

    scored: list[tuple[int, str, str]] = []
    for path in relevant_paths:
        score, filename = _score_path(path, terms)
        scored.append((score, filename, path))

    scored.sort(key=lambda item: (-item[0], item[2]))
    return [path for _, _, path in scored[:limit]]


def _issue_terms(issue: dict) -> set[str]:
    text = " ".join(
        [
            str(issue.get("title", "")),
            " ".join(issue.get("labels", []) or []),
            str(issue.get("body", ""))[:800],
        ]
    ).lower()
    tokens = set(TOKEN_PATTERN.findall(text))
    return {token for token in tokens if len(token) >= 3} - STOPWORDS


def _score_path(path: str, terms: set[str]) -> tuple[int, str]:
    filename = posixpath.basename(path).lower()
    stem = posixpath.splitext(filename)[0]
    stem_tokens = set(TOKEN_PATTERN.findall(stem))
    directory_tokens = set(
        TOKEN_PATTERN.findall(posixpath.dirname(path).lower())
    )

    score = 0
    score += 4 * len(terms & stem_tokens)
    score += 1 * len(terms & directory_tokens)

    lowered = path.lower()
    if lowered.startswith(SOURCE_DIRECTORIES) or any(
        f"/{source}/" in lowered for source in SOURCE_DIRECTORIES
    ):
        score += 1
    if any(f"/{ignored}/" in lowered for ignored in IGNORED_DIRECTORIES):
        score -= 1

    return score, filename
