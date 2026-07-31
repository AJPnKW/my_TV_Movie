#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_trakt_primary.py
# [PROJECT] my_TV_Movie
# [ROLE]    Build catalog from inputs.json and Trakt metadata + user state
# [VERSION] v1.2.0
# [UPDATED] 2026-02-02
#
# Inputs:
#   data/inputs.json (catalog scope with tmdb_id + season_spec)
#
# Requires OAuth tokens:
#   API_TRAKT_ID
#   access token (env or data/trakt.json)
#
# Output:
#   data/data.json (Trakt metadata + user state; TMDB only used later for assets)
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
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from trakt_http import build_headers, header_names  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
INPUTS_JSON = DATA_DIR / "inputs.json"
DATA_JSON = DATA_DIR / "data.json"
TOK_FILE = DATA_DIR / "trakt.json"
CONFIG_JSON = REPO_ROOT / "web" / "config.json"

TRAKT_API_BASE = "https://api.trakt.tv"
DEFAULT_TIMEOUT = 45


def _utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def blank(v: Any) -> bool:
    return v is None or str(v).strip() == ""


def to_int(val: Any) -> Optional[int]:
    try:
        s = str(val).strip()
        if not s:
            return None
        return int(s)
    except Exception:
        return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_jsonc(s: str) -> str:
    lines = []
    for line in s.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        out = []
        in_str = False
        esc = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                out.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == "\"":
                    in_str = False
                i += 1
                continue
            if ch == "\"":
                in_str = True
                out.append(ch)
                i += 1
                continue
            if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            out.append(ch)
            i += 1
        lines.append("".join(out).rstrip())
    cleaned = "\n".join(lines)
    if not cleaned.lstrip().startswith("{"):
        brace = cleaned.find("{")
        if brace != -1:
            cleaned = cleaned[brace:]
    return cleaned


def load_jsonc(path: Path) -> Dict[str, Any]:
    return json.loads(strip_jsonc(read_text(path)))


def load_tokens_file() -> Dict[str, Any]:
    if not TOK_FILE.is_file():
        return {}
    try:
        return json.loads(TOK_FILE.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def load_inputs() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not INPUTS_JSON.is_file():
        raise FileNotFoundError(f"Missing required file: {INPUTS_JSON}")
    js = json.loads(INPUTS_JSON.read_text(encoding="utf-8", errors="replace"))
    tv = js.get("tv") or js.get("shows") or js.get("series") or []
    mv = js.get("movies") or js.get("films") or []
    if not isinstance(tv, list) or not isinstance(mv, list):
        raise ValueError("inputs.json must contain arrays: { tv: [...], movies: [...] }")
    return tv, mv


def trakt_get(
    path: str,
    client_id: str,
    access_token: Optional[str],
    params: Optional[Dict[str, Any]] = None,
    include_auth: bool = True,
) -> Any:
    url = f"{TRAKT_API_BASE}{path}"
    headers = build_headers(client_id, access_token, include_auth=include_auth)
    r = requests.get(url, headers=headers, params=params or {}, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(
            f"TRAKT GET {path} failed: {r.status_code} headers=[{header_names(headers)}] body={r.text[:300]}"
        )
    return r.json()


def trakt_get_public(path: str, client_id: str, params: Optional[Dict[str, Any]] = None) -> Any:
    return trakt_get(path, client_id, access_token=None, params=params, include_auth=False)


def parse_season_rule(spec: str) -> Tuple[str, Optional[List[int]], Optional[int]]:
    s = (spec or "").strip()
    if not s or s == "*":
        return ("all", None, None)
    if s.endswith("+"):
        try:
            return ("min", None, int(s[:-1]))
        except Exception:
            return ("all", None, None)
    seasons: List[int] = []
    for part in s.split(","):
        p = part.strip()
        if not p:
            continue
        if "-" in p:
            a, b = p.split("-", 1)
            try:
                start = int(a)
                end = int(b)
                if start <= end:
                    seasons.extend(list(range(start, end + 1)))
                else:
                    seasons.extend(list(range(end, start + 1)))
            except Exception:
                continue
        else:
            try:
                seasons.append(int(p))
            except Exception:
                continue
    seasons = sorted({x for x in seasons if x > 0})
    return ("filter", seasons or None, None)


def season_allowed(season_number: int, mode: str, flt: Optional[List[int]], mn: Optional[int]) -> bool:
    if season_number <= 0:
        return False
    if mode == "all":
        return True
    if mode == "min":
        return mn is not None and season_number >= mn
    if mode == "filter":
        return flt is not None and season_number in flt
    return True


def trakt_search_tmdb(client_id: str, access_token: str, media_type: str, tmdb_id: int) -> Optional[Dict[str, Any]]:
    data = trakt_get_public(f"/search/tmdb/{tmdb_id}", client_id, params={"type": media_type, "extended": "full"})
    if not isinstance(data, list) or not data:
        return None
    item = data[0].get(media_type)
    return item if isinstance(item, dict) else None


def trakt_slug_link(kind: str, ids: Dict[str, Any]) -> str:
    slug = (ids or {}).get("slug")
    if not slug:
        return ""
    base = "shows" if kind == "show" else "movies"
    return f"https://trakt.tv/{base}/{slug}"


def build_stream_links(cfg: Dict[str, Any], kind: str, tmdb_id: Any) -> Dict[str, str]:
    tmdb = str(tmdb_id or "").strip()
    if not tmdb:
        return {}
    streaming = cfg.get("streaming") if isinstance(cfg, dict) else {}
    out: Dict[str, str] = {}
    providers = streaming.get("embed_providers") if isinstance(streaming, dict) else []
    template_field = "tv_template" if kind == "episode" else "movie_template"
    for provider in providers if isinstance(providers, list) else []:
        if not isinstance(provider, dict):
            continue
        key = str(provider.get("key") or "").strip()
        template = str(provider.get(template_field) or "").strip()
        if key not in {"vidsrc_net", "videasy"} or not template:
            continue
        try:
            href = template.format(tmdb_id=tmdb, season="", episode="")
        except Exception:
            href = ""
        if href:
            out["vidsrc" if key == "vidsrc_net" else key] = href
    return out


def normalize_show(obj: Dict[str, Any], season_mode: str, season_filter: Optional[List[int]], season_min: Optional[int]) -> Dict[str, Any]:
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
        "genres": [{"name": g} for g in (obj.get("genres") or []) if isinstance(g, str)],
        "number_of_episodes": obj.get("aired_episodes"),
        "season_mode": season_mode,
        "season_filter": season_filter,
        "season_min": season_min,
        "seasons": [],
        "links": {"trakt": trakt_slug_link("show", ids)},
    }


def normalize_movie(obj: Dict[str, Any]) -> Dict[str, Any]:
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
        "genres": [{"name": g} for g in (obj.get("genres") or []) if isinstance(g, str)],
        "links": {"trakt": trakt_slug_link("movie", ids)},
    }


def pull_show_seasons(show_id: str, client_id: str, access_token: str, season_mode: str, season_filter: Optional[List[int]], season_min: Optional[int]) -> List[Dict[str, Any]]:
    seasons = trakt_get(f"/shows/{show_id}/seasons", client_id, access_token, params={"extended": "episodes"})
    out: List[Dict[str, Any]] = []
    for s in seasons or []:
        if not isinstance(s, dict):
            continue
        season_number = s.get("number")
        if not isinstance(season_number, int):
            continue
        if not season_allowed(season_number, season_mode, season_filter, season_min):
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
    if blank(client_id):
        print("ERROR: Missing API_TRAKT_ID.", file=sys.stderr)
        return 2

    access_token = None
    tok = load_tokens_file()
    access_token = tok.get("access_token") or access_token
    if blank(access_token):
        access_token = os.getenv("API_TRAKT_ACCESS_TOKEN") or access_token
    if blank(access_token):
        print("ERROR: Missing Trakt access token. Run scripts/trakt_device_auth.py first.", file=sys.stderr)
        return 3

    tv_list, movie_list = load_inputs()
    cfg = load_jsonc(CONFIG_JSON)

    data: Dict[str, Any] = {
        "meta": {
            "generated_utc": _utc(),
            "builder": {"script": "scripts/fetch_trakt_primary.py", "version": "v1.2.0"},
            "source": "inputs + trakt metadata + trakt user state",
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

    def safe_get_public(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            return trakt_get_public(path, client_id, params=params)
        except Exception as ex:
            errors.append({"type": "trakt_fetch", "path": path, "message": str(ex)[:300], "utc": _utc()})
            return []

    # Resolve username for list endpoints
    settings = safe_get("/users/settings")
    user_obj = (settings or {}).get("user") or {}
    username = user_obj.get("username") or (user_obj.get("ids") or {}).get("slug")

    # Core user datasets
    lists = safe_get(f"/users/{username}/lists") if username else []
    list_items: Dict[str, Any] = {}
    for lst in lists or []:
        list_id = lst.get("ids", {}).get("trakt")
        if list_id is None:
            continue
        if username:
            list_items[str(list_id)] = safe_get(f"/users/{username}/lists/{list_id}/items", params={"extended": "full"})

    collection_movies = safe_get("/sync/collection/movies", params={"extended": "full"})
    collection_shows = safe_get("/sync/collection/shows", params={"extended": "full"})
    watchlist_movies = safe_get("/sync/watchlist/movies", params={"extended": "full"})
    watchlist_shows = safe_get("/sync/watchlist/shows", params={"extended": "full"})
    watched_movies = safe_get("/sync/watched/movies", params={"extended": "full"})
    watched_shows = safe_get("/sync/watched/shows", params={"extended": "full"})
    playback = safe_get("/sync/playback")
    activity = safe_get("/sync/last_activities")

    genres_movies = safe_get_public("/genres/movies")
    genres_shows = safe_get_public("/genres/shows")

    def _tmdb_id_from(row: Dict[str, Any], key: str) -> Optional[int]:
        obj = row.get(key) if isinstance(row, dict) else None
        ids = obj.get("ids") if isinstance(obj, dict) else None
        tmdb = ids.get("tmdb") if isinstance(ids, dict) else None
        return tmdb if isinstance(tmdb, int) else None

    summary_movies: Dict[str, Any] = {}
    summary_shows: Dict[str, Any] = {}

    def default_summary(tmdb_id: int) -> Dict[str, Any]:
        return {
            "tmdb_id": tmdb_id,
            "in_collection": False,
            "in_watchlist": False,
            "watched": False,
            "plays": 0,
            "last_watched_at": None,
            "progress": None,
            "paused_at": None,
            "completed": None,
            "last_updated_at": None,
        }

    def ensure_movie(tmdb_id: int) -> Dict[str, Any]:
        return summary_movies.setdefault(str(tmdb_id), default_summary(tmdb_id))

    def ensure_show(tmdb_id: int) -> Dict[str, Any]:
        return summary_shows.setdefault(str(tmdb_id), default_summary(tmdb_id))

    for row in collection_movies or []:
        tid = _tmdb_id_from(row, "movie")
        if tid is None:
            continue
        entry = ensure_movie(tid)
        entry["in_collection"] = True
        if row.get("collected_at"):
            entry["collected_at"] = row.get("collected_at")

    for row in collection_shows or []:
        tid = _tmdb_id_from(row, "show")
        if tid is None:
            continue
        entry = ensure_show(tid)
        entry["in_collection"] = True
        if row.get("collected_at"):
            entry["collected_at"] = row.get("collected_at")

    for row in watchlist_movies or []:
        tid = _tmdb_id_from(row, "movie")
        if tid is None:
            continue
        entry = ensure_movie(tid)
        entry["in_watchlist"] = True
        if row.get("listed_at"):
            entry["watchlist_added_at"] = row.get("listed_at")

    for row in watchlist_shows or []:
        tid = _tmdb_id_from(row, "show")
        if tid is None:
            continue
        entry = ensure_show(tid)
        entry["in_watchlist"] = True
        if row.get("listed_at"):
            entry["watchlist_added_at"] = row.get("listed_at")

    for row in watched_movies or []:
        tid = _tmdb_id_from(row, "movie")
        if tid is None:
            continue
        entry = ensure_movie(tid)
        entry["watched"] = True
        entry["plays"] = row.get("plays")
        entry["last_watched_at"] = row.get("last_watched_at")

    for row in watched_shows or []:
        tid = _tmdb_id_from(row, "show")
        if tid is None:
            continue
        entry = ensure_show(tid)
        entry["watched"] = True
        entry["plays"] = row.get("plays")
        entry["completed"] = row.get("completed")
        entry["last_watched_at"] = row.get("last_watched_at")
        entry["last_updated_at"] = row.get("last_updated_at")

    for row in playback or []:
        if not isinstance(row, dict):
            continue
        typ = row.get("type")
        progress = row.get("progress")
        if typ == "movie":
            tid = _tmdb_id_from(row, "movie")
            if tid is None:
                continue
            entry = ensure_movie(tid)
            if progress is not None:
                entry["progress"] = progress
            if row.get("paused_at"):
                entry["paused_at"] = row.get("paused_at")
        elif typ == "episode":
            show = row.get("show") or {}
            ids = show.get("ids") or {}
            tid = ids.get("tmdb") if isinstance(ids.get("tmdb"), int) else None
            if tid is None:
                continue
            entry = ensure_show(tid)
            if progress is not None:
                entry["progress"] = progress
            if row.get("paused_at"):
                entry["paused_at"] = row.get("paused_at")

    catalog_show_ids = {tid for x in tv_list if isinstance(x, dict) for tid in [to_int(x.get("tmdb_id"))] if tid is not None}
    catalog_movie_ids = {tid for x in movie_list if isinstance(x, dict) for tid in [to_int(x.get("tmdb_id"))] if tid is not None}

    def _filter_summary(src: Dict[str, Any], allowed: set[int]) -> Dict[str, Any]:
        return {k: v for k, v in src.items() if k.isdigit() and int(k) in allowed}

    for tid in catalog_movie_ids:
        summary_movies.setdefault(str(tid), default_summary(tid))
    for tid in catalog_show_ids:
        summary_shows.setdefault(str(tid), default_summary(tid))

    data["trakt"] = {
        "user": {"username": username},
        "summary": {
            "movies": _filter_summary(summary_movies, catalog_movie_ids),
            "shows": _filter_summary(summary_shows, catalog_show_ids),
        },
        "counts": {
            "collection_movies": len(collection_movies or []),
            "collection_shows": len(collection_shows or []),
            "watchlist_movies": len(watchlist_movies or []),
            "watchlist_shows": len(watchlist_shows or []),
            "watched_movies": len(watched_movies or []),
            "watched_shows": len(watched_shows or []),
            "playback": len(playback or []),
        },
        "supporting": {"genres": {"movies": genres_movies, "shows": genres_shows}},
    }

    stats = {
        "sources": {
            "inputs_tv": len(tv_list),
            "inputs_movies": len(movie_list),
            "lists_index": len(lists or []),
            "lists_items_total": sum(len(v or []) for v in list_items.values()),
        },
        "resolved": {"shows": 0, "movies": 0},
        "drops": {"missing_tmdb": 0, "trakt_not_found": 0, "missing_ids": 0},
    }

    # Build shows from inputs.json -> Trakt
    for item in tv_list:
        tmdb_id = to_int(item.get("tmdb_id"))
        if tmdb_id is None:
            stats["drops"]["missing_tmdb"] += 1
            continue
        season_spec = str(item.get("season_spec") or item.get("seasons") or "").strip()
        season_mode, season_filter, season_min = parse_season_rule(season_spec)
        try:
            show = trakt_search_tmdb(client_id, access_token, "show", int(tmdb_id))
        except Exception as ex:
            errors.append({"type": "trakt_search", "media": "show", "tmdb_id": tmdb_id, "message": str(ex)[:300], "utc": _utc()})
            show = None
        if not show:
            stats["drops"]["trakt_not_found"] += 1
            continue
        ids = show.get("ids") or {}
        if not ids.get("tmdb") or not ids.get("trakt"):
            stats["drops"]["missing_ids"] += 1
            continue
        show_obj = normalize_show(show, season_mode, season_filter, season_min)
        links = show_obj.get("links") if isinstance(show_obj.get("links"), dict) else {}
        links.update(build_stream_links(cfg, "episode", tmdb_id))
        show_obj["links"] = links
        try:
            show_obj["seasons"] = pull_show_seasons(str(ids.get("trakt")), client_id, access_token, season_mode, season_filter, season_min)
        except Exception as ex:
            errors.append({"type": "trakt_seasons", "trakt_id": ids.get("trakt"), "message": str(ex)[:300], "utc": _utc()})
        for season in show_obj.get("seasons") or []:
            for ep in season.get("episodes") or []:
                links = ep.get("links") if isinstance(ep.get("links"), dict) else {}
                links.update(build_stream_links(cfg, "episode", tmdb_id))
                ep["links"] = links
        data["shows"].append(show_obj)
        stats["resolved"]["shows"] += 1

    # Build movies from inputs.json -> Trakt
    for item in movie_list:
        tmdb_id = to_int(item.get("tmdb_id"))
        if tmdb_id is None:
            stats["drops"]["missing_tmdb"] += 1
            continue
        try:
            movie = trakt_search_tmdb(client_id, access_token, "movie", int(tmdb_id))
        except Exception as ex:
            errors.append({"type": "trakt_search", "media": "movie", "tmdb_id": tmdb_id, "message": str(ex)[:300], "utc": _utc()})
            movie = None
        if not movie:
            stats["drops"]["trakt_not_found"] += 1
            continue
        ids = movie.get("ids") or {}
        if not ids.get("tmdb") or not ids.get("trakt"):
            stats["drops"]["missing_ids"] += 1
            continue
        movie_obj = normalize_movie(movie)
        links = movie_obj.get("links") if isinstance(movie_obj.get("links"), dict) else {}
        links.update(build_stream_links(cfg, "movie", tmdb_id))
        movie_obj["links"] = links
        data["movies"].append(movie_obj)
        stats["resolved"]["movies"] += 1

    data["meta"]["trakt_primary_stats"] = stats

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[fetch_trakt_primary] wrote {DATA_JSON} (shows={len(data['shows'])} movies={len(data['movies'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
