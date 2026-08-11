#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/qa_data_assets_report.py
# [PROJECT] my_TV_Movie
# [ROLE]    QA counts for data/data.json + asset folder file counts
# [VERSION] v1.0.0
# [UPDATED] 2026-01-21
#
# OUTPUTS
# - Console summary
# - logs/qa_data_assets_report_YYYYMMDD_HHMMSSZ.log.txt
# ==============================================================================

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
ASSETS_DIR = REPO_ROOT / "assets"
LOGS_DIR = REPO_ROOT / "logs"


# -----------------------------
# helpers
# -----------------------------
def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def is_nonempty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, tuple, dict)):
        return len(v) > 0
    return True


def get_dict(obj: Any, key: str) -> Dict[str, Any]:
    v = obj.get(key) if isinstance(obj, dict) else None
    return v if isinstance(v, dict) else {}


def count_present(objs: Iterable[Dict[str, Any]], field: str) -> int:
    c = 0
    for o in objs:
        if isinstance(o, dict) and field in o and is_nonempty(o.get(field)):
            c += 1
    return c


def count_links_present(objs: Iterable[Dict[str, Any]]) -> int:
    c = 0
    for o in objs:
        links = get_dict(o, "links")
        if links and any(is_nonempty(v) for v in links.values()):
            c += 1
    return c


def count_link_key(objs: Iterable[Dict[str, Any]], key: str) -> int:
    c = 0
    for o in objs:
        links = get_dict(o, "links")
        v = links.get(key)
        if is_nonempty(v):
            c += 1
    return c


def count_link_key_fuzzy(objs: Iterable[Dict[str, Any]], needle: str) -> int:
    """
    Counts if links has a key containing `needle` (case-insensitive) with non-empty value.
    Useful when key naming varies (e.g., "rottentomatoes", "rotten_tomatoes").
    """
    n = needle.strip().lower()
    if not n:
        return 0
    c = 0
    for o in objs:
        links = get_dict(o, "links")
        hit = False
        for k, v in links.items():
            if n in str(k).lower() and is_nonempty(v):
                hit = True
                break
        if hit:
            c += 1
    return c


def configured_streaming_keys() -> set[str]:
    config_path = REPO_ROOT / "web" / "config.json"
    keys = {"vidsrc", "videasy"}
    try:
        config = json.loads(config_path.read_text(encoding="utf-8", errors="replace"))
        providers = config.get("streaming", {}).get("embed_providers", [])
        iterable = providers if isinstance(providers, list) else []
        for provider in iterable:
            if isinstance(provider, dict) and provider.get("key"):
                keys.add(str(provider.get("key")))
    except Exception:
        pass
    return keys


def count_streaming_link_leaks(objs: Iterable[Dict[str, Any]], streaming_keys: set[str]) -> int:
    c = 0
    for o in objs:
        links = get_dict(o, "links")
        if any(key in streaming_keys and is_nonempty(value) for key, value in links.items()):
            c += 1
    return c


def safe_len(x: Any) -> int:
    if isinstance(x, list):
        return len(x)
    return 0


def iter_seasons(shows: List[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for s in shows:
        for se in (s.get("seasons") or []):
            if isinstance(se, dict):
                yield se


def iter_episodes(shows: List[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for se in iter_seasons(shows):
        for ep in (se.get("episodes") or []):
            if isinstance(ep, dict):
                yield ep


def count_asset_files(path: Path) -> Tuple[int, int]:
    """
    Returns (file_count, dir_count) under path (recursive, excludes .git-like hidden folders only by name).
    """
    if not path.exists():
        return (0, 0)
    files = 0
    dirs = 0
    for root, dirnames, filenames in os.walk(path):
        # keep walking, but skip obvious hidden/system dirs that aren't content
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        dirs += len(dirnames)
        files += len([f for f in filenames if not f.startswith(".")])
    return (files, dirs)


def write_lines(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", errors="replace")


# -----------------------------
# main
# -----------------------------
def main() -> int:
    if not DATA_JSON.exists():
        raise SystemExit(f"Missing: {DATA_JSON}")

    raw = DATA_JSON.read_text(encoding="utf-8", errors="replace")
    data = json.loads(raw)
    streaming_keys = configured_streaming_keys()

    shows = data.get("shows") or []
    movies = data.get("movies") or []

    if not isinstance(shows, list) or not isinstance(movies, list):
        raise SystemExit("data.json must contain top-level arrays: shows[], movies[]")

    # ---- movies ----
    movie_count = len(movies)
    movie_homepage = count_present(movies, "homepage")
    movie_poster_local = count_present(movies, "poster_local")
    movie_poster_path = count_present(movies, "poster_path")
    movie_backdrop_local = count_present(movies, "backdrop_local")
    movie_backdrop_path = count_present(movies, "backdrop_path")

    movie_links_any = count_links_present(movies)
    movie_tmdb_links = count_link_key(movies, "tmdb") + count_link_key_fuzzy(movies, "themoviedb")
    movie_rt_links = count_link_key_fuzzy(movies, "rotten")
    movie_streaming_link_leaks = count_streaming_link_leaks(movies, streaming_keys)

    # ---- shows ----
    show_count = len(shows)
    show_homepage = count_present(shows, "homepage")
    show_poster_local = count_present(shows, "poster_local")
    show_poster_path = count_present(shows, "poster_path")
    show_backdrop_local = count_present(shows, "backdrop_local")
    show_backdrop_path = count_present(shows, "backdrop_path")

    show_links_any = count_links_present(shows)
    show_tmdb_links = count_link_key(shows, "tmdb") + count_link_key_fuzzy(shows, "themoviedb")
    show_rt_links = count_link_key_fuzzy(shows, "rotten")

    shows_with_seasons = sum(1 for s in shows if safe_len(s.get("seasons")) > 0)
    total_seasons = sum(safe_len(s.get("seasons")) for s in shows)

    # episodes
    episodes_total = 0
    shows_with_episodes = 0
    for s in shows:
        eps = 0
        for se in (s.get("seasons") or []):
            if isinstance(se, dict):
                eps += safe_len(se.get("episodes"))
        if eps > 0:
            shows_with_episodes += 1
        episodes_total += eps

    # ---- seasons ----
    seasons = list(iter_seasons(shows))
    seasons_with_episodes = sum(1 for se in seasons if safe_len(se.get("episodes")) > 0)

    season_poster_local = count_present(seasons, "poster_local")
    season_poster_path = count_present(seasons, "poster_path")
    season_backdrop_local = count_present(seasons, "backdrop_local")  # may not exist in schema
    season_backdrop_path = count_present(seasons, "backdrop_path")    # may not exist in schema
    season_logo_path = count_present(seasons, "logo_path")            # likely not in schema

    # ---- episodes ----
    episodes = list(iter_episodes(shows))

    ep_still_local = count_present(episodes, "still_local")
    ep_still_path = count_present(episodes, "still_path")
    ep_links_any = count_links_present(episodes)
    ep_tmdb_links = count_link_key(episodes, "tmdb") + count_link_key_fuzzy(episodes, "themoviedb")
    ep_streaming_link_leaks = count_streaming_link_leaks(episodes, streaming_keys)

    # ---- assets folder counts ----
    assets_targets = [
        ASSETS_DIR,
        ASSETS_DIR / "backdrops",
        ASSETS_DIR / "backdrops" / "movies",
        ASSETS_DIR / "backdrops" / "shows",
        ASSETS_DIR / "posters",
        ASSETS_DIR / "posters" / "movies",
        ASSETS_DIR / "posters" / "shows",
        ASSETS_DIR / "posters" / "seasons",
        ASSETS_DIR / "stills",
        ASSETS_DIR / "stills" / "episodes",
        ASSETS_DIR / "logos",
        ASSETS_DIR / "logos" / "services",
        ASSETS_DIR / "icons",
        ASSETS_DIR / "HR",
    ]

    # ---- report ----
    lines: List[str] = []
    lines.append(f"QA DATA+ASSETS REPORT | utc={utc_stamp()}")
    lines.append(f"repo_root={REPO_ROOT}")
    lines.append(f"data_json={DATA_JSON}")
    lines.append("")

    lines.append("MOVIES")
    lines.append(f"  movies_total={movie_count}")
    lines.append(f"  homepage_present={movie_homepage}")
    lines.append(f"  poster_local_present={movie_poster_local}")
    lines.append(f"  poster_path_present={movie_poster_path}")
    lines.append(f"  backdrop_local_present={movie_backdrop_local}")
    lines.append(f"  backdrop_path_present={movie_backdrop_path}")
    lines.append(f"  links_any_present={movie_links_any}")
    lines.append(f"  links_tmdb_present={movie_tmdb_links}")
    lines.append(f"  links_rotten_present={movie_rt_links}")
    lines.append(f"  streaming_link_leaks={movie_streaming_link_leaks}")
    lines.append("")

    lines.append("TV SHOWS")
    lines.append(f"  shows_total={show_count}")
    lines.append(f"  shows_with_seasons={shows_with_seasons}")
    lines.append(f"  shows_with_episodes={shows_with_episodes}")
    lines.append(f"  seasons_total={total_seasons}")
    lines.append(f"  episodes_total={episodes_total}")
    lines.append(f"  homepage_present={show_homepage}")
    lines.append(f"  poster_local_present={show_poster_local}")
    lines.append(f"  poster_path_present={show_poster_path}")
    lines.append(f"  backdrop_local_present={show_backdrop_local}")
    lines.append(f"  backdrop_path_present={show_backdrop_path}")
    lines.append(f"  links_any_present={show_links_any}")
    lines.append(f"  links_tmdb_present={show_tmdb_links}")
    lines.append(f"  links_rotten_present={show_rt_links}")
    lines.append("")

    lines.append("SEASONS")
    lines.append(f"  seasons_total={len(seasons)}")
    lines.append(f"  seasons_with_episodes={seasons_with_episodes}")
    lines.append(f"  poster_local_present={season_poster_local}")
    lines.append(f"  poster_path_present={season_poster_path}")
    lines.append(f"  backdrop_local_present={season_backdrop_local}")
    lines.append(f"  backdrop_path_present={season_backdrop_path}")
    lines.append(f"  logo_path_present={season_logo_path}")
    lines.append("")

    lines.append("EPISODES")
    lines.append(f"  episodes_total={len(episodes)}")
    lines.append(f"  still_local_present={ep_still_local}")
    lines.append(f"  still_path_present={ep_still_path}")
    lines.append(f"  links_any_present={ep_links_any}")
    lines.append(f"  links_tmdb_present={ep_tmdb_links}")
    lines.append(f"  streaming_link_leaks={ep_streaming_link_leaks}")
    lines.append("")

    lines.append("ASSETS FILE COUNTS (recursive)")
    for p in assets_targets:
        fcnt, dcnt = count_asset_files(p)
        rel = str(p.relative_to(REPO_ROOT)) if p.exists() else str(p.relative_to(REPO_ROOT))
        lines.append(f"  {rel} | files={fcnt} dirs={dcnt}")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"qa_data_assets_report_{utc_stamp()}.log.txt"
    write_lines(log_path, lines)

    # console (short)
    print(f"movies_total={movie_count} shows_total={show_count} seasons_total={len(seasons)} episodes_total={len(episodes)}")
    print(f"missing_movie_links={(movie_count - movie_links_any)} missing_show_links={(show_count - show_links_any)}")
    print(f"logfile={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
