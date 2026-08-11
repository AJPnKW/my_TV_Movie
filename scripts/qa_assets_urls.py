#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_assets_urls.py
# [PROJECT] my_TV_Movie
# [ROLE]    QA: verify local assets exist + generated streaming URLs are absent from data/data.json
# [VERSION] v1.0.0
# [UPDATED] 2026-01-16
# [BUILD]   14.01.16
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
LOG_DIR = REPO_ROOT / "logs"


def _fs_exists(site_path: str) -> bool:
    fs = REPO_ROOT / site_path.lstrip("/").replace("/", os.sep)
    return fs.is_file()


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = LOG_DIR / f"qa_assets_urls_{ts}.log.txt"

    d = json.loads(DATA_JSON.read_text(encoding="utf-8", errors="replace"))

    missing_assets: List[Tuple[str, Any, str, str]] = []
    streaming_url_leaks: List[Tuple[str, Any, str, str]] = []
    streaming_keys = set()
    config = json.loads((REPO_ROOT / "web" / "config.json").read_text(encoding="utf-8", errors="replace"))
    for provider in config.get("streaming", {}).get("embed_providers", []) or []:
        if isinstance(provider, dict) and provider.get("key"):
            streaming_keys.add(str(provider.get("key")))
    streaming_keys.update({"vidsrc", "videasy"})

    def chk_asset(kind: str, tmdb_id: Any, title: str, site_path: Any) -> None:
        if not isinstance(site_path, str) or not site_path:
            return
        if site_path.startswith("/assets/") or site_path.startswith("/image/"):
            if not _fs_exists(site_path):
                missing_assets.append((kind, tmdb_id, title, site_path))

    def chk_urls(kind: str, tmdb_id: Any, title: str, links: Any) -> None:
        if not isinstance(links, dict) or not links:
            return
        for key in streaming_keys:
            value = links.get(key)
            if isinstance(value, str) and value.strip():
                streaming_url_leaks.append((kind, tmdb_id, title, key))

    for s in d.get("shows", []) or []:
        sid = s.get("tmdb_id")
        title = s.get("title") or s.get("name") or ""
        chk_asset("show_poster", sid, title, s.get("poster_local"))
        chk_asset("show_backdrop", sid, title, s.get("backdrop_local"))

        for se in s.get("seasons", []) or []:
            chk_asset("season_poster", sid, title, se.get("poster_local"))
            for ep in se.get("episodes", []) or []:
                chk_asset("episode_still", sid, title, ep.get("still_local"))
                chk_urls("episode", sid, title, ep.get("links"))

    for m in d.get("movies", []) or []:
        mid = m.get("tmdb_id")
        title = m.get("title") or ""
        chk_asset("movie_poster", mid, title, m.get("poster_local"))
        chk_asset("movie_backdrop", mid, title, m.get("backdrop_local"))
        chk_urls("movie", mid, title, m.get("links"))

    with out.open("w", encoding="utf-8", errors="replace", newline="\n") as f:
        f.write("QA ASSETS + URLS\n")
        f.write(f"shows={len(d.get('shows', []) or [])} movies={len(d.get('movies', []) or [])}\n")
        f.write(f"missing_assets={len(missing_assets)}\n")
        for r in missing_assets[:300]:
            f.write("MISSING_ASSET | " + " | ".join(map(str, r)) + "\n")
        f.write(f"streaming_url_leaks={len(streaming_url_leaks)}\n")
        for r in streaming_url_leaks[:300]:
            f.write("STREAMING_URL_LEAK | " + " | ".join(map(str, r)) + "\n")

    print("missing_assets=", len(missing_assets))
    print("streaming_url_leaks=", len(streaming_url_leaks))
    print("logfile=", str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
