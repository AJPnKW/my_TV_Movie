# -----------------------------------------------------------------------------
# File: /scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v1.4.0 (2025-11-07)
#
# Features:
# - Read:
#     tv_list.txt
#       name | tmdb_show_id | season_spec | tvmaze_id (optional)
#     movies_list.txt
#       name | tmdb_movie_id
# - Fetch from TMDB:
#     * Show details, seasons, episodes
#     * Movie details
# - Optional TVMaze enrichment (episodes):
#     * Requires:
#         - API_TVMAZE_KEY (GitHub secret / env)
#         - tvmaze_id in tv_list.txt line
#     * Fills missing air_dates, real titles, overviews where TMDB is vague.
# - Output:
#     data/data.json:
#       {
#         generated_at: ISO timestamp,
#         shows:  [ { show data..., profile } ],
#         movies: [ { movie data..., profile } ],
#         meta: {
#           shows: <int>,
#           movies: <int>
#         }
#       }
#     data/last_refresh.txt (human timestamp)
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
    def load_dotenv(*args, **kwargs):
        pass

import requests

# --- Paths --------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"
MOVIES_LIST = ROOT / "movies_list.txt"
DATA_DIR = ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"
STAMP = DATA_DIR / "last_refresh.txt"

# --- Environment --------------------------------------------------------------
load_dotenv(ROOT / ".env")

TMDB_V3 = os.environ.get("API_TMDB_KEY", "")
TMDB_V4 = os.environ.get("API_TMDB_TOKEN", "")
TVMAZE_KEY = os.environ.get("API_TVMAZE_KEY", "")  # optional

BASE_TMDB = "https://api.themoviedb.org/3"
BASE_TVMAZE = "https://api.tvmaze.com"

HEADERS_TMDB = (
    {"Authorization": f"Bearer {TMDB_V4}", "Accept": "application/json"}
    if TMDB_V4
    else None
)
PARAMS_TMDB = {"api_key": TMDB_V3} if TMDB_V3 and not TMDB_V4 else {}

# tv_list line:
# name | tmdb_show_id | season_spec | tvmaze_id?
TV_LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)(?:\s*\|\s*(\d+))?\s*$"
)

# movies_list line:
# name | tmdb_movie_id
MOVIE_LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*$"
)


# --- HTTP helpers -------------------------------------------------------------

def tmdb_get(path: str, extra_params=None, max_tries=5, backoff=1.5):
    url = f"{BASE_TMDB}{path}"
    params = {}
    if not TMDB_V4:
        params.update(PARAMS_TMDB)
    if extra_params:
        params.update(extra_params or {})

    session = requests.Session()
    if HEADERS_TMDB:
        session.headers.update(HEADERS_TMDB)

    for attempt in range(max_tries):
        r = session.get(url, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError(f"TMDB rate-limited/failed for {url}")


def tvmaze_get(path: str, params=None, max_tries=3, backoff=1.5):
    """Optional TVMaze helper; only used if API_TVMAZE_KEY is set."""
    if not TVMAZE_KEY:
        raise RuntimeError("TVMaze disabled (no API_TVMAZE_KEY).")
    url = f"{BASE_TVMAZE}{path}"
    headers = {"X-API-Key": TVMAZE_KEY}
    for attempt in range(max_tries):
        r = requests.get(url, headers=headers, params=params or {}, timeout=20)
        if r.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"TVMaze rate-limited/failed for {url}")


def strip_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "").strip()


# --- Parse tv_list.txt --------------------------------------------------------

def parse_tv_list(path: pathlib.Path):
    if not path.exists():
        return []
    shows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = TV_LINE_RE.match(line)
            if not m:
                print(f"WARN: Skipping bad tv_list line: {line}")
                continue
            name, show_id, seasons, tvmaze_id = m.groups()
            if seasons == "*":
                season_spec = "*"
            else:
                season_spec = [
                    int(s.strip()) for s in seasons.split(",") if s.strip()
                ]
            entry = {
                "ref_name": name,
                "show_id": int(show_id),
                "season_spec": season_spec,
                "profile": "default",  # hook for future profiles
            }
            if tvmaze_id:
                entry["tvmaze_id"] = int(tvmaze_id)
            shows.append(entry)
    return shows


# --- Parse movies_list.txt ----------------------------------------------------

def parse_movies_list(path: pathlib.Path):
    if not path.exists():
        return []
    movies = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = MOVIE_LINE_RE.match(line)
            if not m:
                print(f"WARN: Skipping bad movies_list line: {line}")
                continue
            name, movie_id = m.groups()
            movies.append(
                {
                    "ref_name": name,
                    "movie_id": int(movie_id),
                    "profile": "default",  # hook for future profiles
                }
            )
    return movies


# --- Utility: episode title normalization -------------------------------------

def is_placeholder_title(name: str) -> bool:
    if not name:
        return True
    ln = name.strip().lower()
    if ln in {"tba", "n/a"}:
        return True
    if ln.startswith("episode "):
        return True
    return False


def ensure_title(ep: dict, season_no: int) -> str:
    name = ep.get("name") or ""
    ep_no = ep.get("episode_number") or 0
    if is_placeholder_title(name):
        return f"S{season_no:02d}E{ep_no:02d}"
    return name


# --- Link builders ------------------------------------------------------------

def show_links(show_id: int):
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{show_id}",
        "watch_vidsrc": f"https://vidsrc.net/embed/tv/{show_id}",
        "watch_videasy": f"https://player.videasy.net/tv/{show_id}",
    }


def movie_links(movie_id: int):
    return {
        "tmdb": f"https://www.themoviedb.org/movie/{movie_id}",
        "watch_vidsrc": f"https://vidsrc.net/embed/movie/{movie_id}",
        "watch_videasy": f"https://player.videasy.net/movie/{movie_id}",
    }


# --- TVMaze enrichment --------------------------------------------------------

def enrich_with_tvmaze(show_payload: dict, tvmaze_id: int):
    """
    Best-effort:
    - Do nothing if TVMAZE_KEY missing.
    - For matching (season, ep) pairs, fill:
        * missing air_date
        * real titles if TMDB placeholder
        * missing overviews
    """
    if not TVMAZE_KEY or not tvmaze_id:
        return
    try:
        eps = tvmaze_get(f"/shows/{tvmaze_id}/episodes")
    except Exception as e:
        print(f"WARN: TVMaze fetch failed for {show_payload['name']}: {e}")
        return

    idx = {
        (e.get("season"), e.get("number")): e
        for e in eps
        if e.get("season") is not None and e.get("number") is not None
    }

    for s in show_payload.get("seasons", []):
        sn = s["season_number"]
        for ep in s.get("episodes", []):
            key = (sn, ep.get("episode_number"))
            src = idx.get(key)
            if not src:
                continue

            if not ep.get("air_date") and src.get("airdate"):
                ep["air_date"] = src["airdate"]

            if is_placeholder_title(ep.get("name") or "") and src.get("name"):
                ep["name"] = src["name"]

            if not ep.get("overview") and src.get("summary"):
                ep["overview"] = strip_html(src["summary"])


# --- Collect TV show from TMDB (+ optional TVMaze) ----------------------------

def collect_show(show_id: int, season_spec, tvmaze_id=None):
    show = tmdb_get(f"/tv/{show_id}")
    genres = [g["name"] for g in show.get("genres", [])]

    all_seasons_meta = {
        s["season_number"]: s
        for s in show.get("seasons", [])
        if s.get("season_number", 0) > 0
    }

    if season_spec == "*":
        wanted = sorted(all_seasons_meta.keys())
    else:
        wanted = [s for s in season_spec if s in all_seasons_meta]

    seasons = []
    for sn in wanted:
        s_meta = all_seasons_meta.get(sn, {})
        s_info = tmdb_get(f"/tv/{show_id}/season/{sn}")
        eps = []
        for ep in s_info.get("episodes", []):
            eps.append(
                {
                    "episode_number": ep.get("episode_number"),
                    "name": ensure_title(ep, sn),
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview") or "",
                    "still_path": ep.get("still_path"),
                }
            )
        seasons.append(
            {
                "season_number": sn,
                "name": s_meta.get("name") or f"Season {sn}",
                "air_date": s_meta.get("air_date") or s_info.get("air_date"),
                "episode_count": len(eps),
                "overview": s_info.get("overview") or s_meta.get("overview") or "",
                "episodes": eps,
            }
        )

    payload = {
        "show_id": show_id,
        "name": show.get("name"),
        "original_name": show.get("original_name"),
        "overview": show.get("overview") or "",
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "status": show.get("status"),  # used for filters/status display
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "genres": genres,
        "links": show_links(show_id),
        "seasons": seasons,
    }

    if tvmaze_id:
        enrich_with_tvmaze(payload, tvmaze_id)

    return payload


# --- Collect Movie from TMDB --------------------------------------------------

def collect_movie(movie_id: int):
    mv = tmdb_get(f"/movie/{movie_id}")
    genres = [g["name"] for g in mv.get("genres", [])]
    return {
        "movie_id": movie_id,
        "name": mv.get("title"),
        "original_name": mv.get("original_title"),
        "overview": mv.get("overview") or "",
        "release_date": mv.get("release_date"),
        "runtime": mv.get("runtime"),
        "status": mv.get("status"),  # e.g. Released, Planned, etc.
        "poster_path": mv.get("poster_path"),
        "backdrop_path": mv.get("backdrop_path"),
        "genres": genres,
        "links": movie_links(movie_id),
    }


# --- Main ---------------------------------------------------------------------

def main():
    if not TMDB_V3 and not TMDB_V4:
        print("ERROR: Set API_TMDB_KEY or API_TMDB_TOKEN.")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tv_specs = parse_tv_list(TV_LIST)
    mv_specs = parse_movies_list(MOVIES_LIST)

    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "shows": [],
        "movies": [],
    }

    # Shows
    for item in tv_specs:
        try:
            print(
                f"Show: {item['ref_name']} ({item['show_id']}) "
                f"seasons={item['season_spec']}"
            )
            data = collect_show(
                item["show_id"],
                item["season_spec"],
                tvmaze_id=item.get("tvmaze_id"),
            )
            data["ref_name"] = item["ref_name"]
            data["profile"] = item.get("profile", "default")
            out["shows"].append(data)
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR show {item['ref_name']} ({item['show_id']}): {e}")

    # Movies
    for item in mv_specs:
        try:
            print(f"Movie: {item['ref_name']} ({item['movie_id']})")
            mv = collect_movie(item["movie_id"])
            mv["ref_name"] = item["ref_name"]
            mv["profile"] = item.get("profile", "default")
            out["movies"].append(mv)
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR movie {item['ref_name']} ({item['movie_id']}): {e}")

    out["meta"] = {
        "shows": len(out["shows"]),
        "movies": len(out["movies"]),
    }

    DATA_JSON.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    STAMP.write_text(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        encoding="utf-8",
    )
    print(f"Wrote: {DATA_JSON}")


if __name__ == "__main__":
    main()
