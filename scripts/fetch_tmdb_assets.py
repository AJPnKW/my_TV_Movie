#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_tmdb_assets.py
# [PROJECT] my_TV_Movie
# [ROLE]    Augment Trakt-primary data.json with TMDB assets + metadata
# [VERSION] v1.0.0
# [UPDATED] 2026-02-01
#
# Requires:
#   API_TMDB_KEY or API_TMDB_TOKEN
#   web/config.json (image_cache + streaming)
#
# Input:
#   data/data.json (Trakt-primary)
# Output:
#   data/data.json (augmented with TMDB fields)
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore
except Exception as ex:
    raise SystemExit("Missing dependency: requests. Run: python -m pip install -r requirements.txt") from ex

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
CONFIG_JSON = REPO_ROOT / "web" / "config.json"

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def _utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_jsonc(s: str) -> str:
    s = re.sub(r"/\\*.*?\\*/", "", s, flags=re.S)
    lines = []
    for line in s.splitlines():
        if re.match(r"^\\s*//", line):
            continue
        lines.append(re.sub(r"\\s+//.*$", "", line))
    return "\\n".join(lines)


def load_jsonc(path: Path) -> Dict[str, Any]:
    raw = read_text(path)
    return json.loads(strip_jsonc(raw))


def tmdb_headers(token: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def tmdb_get(path: str, key: Optional[str], token: Optional[str], params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TMDB_API_BASE}{path}"
    p = params or {}
    if key and not token:
        p["api_key"] = key
    r = requests.get(url, headers=tmdb_headers(token), params=p, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"TMDB {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()


def tmdb_image_url(size: str, path: Optional[str]) -> str:
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}{path}"


def compute_local_path(cfg: Dict[str, Any], folder_key: str, tmdb_path: Optional[str]) -> str:
    if not tmdb_path:
        return ""
    base_dir = (cfg.get("image_cache") or {}).get("base_dir") or ""
    folders = (cfg.get("image_cache") or {}).get("folders") or {}
    folder = folders.get(folder_key) or ""
    if not base_dir or not folder:
        return ""
    filename = Path(tmdb_path).name
    return f"{base_dir}/{folder}/{filename}"


def main() -> int:
    tmdb_key = (os.getenv("API_TMDB_KEY") or "").strip()
    tmdb_token = (os.getenv("API_TMDB_TOKEN") or "").strip()
    if not tmdb_key and not tmdb_token:
        print("ERROR: Missing TMDB creds. Set API_TMDB_KEY or API_TMDB_TOKEN.")
        return 2

    if not DATA_JSON.exists():
        print("ERROR: Missing data/data.json (run fetch_trakt_primary.py first).")
        return 3

    cfg = load_jsonc(CONFIG_JSON)
    data = json.loads(read_text(DATA_JSON))

    shows = data.get("shows") or []
    movies = data.get("movies") or []
    errors = data.setdefault("errors", [])

    # Movies
    for m in movies:
        tmdb_id = m.get("tmdb_id")
        if not isinstance(tmdb_id, int):
            continue
        try:
            details = tmdb_get(f"/movie/{tmdb_id}", tmdb_key, tmdb_token, params={"language": "en-US"})
            ext = tmdb_get(f"/movie/{tmdb_id}/external_ids", tmdb_key, tmdb_token)
            providers = tmdb_get(f"/movie/{tmdb_id}/watch/providers", tmdb_key, tmdb_token)

            m.update(
                {
                    "id": tmdb_id,
                    "imdb_id": ext.get("imdb_id") or m.get("imdb_id"),
                    "overview": details.get("overview") or m.get("overview"),
                    "status": details.get("status"),
                    "popularity": details.get("popularity"),
                    "vote_average": details.get("vote_average"),
                    "vote_count": details.get("vote_count"),
                    "runtime": details.get("runtime") or m.get("runtime"),
                    "homepage": details.get("homepage"),
                    "genres": details.get("genres") or m.get("genres") or [],
                    "poster_path": details.get("poster_path"),
                    "backdrop_path": details.get("backdrop_path"),
                    "poster_local": compute_local_path(cfg, "posters_movies", details.get("poster_path")),
                    "backdrop_local": compute_local_path(cfg, "backdrops", details.get("backdrop_path")),
                    "watch_providers": providers,
                }
            )
        except Exception as ex:
            errors.append({"type": "tmdb_movie", "tmdb_id": tmdb_id, "message": str(ex)[:200], "utc": _utc()})

    # Shows
    for s in shows:
        tmdb_id = s.get("tmdb_id")
        if not isinstance(tmdb_id, int):
            continue
        try:
            details = tmdb_get(f"/tv/{tmdb_id}", tmdb_key, tmdb_token, params={"language": "en-US"})
            ext = tmdb_get(f"/tv/{tmdb_id}/external_ids", tmdb_key, tmdb_token)
            providers = tmdb_get(f"/tv/{tmdb_id}/watch/providers", tmdb_key, tmdb_token)
            images = tmdb_get(f"/tv/{tmdb_id}/images", tmdb_key, tmdb_token, params={"include_image_language": "en,null"})
            logos = (images or {}).get("logos") or []
            logo_path = logos[0].get("file_path") if logos else None

            s.update(
                {
                    "id": tmdb_id,
                    "tvdb_id": ext.get("tvdb_id") or s.get("tvdb_id"),
                    "imdb_id": ext.get("imdb_id") or s.get("imdb_id"),
                    "overview": details.get("overview") or s.get("overview"),
                    "status": details.get("status"),
                    "popularity": details.get("popularity"),
                    "vote_average": details.get("vote_average"),
                    "vote_count": details.get("vote_count"),
                    "homepage": details.get("homepage"),
                    "genres": details.get("genres") or s.get("genres") or [],
                    "origin_country": details.get("origin_country") or [],
                    "in_production": details.get("in_production"),
                    "number_of_seasons": details.get("number_of_seasons"),
                    "number_of_episodes": details.get("number_of_episodes"),
                    "episode_run_time": details.get("episode_run_time") or [],
                    "last_air_date": details.get("last_air_date"),
                    "next_episode_to_air": details.get("next_episode_to_air"),
                    "last_episode_to_air": details.get("last_episode_to_air"),
                    "type": details.get("type"),
                    "networks": details.get("networks") or [],
                    "created_by": details.get("created_by") or [],
                    "poster_path": details.get("poster_path"),
                    "backdrop_path": details.get("backdrop_path"),
                    "poster_local": compute_local_path(cfg, "posters_shows", details.get("poster_path")),
                    "backdrop_local": compute_local_path(cfg, "backdrops", details.get("backdrop_path")),
                    "watch_providers": providers,
                    "show_logo_tmdb": tmdb_image_url("w154", logo_path) if logo_path else "",
                }
            )

            # Season / episode stills
            seasons = s.get("seasons") or []
            for season in seasons:
                season_num = season.get("season_number")
                if not isinstance(season_num, int):
                    continue
                try:
                    season_details = tmdb_get(f"/tv/{tmdb_id}/season/{season_num}", tmdb_key, tmdb_token, params={"language": "en-US"})
                    season["poster_tmdb"] = season_details.get("poster_path")
                    season["poster_local"] = compute_local_path(cfg, "posters_seasons", season_details.get("poster_path"))
                    eps_by_num = {int(e.get("episode_number")): e for e in (season_details.get("episodes") or []) if isinstance(e.get("episode_number"), int)}
                    for ep in season.get("episodes") or []:
                        ep_num = ep.get("episode_number")
                        if not isinstance(ep_num, int) or ep_num not in eps_by_num:
                            continue
                        tmdb_ep = eps_by_num[ep_num]
                        still_path = tmdb_ep.get("still_path")
                        ep["still_tmdb"] = still_path
                        ep["still_local"] = compute_local_path(cfg, "stills_episodes", still_path)
                except Exception:
                    continue
        except Exception as ex:
            errors.append({"type": "tmdb_show", "tmdb_id": tmdb_id, "message": str(ex)[:200], "utc": _utc()})

    data["meta"]["tmdb_assets_utc"] = _utc()
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[fetch_tmdb_assets] updated {DATA_JSON} (shows={len(shows)} movies={len(movies)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
