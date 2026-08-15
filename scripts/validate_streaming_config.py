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
    "vsem",
    "vidsrc_pm",
    "vidcore",
    "vidfast",
    "vidlink",
    "vidsrc_to",
    "vidsrc_cc",
    "2embed_skin",
    "nontongo",
    "moviesapi",
    "smashystream",
    "autoembed",
    "frembed",
    "videasy",
    "superembed",
    "multiembed",
]
EXPECTED_PROVIDER_TEMPLATES = {
    "vsem": {
        "base_url": "https://vsembed.ru",
        "tv_template": "https://vsembed.ru/embed/tv/{tmdb_id}/{season}/{episode}",
        "movie_template": "https://vsembed.ru/embed/movie/{tmdb_id}",
        "sample_tv": "https://vsembed.ru/embed/tv/108978/4/3",
        "sample_movie": "https://vsembed.ru/embed/movie/937249",
    }
}


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
    providers_by_key: dict[str, dict[str, Any]] = {}
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
        providers_by_key[key] = provider
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

    for key, expected in EXPECTED_PROVIDER_TEMPLATES.items():
        provider = providers_by_key.get(key)
        if not provider:
            issues.append(f"streaming.embed_providers missing expected provider key={key}")
            continue
        for field in ("base_url", "tv_template", "movie_template"):
            if _safe_text(provider.get(field)) != expected[field]:
                issues.append(f"streaming.embed_providers[{key}] {field} drifted from baseline")
        sample_tv = _safe_text(provider.get("tv_template")).replace("{tmdb_id}", "108978").replace("{season}", "4").replace("{episode}", "3")
        sample_movie = _safe_text(provider.get("movie_template")).replace("{tmdb_id}", "937249")
        if sample_tv != expected["sample_tv"]:
            issues.append(f"streaming.embed_providers[{key}] sample TV URL drifted: {sample_tv}")
        if sample_movie != expected["sample_movie"]:
            issues.append(f"streaming.embed_providers[{key}] sample movie URL drifted: {sample_movie}")

    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 1

    print(json.dumps({"streaming_config_validation": "passed", "buildable_provider_count": len(buildable_keys)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
