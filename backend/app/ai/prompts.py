"""Fixed prompt templates for the FirstPR pipelines.

The AI pipeline is a fixed, validated sequence of calls — never a
free-roaming agent. Each template ends with an explicit JSON contract.
"""

from __future__ import annotations

import json

from app.ai.schemas import ScreenshotAnalysis

_JSON_RULES = (
    "Respond with ONLY a JSON object, no markdown fences, no prose. "
    "Use only information present in the provided context; never invent "
    "commands, file paths or repository facts."
)


def build_conventions_prompt(
    *,
    repo_name: str,
    repo_description: str | None,
    readme: str,
    contributing: str,
) -> str:
    return f"""You are analyzing documentation for the open-source repository "{repo_name}".
Repository description: {repo_description or "(none)"}

--- README (truncated) ---
{readme}

--- CONTRIBUTING (truncated) ---
{contributing or "(not found)"}
--- END ---

Extract the contribution conventions ONLY where the documentation explicitly supports them.
Do not invent setup commands. If the test or lint command is not documented, set it to null.

{_JSON_RULES}
Return JSON with exactly these keys:
{{
  "setup_commands": ["..."],
  "test_command": "..." | null,
  "lint_command": "..." | null,
  "pr_rules": ["..."]
}}"""


def build_issue_scoring_prompt(
    *,
    repo_name: str,
    conventions: dict,
    issues: list[dict],
    candidate_paths: dict[int, list[str]],
    screenshot_context: dict[int, str],
) -> str:
    issues_blob = json.dumps(issues, indent=2)
    paths_blob = json.dumps(
        {str(number): paths for number, paths in candidate_paths.items()},
        indent=2,
    )
    screenshots_blob = json.dumps(screenshot_context, indent=2)
    return f"""You are assisting a first-time contributor to "{repo_name}".

Repository conventions: {json.dumps(conventions, indent=2)}

GitHub issues to analyze: {issues_blob}

For each issue, candidate files found by keyword matching (real paths from the repository tree): {paths_blob}

Issue screenshot observations: {screenshots_blob}

Score every issue and recommend the files to change:
- "difficulty": integer 1 (very easy) to 5 (hard).
- "files": at most 4 paths, chosen ONLY from the candidate paths listed for that issue.
- "approach": one or two sentences describing how to fix the issue.
- "first_step": the single concrete first action for a newcomer.
- "screenshots_analyzed": true only when screenshot observations were actually provided above for that issue.

{_JSON_RULES}
Return JSON: {{"recommendations": [{{"issue_number": <int>, "title": <str>, "difficulty": <int>, "files": ["..."], "approach": <str>, "first_step": <str>, "screenshots_analyzed": <bool>}}]}}
Include one recommendation per issue, in the same order."""


def build_triage_prompt(*, note: str | None) -> str:
    note_block = f"User note about the bug: {note}\n" if note else ""
    return f"""You are triaging a bug screenshot from an open-source repository.
{note_block}Look at the image and report what is visibly wrong.

{_JSON_RULES}
Return JSON with exactly these keys:
{{
  "summary": "<one sentence describing the visible problem>",
  "visible_errors": [{{"error_type": "<e.g. exception|stack_trace|ui_error|build_error>", "message": "<exact visible text of the error>", "location_hint": "<file or component name visible, or null>"}}],
  "candidate_files": ["<likely source file paths responsible, repository-relative>"],
  "search_terms": ["<short keywords to find related code and issues>"]
}}"""


def build_issue_draft_prompt(
    *,
    analysis: ScreenshotAnalysis,
    related_issues: list[dict],
) -> str:
    related_blob = json.dumps(related_issues, indent=2)
    errors_blob = json.dumps(
        [error.model_dump() for error in analysis.visible_errors], indent=2
    )
    return f"""Draft a GitHub issue for the bug shown in the screenshot.

Screenshot summary: {analysis.summary}
Visible errors: {errors_blob}
Likely files involved: {json.dumps(analysis.candidate_files)}

Potentially related existing issues (do NOT duplicate them; reference them if relevant): {related_blob}

Write the issue body in GitHub markdown with sections: Steps to Reproduce, Expected Behavior, Actual Behavior, Environment notes.
Keep it factual; only use details visible in the screenshot data above.

{_JSON_RULES}
Return JSON: {{"title": "<concise issue title>", "body": "<markdown body>"}}"""


def build_plan_prompt(
    *,
    repo_name: str,
    issue: dict,
    conventions: dict,
    context_paths: list[str],
) -> str:
    issue_blob = json.dumps(issue, indent=2)
    return f"""Create a personalized contribution plan for a first-time open-source contributor.

Repository: {repo_name}
Conventions: {json.dumps(conventions, indent=2)}
Issue: {issue_blob}
Real files from the repository that may be relevant: {json.dumps(context_paths)}

Rules:
- "files_to_touch" must contain ONLY paths from the provided list.
- "setup_steps" must only contain commands documented above; if none are documented, use generic steps like "Install dependencies per README".
- "estimated_difficulty": integer 1-5.

{_JSON_RULES}
Return JSON: {{"overview": <str>, "setup_steps": ["..."], "implementation_steps": ["..."], "files_to_touch": ["..."], "testing_strategy": <str>, "pr_checklist": ["..."], "estimated_difficulty": <int>}}"""


MAX_DOC_CHARS = 2500


def truncate_document(text: str) -> str:
    if len(text) <= MAX_DOC_CHARS:
        return text
    return text[:MAX_DOC_CHARS] + "\n... (truncated)"
