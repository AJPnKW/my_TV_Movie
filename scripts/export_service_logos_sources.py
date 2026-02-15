#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/export_service_logos_sources.py
# [PROJECT] my_TV_Movie
# [ROLE]    Export canonical service logo sources from web/config.json
# [VERSION] v1.0.0
# [UPDATED] 2026-02-15_00-00-00
# [BUILD]   14.01.08
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_JSON = REPO_ROOT / "web" / "config.json"
OUT_JSON = REPO_ROOT / "data" / "service_logos_sources.json"
LOG_DIR = REPO_ROOT / "logs"

URL_RE = re.compile(r"^https?://", re.IGNORECASE)
SAFE_RE = re.compile(r"[^a-z0-9._-]+")


def _ts_file() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"export_service_logos_sources_{_ts_file()}.log.txt"


def _write_log(fp, msg: str) -> None:
    line = f"{_now()} | {msg}"
    fp.write(line + "\n")
    fp.flush()
    print(line)


def _safe_slug(value: str) -> str:
    s = (value or "").strip().lower()
    s = SAFE_RE.sub("_", s).strip("._-")
    return s


def _basename_from_url(url: str) -> str:
    u = (url or "").strip().split("?", 1)[0]
    name = Path(u).name
    if not name:
        return ""
    return SAFE_RE.sub("_", name).strip("._-")


def _derive_filename(service_slug: str, url: str, explicit: Optional[str]) -> str:
    if explicit:
        out = SAFE_RE.sub("_", explicit.strip()).strip("._-")
        if out:
            return out
    from_url = _basename_from_url(url)
    if from_url:
        return from_url
    return f"{service_slug}.png"


def _to_tmdb_logo_url(base: str, logo_path: str, size: str = "w45") -> str:
    b = (base or "").rstrip("/")
    p = (logo_path or "").strip()
    if not b or not p.startswith("/"):
        return ""
    return f"{b}/{size}{p}"


def _extract_row(
    slug_hint: str,
    raw: Dict[str, Any],
    tmdb_image_base: str,
) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    slug_raw = str(raw.get("service_slug") or raw.get("slug") or raw.get("service") or slug_hint or "").strip()
    service_slug = _safe_slug(slug_raw)
    if not service_slug:
        return None, "missing service_slug"

    filename_explicit = raw.get("filename")
    if filename_explicit is not None:
        filename_explicit = str(filename_explicit).strip()

    url_candidates = [
        raw.get("logo_url"),
        raw.get("url"),
        raw.get("logo"),
    ]
    logo_path = str(raw.get("logo_path") or "").strip()
    if logo_path:
        url_candidates.append(_to_tmdb_logo_url(tmdb_image_base, logo_path))

    url = ""
    for c in url_candidates:
        s = str(c or "").strip()
        if URL_RE.match(s):
            url = s
            break

    if not url:
        return None, f"service '{service_slug}' missing logo URL"

    filename = _derive_filename(service_slug, url, filename_explicit)
    return {"service_slug": service_slug, "url": url, "filename": filename}, None


def _extract_rows_from_section(
    section_name: str,
    section: Any,
    tmdb_image_base: str,
) -> Tuple[List[Dict[str, str]], List[str]]:
    rows: List[Dict[str, str]] = []
    errors: List[str] = []

    if isinstance(section, list):
        for idx, item in enumerate(section):
            if not isinstance(item, dict):
                errors.append(f"{section_name}[{idx}] must be an object")
                continue
            row, err = _extract_row("", item, tmdb_image_base)
            if err:
                errors.append(f"{section_name}[{idx}] {err}")
                continue
            rows.append(row)
        return rows, errors

    if isinstance(section, dict):
        for key in sorted(section.keys()):
            item = section[key]
            if isinstance(item, dict):
                row, err = _extract_row(str(key), item, tmdb_image_base)
                if err:
                    errors.append(f"{section_name}.{key} {err}")
                    continue
                rows.append(row)
        return rows, errors

    errors.append(f"{section_name} must be an object or array")
    return rows, errors


def _load_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return data


def _build_rows(cfg: Dict[str, Any]) -> Tuple[List[Dict[str, str]], List[str]]:
    tmdb_image_base = str(((cfg.get("image_cache") or {}).get("tmdb_image_base") or "https://image.tmdb.org/t/p")).strip()
    sections = ["service_logos", "streaming_services", "streaming"]

    rows: List[Dict[str, str]] = []
    errors: List[str] = []
    for name in sections:
        if name not in cfg:
            continue
        section_rows, section_errors = _extract_rows_from_section(name, cfg[name], tmdb_image_base)
        rows.extend(section_rows)
        errors.extend(section_errors)

    # Deterministic de-duplication by (service_slug, url, filename)
    uniq = {}
    for r in rows:
        k = (r["service_slug"], r["url"], r["filename"])
        if k not in uniq:
            uniq[k] = r

    ordered = sorted(uniq.values(), key=lambda x: (x["service_slug"], x["url"]))
    return ordered, errors


def main() -> int:
    logp = _log_path()
    with logp.open("w", encoding="utf-8", newline="\n") as log_fp:
        _write_log(log_fp, "[export_service_logos_sources] START")
        _write_log(log_fp, f"config={CONFIG_JSON.as_posix()}")
        _write_log(log_fp, f"output={OUT_JSON.as_posix()}")

        if not CONFIG_JSON.exists():
            _write_log(log_fp, "FAIL missing web/config.json")
            return 2

        try:
            cfg = _load_json(CONFIG_JSON)
        except Exception as ex:
            _write_log(log_fp, f"FAIL parse config :: {ex}")
            return 3

        rows, errors = _build_rows(cfg)
        if errors:
            for e in errors:
                _write_log(log_fp, f"FAIL {e}")
            return 4

        if not rows:
            _write_log(log_fp, "FAIL no service logo sources found in config sections: service_logos, streaming_services, streaming")
            return 5

        for idx, row in enumerate(rows):
            slug = str(row.get("service_slug") or "").strip()
            url = str(row.get("url") or "").strip()
            if not slug or not url:
                _write_log(log_fp, f"FAIL row[{idx}] missing required fields service_slug/url")
                return 6

        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
        OUT_JSON.write_text(payload, encoding="utf-8")

        # Required validation: ensure written output re-parses as JSON.
        try:
            json.loads(OUT_JSON.read_text(encoding="utf-8", errors="replace"))
        except Exception as ex:
            _write_log(log_fp, f"FAIL output json validation :: {ex}")
            return 7

        _write_log(log_fp, f"OK exported_rows={len(rows)}")
        _write_log(log_fp, f"[export_service_logos_sources] END log={logp.as_posix()}")
        print(f"export_service_logos_sources: rows={len(rows)} output={OUT_JSON.as_posix()}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
