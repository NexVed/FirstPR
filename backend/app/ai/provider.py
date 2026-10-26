"""AI provider abstraction.

A provider turns a prompt (plus optional screenshot images) into a
validated Pydantic model. Providers must:

- Extract JSON from fenced or noisy output (never rely on JSON mode).
- Retry invalid structured responses with the validation error included
  in a corrective prompt.
- On HTTP 429 wait eight seconds and retry, up to three total attempts.
- Apply request timeouts and never log API keys.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ValidationError

from app.ai.schemas import (
    ContributionPlanDraft,
    IssueDraft,
    IssueRecommendationBatch,
    RepositoryConventions,
    ScreenshotAnalysis,
)
from app.core.exceptions import AIModelResponseError
from app.utils.json_parser import parse_json_object

MAX_429_ATTEMPTS = 3
RETRY_AFTER_429_SECONDS = 8.0
MAX_VALIDATION_RETRIES = 2

ModelT = TypeVar("ModelT", bound=BaseModel)

# Exported so services (and tests) can reference the structured outputs.
STRUCTURED_OUTPUTS = (
    RepositoryConventions,
    IssueRecommendationBatch,
    ScreenshotAnalysis,
    IssueDraft,
    ContributionPlanDraft,
)


@dataclass(frozen=True)
class ImageInput:
    """A screenshot to send to a multimodal model."""

    mime_type: str
    data: bytes


@runtime_checkable
class AIProvider(Protocol):
    name: str

    async def generate_json(
        self,
        prompt: str,
        response_model: type[ModelT],
        images: list[ImageInput] | None = None,
    ) -> ModelT:
        """Run the prompt and validate the model output against a schema."""
        ...


class BaseAIProvider:
    """Shared JSON extraction/validation loop over a raw text completion."""

    name: str = "base"

    async def _complete(
        self,
        prompt: str,
        images: list[ImageInput] | None,
    ) -> str:
        raise NotImplementedError

    async def generate_json(
        self,
        prompt: str,
        response_model: type[ModelT],
        images: list[ImageInput] | None = None,
    ) -> ModelT:
        current_prompt = prompt
        last_error: str | None = None
        last_output: str | None = None

        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            text = await self._complete(current_prompt, images)
            last_output = text
            try:
                payload = parse_json_object(text)
                return response_model.model_validate(payload)
            except ValueError as exc:
                last_error = str(exc)
            except ValidationError as exc:
                last_error = exc.errors(include_url=False)

            if attempt < MAX_VALIDATION_RETRIES:
                current_prompt = (
                    f"{prompt}\n\nYour previous response was invalid. "
                    f"Previous response:\n{last_output}\n\n"
                    f"Validation error: {last_error}\n"
                    "Return ONLY corrected JSON matching the requested schema."
                )

        raise AIModelResponseError(
            "Model did not return a valid structured response"
        ) from None


def model_to_dict(model: BaseModel) -> dict:
    return json.loads(model.model_dump_json())
