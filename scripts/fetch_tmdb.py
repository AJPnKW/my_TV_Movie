# -----------------------------------------------------------------------------
# File: /scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v1.2.0 (2025-11-06)
# Purpose:
#   - Parse /tv_list.txt (name | tmdb_show_id | season_spec)
#   - Fetch show/season/episode data from TMDB
#   - Fill missing/placeholder episode titles as SxxEyy
#   - Write /data/data.json and /data/last_refresh.txt
# -----------------------------------------------------------------------------

import os
import json
import time
import re
import pathlib
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv  # for local dev
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

import requests

# --- Paths --------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / "tv_list.txt"
DATA_DIR = ROOT / "data"
DATA_JSON = DATA_DIR / "data.json"
STAMP = DATA_DIR / "last_refresh.txt"

# --- API keys -----------------------------------------------------------------
load_dotenv(ROOT / ".env")

TMDB_V3 = os.environ.get("API_TMDB_KEY", "")
TMDB_V4 = os.environ.get("API_TMDB_TOKEN", "")

BASE = "https://api.themoviedb.org/3"
HEADERS = (
    {"Authorization": f"Bearer {TMDB_V4}", "Accept": "application/json"}
    if TMDB_V4
    else None
)
PARAMS_KEY = {"api_key": TMDB_V3} if TMDB_V3 and not TMDB_V4 else {}

# --- Input format: name | id | seasons ---------------------------------------
LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)\s*$"
)

# --- HTTP helper --------------------------------------------------------------
def tmdb_get(path: str, extra_params=None, max_tries=5, backoff=1.5):
    """GET wrapper with simple 429 backoff."""
    url = f"{BASE}{path}"
    params = {}
    if not TMDB_V4:
        params.update(PARAMS_KEY)
    if extra_params:
        params.update(extra_params)

    session = requests.Session()
    if HEADERS:
        session.headers.update(HEADERS)

    for attempt in range(max_tries):
        r = session.get(url, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError(f"TMDB rate-limited or failed: {url}")

# --- Parsing tv_list.txt ------------------------------------------------------
def parse_tv_list(path: pathlib.Path):
    """
    Read tv_list.txt and yield:
      { 'ref_name': str, 'show_id': int, 'season_spec': '*' or [int,...] }
    """
    shows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = LINE_RE.match(line)
            if not m:
                print(f"WARN: Skipping unrecognized line: {line}")
                continue
            name, show_id, seasons = m.groups()
            if seasons == "*":
                season_spec = "*"
            else:
                season_spec = [
                    int(s.strip()) for s in seasons.split(",") if s.strip()
                ]
            shows.append(
                {
                    "ref_name": name,
                    "show_id": int(show_id),
                    "season_spec": season_spec,
                }
            )
    return shows

# --- Link builder -------------------------------------------------------------
def build_links(show_id: int):
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{show_id}",
        "watch_vidsrc": f"https://vidsrc.net/embed/tv/{show_id}",
        "watch_videasy": f"https://player.videasy.net/tv/{show_id}",
    }

# --- Episode title normalizer -------------------------------------------------
def ensure_title(ep: dict, season_no: int) -> str:
    name = ep.get("name") or ""
    ep_no = ep.get("episode_number") or 0
    if not name or name.lower().startswith("episode "):
        return f"S{season_no:02d}E{ep_no:02d}"
    return name

# --- TMDB data collector ------------------------------------------------------
def collect_show(show_id: int, season_spec):
    show = tmdb_get(f"/tv/{show_id}")
    genres = [g["name"] for g in show.get("genres", [])]

    seasons_meta = {
        s["season_number"]: s
        for s in show.get("seasons", [])
        if s.get("season_number", 0) > 0
    }

    if season_spec == "*":
        wanted = sorted(seasons_meta.keys())
    else:
        wanted = [s for s in season_spec if s in seasons_meta]

    seasons = []
    for sn in wanted:
        s_info = tmdb_get(f"/tv/{show_id}/season/{sn}")
        episodes = []
        for ep in s_info.get("episodes", []):
            episodes.append(
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
                "episodes": episodes,
            }
        )

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
        "links": build_links(show_id),
        "seasons": seasons,
    }

# --- Main ---------------------------------------------------------------------
def main():
    if not TMDB_V3 and not TMDB_V4:
        print("ERROR: Set API_TMDB_KEY or API_TMDB_TOKEN environment variable.")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    shows = parse_tv_list(TV_LIST)
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "shows": [],
    }

    for item in shows:
        try:
            print(
                f"Fetching TMDB: {item['ref_name']} "
                f"({item['show_id']}) seasons={item['season_spec']}"
            )
            data = collect_show(item["show_id"], item["season_spec"])
            data["ref_name"] = item["ref_name"]
            out["shows"].append(data)
            time.sleep(0.2)
        except Exception as e:
            print(f"ERROR: {item['ref_name']} ({item['show_id']}): {e}")

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
