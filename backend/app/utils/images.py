"""Screenshot upload validation: size limit and magic-byte content sniffing."""

from __future__ import annotations

from app.core.exceptions import InvalidImageError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"

MIME_BY_SIGNATURE: tuple[tuple[bytes, str], ...] = (
    (PNG_SIGNATURE, "image/png"),
    (JPEG_SIGNATURE, "image/jpeg"),
)


def detect_mime_type(data: bytes) -> str:
    for signature, mime in MIME_BY_SIGNATURE:
        if data.startswith(signature):
            return mime
    raise InvalidImageError(
        "Unsupported image format: only PNG and JPEG screenshots are accepted"
    )


def validate_image(data: bytes, *, max_bytes: int) -> str:
    """Validate a screenshot upload and return its MIME type."""
    if not data:
        raise InvalidImageError("Image is empty")
    if len(data) > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise InvalidImageError(
            f"Image exceeds the maximum size of {limit_mb:g} MB"
        )
    return detect_mime_type(data)
