# -----------------------------------------------------------------------------
# File: /scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v1.3.0 (2025-11-06)
#
# Purpose
#   - Read /tv_list.txt lines:
#       name | tmdb_show_id | season_spec | tvmaze_id (optional)
#     where:
#       season_spec: "5" or "1,2,5" or "*" (all seasons)
#   - Fetch show/season/episode data from TMDB.
#   - Optionally enrich episodes from TVmaze (if tvmaze_id + API_TVMAZE_KEY).
#   - Normalize episodes:
#       * keep TMDB titles
#       * if missing/placeholder => SxxEyy
#   - Write:
#       /data/data.json
#       /data/last_refresh.txt
#
# Notes
#   - Safe to run on GitHub Actions + locally.
#   - TVmaze is optional and best-effort; TMDB is source of truth.
# -----------------------------------------------------------------------------

import os
import json
import time
import re
import pathlib
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv  # for local dev; ignored in CI if missing
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

# --- Environment --------------------------------------------------------------
load_dotenv(ROOT / ".env")

TMDB_V3 = os.environ.get("API_TMDB_KEY", "")
TMDB_V4 = os.environ.get("API_TMDB_TOKEN", "")

TVMAZE_KEY = os.environ.get("API_TVMAZE_KEY", "")  # optional; for enrichment

BASE_TMDB = "https://api.themoviedb.org/3"
BASE_TVMAZE = "https://api.tvmaze.com"

HEADERS_TMDB = (
    {"Authorization": f"Bearer {TMDB_V4}", "Accept": "application/json"}
    if TMDB_V4
    else None
)
PARAMS_TMDB = {"api_key": TMDB_V3} if TMDB_V3 and not TMDB_V4 else {}

# name | tmdb_id | seasons | (optional) tvmaze_id
LINE_RE = re.compile(
    r"^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)(?:\s*\|\s*(\d+))?\s*$"
)


# --- HTTP helpers -------------------------------------------------------------

def tmdb_get(path: str, extra_params=None, max_tries=5, backoff=1.5):
    url = f"{BASE_TMDB}{path}"
    params = {}
    if not TMDB_V4:
        params.update(PARAMS_TMDB)
    if extra_params:
        params.update(extra_params)

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

    raise RuntimeError(f"TMDB rate-limited/failed: {url}")


def tvmaze_get(path: str, params=None, max_tries=3, backoff=1.5):
    """Optional helper. Does nothing if TVMAZE_KEY not set."""
    if not TVMAZE_KEY:
        raise RuntimeError("TVMaze disabled (no API_TVMAZE_KEY).")
    url = f"{BASE_TVMAZE}{path}"
    headers = {"X-API-Key": TVMAZE_KEY} if TVMAZE_KEY else {}
    for attempt in range(max_tries):
        r = requests.get(url, headers=headers, params=params or {}, timeout=20)
        if r.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"TVMaze rate-limited/failed: {url}")


def strip_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "").strip()


# --- tv_list.txt parser -------------------------------------------------------

def parse_tv_list(path: pathlib.Path):
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
            }
            if tvmaze_id:
                entry["tvmaze_id"] = int(tvmaze_id)
            shows.append(entry)
    return shows


# --- Link builders & title normalization --------------------------------------

def build_links(show_id: int):
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{show_id}",
        # show-level watch links (season/episode added per-use in UI where needed)
        "watch_vidsrc": f"https://vidsrc.net/embed/tv/{show_id}",
        "watch_videasy": f"https://player.videasy.net/tv/{show_id}",
    }


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


# --- TVMaze enrichment --------------------------------------------------------

def enrich_with_tvmaze(show_payload: dict, tvmaze_id: int):
    """
    Best-effort:
    - Use TVmaze episodes to fill missing dates / names / overviews.
    - Does NOT override good TMDB data.
    - Safe if it fails; we just log and move on.
    """
    if not TVMAZE_KEY or not tvmaze_id:
        return

    try:
        eps = tvmaze_get(f"/shows/{tvmaze_id}/episodes")
    except Exception as e:
        print(f"WARN: TVMaze fetch failed for {show_payload['name']}: {e}")
        return

    # Map (season, number) -> episode info
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

            # Airdate: fill if missing
            if not ep.get("air_date") and src.get("airdate"):
                ep["air_date"] = src["airdate"]

            # Title: if we had to synthesize and TVmaze has real title
            if is_placeholder_title(ep.get("name", "")) and src.get("name"):
                ep["name"] = src["name"]

            # Overview: fill if empty
            if not ep.get("overview") and src.get("summary"):
                ep["overview"] = strip_html(src["summary"])


# --- TMDB collector -----------------------------------------------------------

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
        "status": show.get("status"),
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "genres": genres,
        "links": build_links(show_id),
        "seasons": seasons,
    }

    if tvmaze_id:
        enrich_with_tvmaze(payload, tvmaze_id)

    return payload


# --- Main ---------------------------------------------------------------------

def main():
    if not TMDB_V3 and not TMDB_V4:
        print("ERROR: Set API_TMDB_KEY or API_TMDB_TOKEN.")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    shows_spec = parse_tv_list(TV_LIST)
    out = {"generated_at": datetime.utcnow().isoformat() + "Z", "shows": []}

    for item in shows_spec:
        try:
            print(
                f"Fetching TMDB: {item['ref_name']} "
                f"({item['show_id']}) seasons={item['season_spec']}"
            )
            data = collect_show(
                item["show_id"],
                item["season_spec"],
                tvmaze_id=item.get("tvmaze_id"),
            )
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
