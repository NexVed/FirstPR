"""OpenAI-compatible chat completions provider.

Works with Ollama, vLLM, llama.cpp servers and self-hosted models on
DigitalOcean GPU Droplets.
"""

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


def _normalize_endpoint(base_url: str) -> str:
    """Resolve the chat completions URL from a configured base URL."""
    base = base_url.strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


class OpenAICompatibleProvider(BaseAIProvider):
    name = "openai_compatible"

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: float,
    ):
        self._http = http
        self._endpoint = _normalize_endpoint(base_url)
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    def _build_messages(
        self, prompt: str, images: list[ImageInput] | None
    ) -> list[dict]:
        content: list[dict] = []
        for image in images or []:
            encoded = base64.b64encode(image.data).decode("ascii")
            data_uri = f"data:{image.mime_type};base64,{encoded}"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri},
                }
            )
        content.append({"type": "text", "text": prompt})
        return [{"role": "user", "content": content}]

    async def _complete(
        self,
        prompt: str,
        images: list[ImageInput] | None,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body = {
            "model": self._model,
            "messages": self._build_messages(prompt, images),
            "temperature": 0.2,
            "max_tokens": 2048,
        }

        for attempt in range(1, MAX_429_ATTEMPTS + 1):
            try:
                response = await self._http.post(
                    self._endpoint,
                    json=body,
                    headers=headers,
                    timeout=self._timeout,
                )
            except httpx.TimeoutException as exc:
                raise AIModelResponseError("AI provider timed out") from exc
            except httpx.HTTPError as exc:
                logger.warning(
                    "LLM request failed: %s", type(exc).__name__
                )
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
                    "OpenAI-compatible API error status=%s",
                    response.status_code,
                )
                raise AIModelResponseError("AI provider returned an error")

            payload = response.json()
            choices = payload.get("choices") or []
            if not choices:
                raise AIModelResponseError("AI provider returned no choices")
            message = choices[0].get("message") or {}
            text = message.get("content")
            if not isinstance(text, str) or not text.strip():
                raise AIModelResponseError(
                    "AI provider returned no text output"
                )
            return text

        raise AIModelResponseError("AI provider did not return a response")
