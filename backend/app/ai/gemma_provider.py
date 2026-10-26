"""Gemma via the native Gemini-compatible generateContent endpoint."""

from __future__ import annotations

import asyncio
import base64

import httpx

from app.ai.provider import (
    BaseAIProvider,
    ImageInput,
    MAX_429_ATTEMPTS,
    RETRY_AFTER_429_SECONDS,
)
from app.core.exceptions import AIModelResponseError
from app.core.logging import get_logger

logger = get_logger(__name__)


class GemmaProvider(BaseAIProvider):
    """Calls Gemma through the configured Gemini-compatible endpoint."""

    name = "gemma"

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        api_base: str,
        api_key: str,
        model: str,
        timeout: float,
    ):
        self._http = http
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def _endpoint(self) -> str:
        return f"{self._api_base}/{self._model}:generateContent"

    def _build_body(
        self, prompt: str, images: list[ImageInput] | None
    ) -> dict:
        parts: list[dict] = []
        for image in images or []:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": image.mime_type,
                        "data": base64.b64encode(image.data).decode("ascii"),
                    }
                }
            )
        # Fold the instruction prompt into the user text; no system role.
        parts.append({"text": prompt})
        return {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
                "thinkingConfig": {"thinkingLevel": "MINIMAL"},
            },
        }

    async def _complete(
        self,
        prompt: str,
        images: list[ImageInput] | None,
    ) -> str:
        body = self._build_body(prompt, images)
        headers = {"x-goog-api-key": self._api_key}

        for attempt in range(1, MAX_429_ATTEMPTS + 1):
            try:
                logger.info("Gemma request started (attempt %d)", attempt)
                response = await asyncio.wait_for(
                    self._http.post(
                        self._endpoint(),
                        json=body,
                        headers=headers,
                        timeout=self._timeout,
                    ),
                    timeout=self._timeout,
                )
                logger.info("Gemma response status=%d (attempt %d)", response.status_code, attempt)
            except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
                raise AIModelResponseError(
                    "AI provider timed out"
                ) from exc
            except httpx.HTTPError as exc:
                logger.warning("Gemma request failed: %s", type(exc).__name__)
                raise AIModelResponseError(
                    "AI provider request failed"
                ) from exc

            if response.status_code == 429 and attempt < MAX_429_ATTEMPTS:
                await asyncio.sleep(RETRY_AFTER_429_SECONDS)
                continue

            if response.status_code == 429:
                raise AIModelResponseError(
                    "AI provider rate limit exceeded, try again shortly"
                )

            if response.status_code >= 400:
                logger.warning(
                    "Gemma API error status=%s", response.status_code
                )
                raise AIModelResponseError(
                    "AI provider returned an error"
                )

            return self._extract_text(response.json())

        raise AIModelResponseError("AI provider did not return a response")

    @staticmethod
    def _extract_text(payload: dict) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            raise AIModelResponseError("AI provider returned no candidates")
        content = candidates[0].get("content") or {}
        chunks: list[str] = []
        for part in content.get("parts") or []:
            # Skip reasoning parts flagged as thought.
            if part.get("thought"):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
        if not chunks:
            raise AIModelResponseError("AI provider returned no text output")
        return "".join(chunks)
