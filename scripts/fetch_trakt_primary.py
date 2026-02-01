#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_trakt_primary.py
# [PROJECT] my_TV_Movie
# [ROLE]    Build primary dataset from Trakt (single source of truth)
# [VERSION] v1.0.0
# [UPDATED] 2026-02-01
#
# Requires OAuth tokens:
#   API_TRAKT_ID
#   API_TRAKT_SECRET (or API_TRAKT_KEY)
#   access/refresh tokens (env or data/trakt_tokens_latest.json)
#
# Output:
#   data/data.json (Trakt-primary)
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception as ex:
    raise SystemExit("Missing dependency: requests. Run: python -m pip install -r requirements.txt") from ex

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"
TOK_OUT = DATA_DIR / "trakt_tokens_latest.json"
TOK_FALLBACK = DATA_DIR / "trakt.json"
LOGS_DIR = REPO_ROOT / "logs"

TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_API_VERSION = "2"
DEFAULT_TIMEOUT = 45


def _utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def blank(v: Any) -> bool:
    return v is None or str(v).strip() == ""


def load_tokens_file() -> Dict[str, Any]:
    for path in (TOK_OUT, TOK_FALLBACK):
        if not path.is_file():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
    return {}


def trakt_headers(client_id: str, access_token: Optional[str]) -> Dict[str, str]:
    h = {"trakt-api-version": TRAKT_API_VERSION, "trakt-api-key": client_id}
    if access_token and not blank(access_token):
        h["Authorization"] = f"Bearer {access_token}"
    return h


def trakt_get(path: str, client_id: str, access_token: Optional[str], params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TRAKT_API_BASE}{path}"
    r = requests.get(url, headers=trakt_headers(client_id, access_token), params=params or {}, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"TRAKT GET {path} failed: {r.status_code} {r.text[:300]}")
    return r.json()


def to_genres_list(names: Any) -> List[Dict[str, Any]]:
    if not isinstance(names, list):
        return []
    return [{"name": n} for n in names if isinstance(n, str) and n.strip()]


def norm_show(obj: Dict[str, Any]) -> Dict[str, Any]:
    ids = obj.get("ids") or {}
    return {
        "tmdb_id": ids.get("tmdb"),
        "trakt_id": ids.get("trakt"),
        "tvdb_id": ids.get("tvdb"),
        "imdb_id": ids.get("imdb"),
        "title": obj.get("title") or obj.get("name"),
        "name": obj.get("title") or obj.get("name"),
        "overview": obj.get("overview"),
        "status": obj.get("status"),
        "first_air_date": obj.get("first_aired"),
        "runtime": obj.get("runtime"),
        "network": obj.get("network"),
        "country": obj.get("country"),
        "language": obj.get("language"),
        "genres": to_genres_list(obj.get("genres")),
        "number_of_episodes": obj.get("aired_episodes"),
        "seasons": [],
        "links": {"trakt": obj.get("trakt_url") or ""},
    }


def norm_movie(obj: Dict[str, Any]) -> Dict[str, Any]:
    ids = obj.get("ids") or {}
    return {
        "tmdb_id": ids.get("tmdb"),
        "trakt_id": ids.get("trakt"),
        "imdb_id": ids.get("imdb"),
        "title": obj.get("title"),
        "overview": obj.get("overview"),
        "release_date": obj.get("released"),
        "runtime": obj.get("runtime"),
        "language": obj.get("language"),
        "genres": to_genres_list(obj.get("genres")),
        "links": {"trakt": obj.get("trakt_url") or ""},
    }


def pull_show_seasons(show_id: str, client_id: str, access_token: str) -> List[Dict[str, Any]]:
    seasons = trakt_get(f"/shows/{show_id}/seasons", client_id, access_token, params={"extended": "episodes"})
    out: List[Dict[str, Any]] = []
    for s in seasons or []:
        if not isinstance(s, dict):
            continue
        season_number = s.get("number")
        if season_number is None:
            continue
        season_obj = {
            "season_number": season_number,
            "title": s.get("title"),
            "episode_count": s.get("episode_count"),
            "first_aired": s.get("first_aired"),
            "episodes": [],
        }
        for ep in s.get("episodes") or []:
            if not isinstance(ep, dict):
                continue
            ep_ids = ep.get("ids") or {}
            season_obj["episodes"].append(
                {
                    "episode_number": ep.get("number"),
                    "season_number": season_number,
                    "title": ep.get("title"),
                    "first_aired": ep.get("first_aired"),
                    "trakt_id": ep_ids.get("trakt"),
                    "tmdb_id": ep_ids.get("tmdb"),
                    "tvdb_id": ep_ids.get("tvdb"),
                    "imdb_id": ep_ids.get("imdb"),
                }
            )
        out.append(season_obj)
    return out


def main() -> int:
    client_id = os.getenv("API_TRAKT_ID")
    client_secret = os.getenv("API_TRAKT_SECRET") or os.getenv("API_TRAKT_KEY")
    access_token = os.getenv("API_TRAKT_ACCESS_TOKEN")
    refresh_token = os.getenv("API_TRAKT_REFRESH_TOKEN")

    if blank(client_id) or blank(client_secret):
        print("ERROR: Missing API_TRAKT_ID or API_TRAKT_SECRET.", file=sys.stderr)
        return 2

    if blank(access_token):
        tok = load_tokens_file()
        access_token = tok.get("access_token") or access_token
        refresh_token = tok.get("refresh_token") or refresh_token

    if blank(access_token):
        print("ERROR: Missing Trakt access token. Run scripts/trakt_device_auth.py first.", file=sys.stderr)
        return 3

    data: Dict[str, Any] = {
        "meta": {
            "generated_utc": _utc(),
            "builder": {"script": "scripts/fetch_trakt_primary.py", "version": "v1.0.0"},
            "source": "trakt_primary",
        },
        "shows": [],
        "movies": [],
        "trakt": {},
        "errors": [],
    }

    errors = data["errors"]

    def safe_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            return trakt_get(path, client_id, access_token, params=params)
        except Exception as ex:
            errors.append({"type": "trakt_fetch", "path": path, "message": str(ex)[:300], "utc": _utc()})
            return []

    # Core user datasets
    lists = safe_get("/users/me/lists")
    list_items: Dict[str, Any] = {}
    for lst in lists or []:
        list_id = lst.get("ids", {}).get("trakt")
        if list_id is None:
            continue
        list_items[str(list_id)] = safe_get(f"/users/me/lists/{list_id}/items", params={"extended": "full"})

    collection_movies = safe_get("/sync/collection/movies", params={"extended": "full"})
    collection_shows = safe_get("/sync/collection/shows", params={"extended": "full"})
    watchlist_movies = safe_get("/sync/watchlist/movies", params={"extended": "full"})
    watchlist_shows = safe_get("/sync/watchlist/shows", params={"extended": "full"})
    watched_movies = safe_get("/sync/watched/movies", params={"extended": "full"})
    watched_shows = safe_get("/sync/watched/shows", params={"extended": "full"})
    playback = safe_get("/sync/playback")
    activity = safe_get("/sync/last_activities")

    # Discovery / trends (public, but OK with auth headers)
    trending_movies = safe_get("/movies/trending", params={"extended": "full"})
    trending_shows = safe_get("/shows/trending", params={"extended": "full"})
    popular_movies = safe_get("/movies/popular", params={"extended": "full"})
    popular_shows = safe_get("/shows/popular", params={"extended": "full"})
    anticipated_movies = safe_get("/movies/anticipated", params={"extended": "full"})
    anticipated_shows = safe_get("/shows/anticipated", params={"extended": "full"})
    recommended_movies = safe_get("/movies/recommended", params={"extended": "full"})
    recommended_shows = safe_get("/shows/recommended", params={"extended": "full"})

    # Calendar (next 7 days)
    today = _dt.date.today().strftime("%Y-%m-%d")
    calendar = safe_get(f"/calendars/my/shows/{today}/7", params={"extended": "full"})

    # Supporting refs
    genres_movies = safe_get("/genres/movies")
    genres_shows = safe_get("/genres/shows")

    data["trakt"] = {
        "lists": lists,
        "list_items": list_items,
        "collection": {"movies": collection_movies, "shows": collection_shows},
        "watchlist": {"movies": watchlist_movies, "shows": watchlist_shows},
        "watched": {"movies": watched_movies, "shows": watched_shows},
        "playback": playback,
        "trending": {"movies": trending_movies, "shows": trending_shows},
        "popular": {"movies": popular_movies, "shows": popular_shows},
        "anticipated": {"movies": anticipated_movies, "shows": anticipated_shows},
        "recommended": {"movies": recommended_movies, "shows": recommended_shows},
        "calendar": calendar,
        "activity": activity,
        "supporting": {"genres": {"movies": genres_movies, "shows": genres_shows}},
    }

    # Build canonical shows/movies lists (union from collection/watchlist/lists/watched)
    show_map: Dict[int, Dict[str, Any]] = {}
    movie_map: Dict[int, Dict[str, Any]] = {}

    def add_show(obj: Dict[str, Any]) -> None:
        ids = obj.get("ids") or {}
        tmdb_id = ids.get("tmdb")
        if not isinstance(tmdb_id, int):
            return
        if tmdb_id not in show_map:
            show_map[tmdb_id] = norm_show(obj)

    def add_movie(obj: Dict[str, Any]) -> None:
        ids = obj.get("ids") or {}
        tmdb_id = ids.get("tmdb")
        if not isinstance(tmdb_id, int):
            return
        if tmdb_id not in movie_map:
            movie_map[tmdb_id] = norm_movie(obj)

    for row in collection_shows or []:
        show = row.get("show") or {}
        add_show(show)
    for row in watchlist_shows or []:
        show = row.get("show") or {}
        add_show(show)
    for row in watched_shows or []:
        show = row.get("show") or {}
        add_show(show)
    for lst_items in list_items.values():
        for row in lst_items or []:
            if row.get("type") == "show":
                add_show(row.get("show") or {})

    for row in collection_movies or []:
        movie = row.get("movie") or {}
        add_movie(movie)
    for row in watchlist_movies or []:
        movie = row.get("movie") or {}
        add_movie(movie)
    for row in watched_movies or []:
        movie = row.get("movie") or {}
        add_movie(movie)
    for lst_items in list_items.values():
        for row in lst_items or []:
            if row.get("type") == "movie":
                add_movie(row.get("movie") or {})

    # Enrich shows with seasons/episodes from Trakt
    for show in list(show_map.values()):
        trakt_id = show.get("trakt_id")
        if not trakt_id:
            continue
        try:
            show["seasons"] = pull_show_seasons(str(trakt_id), client_id, access_token)
        except Exception as ex:
            errors.append({"type": "trakt_seasons", "message": str(ex)[:300], "trakt_id": trakt_id, "utc": _utc()})

    data["shows"] = list(show_map.values())
    data["movies"] = list(movie_map.values())

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[fetch_trakt_primary] wrote {DATA_JSON} (shows={len(data['shows'])} movies={len(data['movies'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
