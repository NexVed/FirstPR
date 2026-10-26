import logging
import sys

from app.core.config import Settings

_SENSITIVE_ENV_KEYS = {
    "GEMINI_API_KEY",
    "LLM_API_KEY",
    "GITHUB_TOKEN",
    "SUPABASE_KEY",
    "SUPABASE_JWT_SECRET",
}


def setup_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for noisy in ("httpx", "httpcore", "postgrest", "supabase"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def redact(value: str | None) -> str:
    """Return a safe representation of a potentially secret value."""
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-2:]}"


def redact_url(url: str) -> str:
    """Strip credentials embedded in a URL before logging it."""
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        host = rest.rsplit("@", 1)[1]
        return f"{scheme}://{host}"
    return url


__all__ = [
    "setup_logging",
    "get_logger",
    "redact",
    "redact_url",
    "_SENSITIVE_ENV_KEYS",
]
