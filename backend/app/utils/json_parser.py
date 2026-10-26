"""Extract the first JSON object/array from noisy model output.

Models wrap JSON in markdown fences, add prose before/after, or emit
reasoning text. This parser handles all three without eval.
"""

from __future__ import annotations

import json

_FENCE = "```"


def extract_json_text(text: str) -> str:
    if not text:
        raise ValueError("Empty model response")

    # Preferred: fenced block, ```json ... ``` or plain ``` ... ```.
    index = 0
    candidates: list[str] = []
    while True:
        start = text.find(_FENCE, index)
        if start == -1:
            break
        line_end = text.find("\n", start)
        if line_end == -1:
            break
        language = text[start + 3 : line_end].strip().lower()
        end = text.find(_FENCE, line_end + 1)
        if end == -1:
            break
        body = text[line_end + 1 : end]
        if language in ("", "json"):
            candidates.append(body.strip())
        index = end + 3
    for candidate in candidates:
        if _parses(candidate):
            return candidate

    # Fallback: balanced scan for the first {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        found = _find_balanced(text, opener, closer)
        if found is not None:
            snippet = found
            if _parses(snippet):
                return snippet
            # Trailing commas and stray closing braces are common noise.
            cleaned = _strip_trailing_commas(snippet)
            if _parses(cleaned):
                return cleaned

    raise ValueError("No JSON object found in model response")


def _find_balanced(text: str, opener: str, closer: str) -> str | None:
    start = text.find(opener)
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for position in range(start, len(text)):
        char = text[position]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : position + 1]
    return None


def _strip_trailing_commas(snippet: str) -> str:
    result: list[str] = []
    for position, char in enumerate(snippet):
        if char == ",":
            rest = snippet[position + 1 :].lstrip()
            if rest and rest[0] in ("}", "]"):
                continue
        result.append(char)
    return "".join(result)


def _parses(candidate: str) -> bool:
    try:
        json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return False
    return True


def parse_json_object(text: str) -> dict:
    extracted = extract_json_text(text)
    try:
        value = json.loads(extracted)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Model response JSON is not an object")
    return value
