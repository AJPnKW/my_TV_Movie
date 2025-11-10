# -----------------------------------------------------------------------------
# File: scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v2.0.2 (2025-11-10 23:55 EST)
#
# Purpose:
#   - Parse tv_list.txt and movies_list.txt
#   - Fetch TMDB metadata:
#       * TV shows + selected seasons + all episodes
#       * Movies
#   - Emit data/data.json consumed by web/index.html
#
# Input formats:
#   tv_list.txt:
#     name|tmdb_show_id|season_spec
#       season_spec:
#         *        = all seasons
#         "5"      = only season 5
#         "1,2,5"  = seasons 1, 2, 5
#
#   movies_list.txt:
#     name|tmdb_movie_id
#
# Output schema (simplified):
#   {
#     "generated_at": "...Z",
#     "shows": [ { show_id, name, status, poster_path, genres, networks, links, seasons: [...] } ],
#     "movies": [ { movie_id, tmdb_id, title, release_date, status, runtime, genres, collection, links } ],
#     "meta": { "shows": N, "movies": M }
#   }
# -----------------------------------------------------------------------------

import os
import json
import time
import re
import pathlib
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        pass

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"
MOVIES_LIST = ROOT / "movies_list.txt"
DATA_DIR = ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"
STAMP = DATA_DIR / "last_refresh.txt"

load_dotenv(ROOT / ".env")

TMDB_V3 = os.environ.get("API_TMDB_KEY", "").strip()
TMDB_V4 = os.environ.get("API_TMDB_TOKEN", "").strip()

BASE = "https://api.themoviedb.org/3"

HEADERS = {"Accept": "application/json"}
if TMDB_V4:
    HEADERS["Authorization"] = f"Bearer {TMDB_V4}"

PARAMS_KEY = {}
if TMDB_V3 and not TMDB_V4:
    PARAMS_KEY["api_key"] = TMDB_V3

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def tmdb_get(path, extra=None, tries=4, backoff=1.8):
    url = f"{BASE}{path}"
    params = dict(PARAMS_KEY)
    if extra:
        params.update(extra or {})
    last_err = None
    for attempt in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=25)
            if r.status_code == 429:
                sleep_for = backoff * (attempt + 1)
                print(f"[TMDB] 429 {url} -> sleep {sleep_for:.1f}s", flush=True)
                time.sleep(sleep_for)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            sleep_for = backoff * (attempt + 1)
            print(f"[TMDB] error on {url}: {e} (attempt {attempt+1}/{tries}), sleep {sleep_for:.1f}s", flush=True)
            time.sleep(sleep_for)
    raise RuntimeError(f"TMDB failed after {tries} attempts for {path}: {last_err}")


RE_TV = re.compile(r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)\s*$")
RE_MOVIE = re.compile(r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*$")


def parse_tv_list(path: pathlib.Path):
    items = []
    if not path.exists():
        print(f"[tv] NOTE: {path} missing, skipping TV.")
        return items
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = RE_TV.match(line)
        if not m:
            print(f"[tv] WARN: bad line: {line}")
            continue
        name, show_id, spec = m.groups()
        if spec.strip() == "*":
            season_spec = "*"
        else:
            season_spec = [
                int(s.strip()) for s in spec.split(",")
                if s.strip().isdigit()
            ]
        items.append({
            "ref_name": name,
            "show_id": int(show_id),
            "season_spec": season_spec,
        })
    return items


def parse_movies_list(path: pathlib.Path):
    items = []
    if not path.exists():
        print(f"[movie] NOTE: {path} missing, skipping movies.")
        return items
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = RE_MOVIE.match(line)
        if not m:
            print(f"[movie] WARN: bad line: {line}")
            continue
        name, mid = m.groups()
        items.append({
            "ref_name": name,
            "movie_id": int(mid),
        })
    return items


def build_show_links(show_id: int) -> dict:
    return {"tmdb": f"https://www.themoviedb.org/tv/{show_id}"}


def build_movie_links(movie_id: int) -> dict:
    return {"tmdb": f"https://www.themoviedb.org/movie/{movie_id}"}


def ensure_ep_title(ep: dict, season_no: int) -> str:
    name = (ep.get("name") or "").strip()
    ep_no = ep.get("episode_number") or 0
    if not name or name.lower().startswith("episode "):
        return f"S{season_no:02d}E{ep_no:02d}"
    return name


def collect_show(show_id: int, season_spec):
    show = tmdb_get(f"/tv/{show_id}")
    genres = [g["name"] for g in show.get("genres", [])]
    networks = [n["name"] for n in show.get("networks", [])]

    seasons_meta = {
        s["season_number"]: s
        for s in show.get("seasons", [])
        if s.get("season_number", 0) > 0
    }

    if season_spec == "*":
        wanted = sorted(seasons_meta.keys())
    else:
        wanted = [s for s in season_spec if s in seasons_meta]

    seasons_out = []
    for sn in wanted:
        s_info = tmdb_get(f"/tv/{show_id}/season/{sn}")
        episodes_out = []
        for ep in s_info.get("episodes", []):
            episodes_out.append({
                "episode_number": ep.get("episode_number"),
                "name": ensure_ep_title(ep, sn),
                "air_date": ep.get("air_date"),
                "overview": ep.get("overview") or "",
                "still_path": ep.get("still_path"),
                "runtime": ep.get("runtime"),
            })
        seasons_out.append({
            "season_number": sn,
            "name": s_info.get("name") or f"Season {sn}",
            "air_date": s_info.get("air_date"),
            "overview": s_info.get("overview") or "",
            "episode_count": len(episodes_out),
            "episodes": episodes_out,
        })

    return {
        "show_id": show_id,
        "name": show.get("name"),
        "original_name": show.get("original_name"),
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "status": show.get("status"),
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "genres": genres,
        "networks": networks,
        "links": build_show_links(show_id),
        "seasons": seasons_out,
    }


def collect_movie(movie_id: int, ref_name: str):
    mv = tmdb_get(f"/movie/{movie_id}")
    genres = [g["name"] for g in mv.get("genres", [])]
    col = mv.get("belongs_to_collection") or None
    return {
        "movie_id": movie_id,
        "tmdb_id": movie_id,
        "title": mv.get("title") or ref_name,
        "original_title": mv.get("original_title"),
        "release_date": mv.get("release_date"),
        "status": mv.get("status"),
        "runtime": mv.get("runtime"),
        "poster_path": mv.get("poster_path"),
        "backdrop_path": mv.get("backdrop_path"),
        "overview": mv.get("overview") or "",
        "genres": genres,
        "collection": {
            "id": col.get("id"),
            "name": col.get("name"),
        } if col else None,
            "links": build_movie_links(movie_id),
    }


def main():
    if not (TMDB_V3 or TMDB_V4):
        print("ERROR: API_TMDB_KEY or API_TMDB_TOKEN is required.", file=sys.stderr)
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tv_items = parse_tv_list(TV_LIST)
    mv_items = parse_movies_list(MOVIES_LIST)

    data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "shows": [],
        "movies": [],
        "meta": {"shows": 0, "movies": 0},
    }

    for item in tv_items:
        try:
            print(f"[tv] {item['ref_name']} ({item['show_id']}) {item['season_spec']}")
            show = collect_show(item["show_id"], item["season_spec"])
            show["ref_name"] = item["ref_name"]
            data["shows"].append(show)
            time.sleep(0.25)
        except Exception as e:  # noqa: BLE001
            print(f"[tv] ERROR for {item['ref_name']} ({item['show_id']}): {e}", file=sys.stderr)

    for item in mv_items:
        try:
            print(f"[movie] {item['ref_name']} ({item['movie_id']})")
            movie = collect_movie(item["movie_id"], item["ref_name"])
            data["movies"].append(movie)
            time.sleep(0.25)
        except Exception as e:  # noqa: BLE001
            print(f"[movie] ERROR for {item['ref_name']} ({item['movie_id']}): {e}", file=sys.stderr)

    data["meta"]["shows"] = len(data["shows"])
    data["meta"]["movies"] = len(data["movies"])

    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    STAMP.write_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")

    print(f"[ok] wrote {DATA_JSON} (shows={data['meta']['shows']}, movies={data['meta']['movies']})")


if __name__ == "__main__":
    main()
