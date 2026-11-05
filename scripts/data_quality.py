#!/usr/bin/env python3
"""Small shared contract for build-data record-quality diagnostics."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

SEVERITIES = ("info", "warning", "recoverable_error", "fatal_error")


def make_issue(
    severity: str,
    category: str,
    *,
    media_type: str | None = None,
    tmdb_id: Any = None,
    title: Any = "",
    field: str | None = None,
    input_value: Any = None,
    source_value: Any = None,
    action: str = "reported",
    message: str = "",
) -> dict[str, Any]:
    normalized = str(severity or "").strip().lower()
    if normalized not in SEVERITIES:
        raise ValueError(f"Unsupported data-quality severity: {severity}")
    return {
        "severity": normalized,
        "category": str(category or "unknown"),
        "media_type": media_type,
        "tmdb_id": tmdb_id,
        "title": str(title or ""),
        "field": field,
        "input_value": input_value,
        "source_value": source_value,
        "action": str(action or "reported"),
        "message": str(message or ""),
    }


def summarize(issues: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(issue.get("severity") or "").lower() for issue in issues)
    return {severity: int(counts.get(severity, 0)) for severity in SEVERITIES}


def fatal_count(summary: dict[str, int]) -> int:
    return int(summary.get("fatal_error", 0))


def canonical_runtime_value(input_value: Any, source_value: Any) -> Any:
    """Prefer the authoritative external value while leaving authored input untouched."""
    return source_value if source_value not in (None, "") else input_value

