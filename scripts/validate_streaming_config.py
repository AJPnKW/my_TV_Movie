#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "web" / "config.json"

BUILDABLE_STATUSES = {"ok", "warn", "candidate"}
INACTIVE_STATUSES = {"blocked", "archived", "disabled"}
VALID_STATUSES = BUILDABLE_STATUSES | INACTIVE_STATUSES
REQUIRED_VISIBLE_KEYS = [
    "vidcore",
    "vidfast",
    "vidlink",
    "vidsrc_pm",
    "vidsrc_to",
    "vidsrc_cc",
    "2embed_skin",
    "nontongo",
    "moviesapi",
    "smashystream",
    "autoembed",
    "frembed",
    "vsem",
    "videasy",
    "superembed",
    "multiembed",
]


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def main() -> int:
    issues: list[str] = []
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    streaming = config.get("streaming") if isinstance(config, dict) else None
    if not isinstance(streaming, dict):
        issues.append("web/config.json must contain streaming object")
        streaming = {}

    providers = streaming.get("embed_providers")
    if not isinstance(providers, list) or not providers:
        issues.append("streaming.embed_providers must be a non-empty array")
        providers = []

    seen_keys: set[str] = set()
    buildable_keys: set[str] = set()
    for idx, provider in enumerate(providers):
        if not isinstance(provider, dict):
            issues.append(f"streaming.embed_providers[{idx}] must be an object")
            continue
        key = _safe_text(provider.get("key"))
        name = _safe_text(provider.get("name")) or key
        status = _safe_text(provider.get("status")).lower() or "ok"
        enabled = provider.get("enabled", True) is not False
        tv_template = _safe_text(provider.get("tv_template"))
        movie_template = _safe_text(provider.get("movie_template"))
        if not key:
            issues.append(f"streaming.embed_providers[{idx}] missing key")
            continue
        if key in seen_keys:
            issues.append(f"streaming.embed_providers[{idx}] duplicate key={key}")
        seen_keys.add(key)
        if status not in VALID_STATUSES:
            issues.append(f"streaming.embed_providers[{idx}] {name} has invalid status={status!r}")
        for field in ("style", "tier", "tmdb_format"):
            if field not in provider:
                issues.append(f"streaming.embed_providers[{idx}] {name} missing metadata field={field}")
        if enabled and status in BUILDABLE_STATUSES:
            buildable_keys.add(key)
            if not tv_template or not movie_template:
                issues.append(f"streaming.embed_providers[{idx}] {name} is buildable and must define tv_template and movie_template")
            for field, template in (("tv_template", tv_template), ("movie_template", movie_template)):
                if template and not template.startswith("https://"):
                    issues.append(f"streaming.embed_providers[{idx}] {name}.{field} must be an https template")
        elif status in INACTIVE_STATUSES and (tv_template or movie_template) and not (tv_template and movie_template):
            issues.append(f"streaming.embed_providers[{idx}] {name} inactive templates must be both blank or both defined")
        elif enabled and status in INACTIVE_STATUSES:
            issues.append(f"streaming.embed_providers[{idx}] {name} cannot be enabled with inactive status={status}")

    fallback_order = [_safe_text(value) for value in (streaming.get("fallback_order") or []) if _safe_text(value)]
    if fallback_order != REQUIRED_VISIBLE_KEYS:
        issues.append("streaming.fallback_order must match the configured visible provider fallback chain")
    for key in fallback_order:
        if key not in buildable_keys:
            issues.append(f"streaming.fallback_order references non-buildable or missing provider key={key}")
    for key in REQUIRED_VISIBLE_KEYS:
        if key not in buildable_keys:
            issues.append(f"streaming.embed_providers must define buildable provider key={key}")

    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 1

    print(json.dumps({"streaming_config_validation": "passed", "buildable_provider_count": len(buildable_keys)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
