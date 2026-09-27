from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from a plain or Markdown-fenced model response."""

    cleaned = text.strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("The model did not return valid JSON.") from exc

    if not isinstance(value, dict):
        raise ValueError("The model response must be a JSON object.")
    return value
