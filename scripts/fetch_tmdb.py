# -----------------------------------------------------------------------------
# File: /scripts/fetch_tmdb.py
# Project: my_TV_Movie
# Version: v1.1.0 (2025-11-06)
# Purpose:
#   - Parse /tv_list.txt (pipe-separated lines: name|tmdb_show_id|season_spec)
#   - Query TMDB for each show/season/episodes
#   - Normalize episodes (fill missing titles as "SxxEyy")
#   - Write /data/data.json (consumed by web/index.html)
#   - Write /data/last_refresh.txt (human-readable timestamp)
#
# Inputs:
#   - Environment: API_TMDB_KEY (v3 key) or API_TMDB_TOKEN (v4 bearer)
#   - File: /tv_list.txt
#
# Outputs:
#   - /data/data.json
#   - /data/last_refresh.txt
#
# ChangeLog:
#   - v1.1.0: Hardened rate-limit handling; extra comments; stable paths for GH Actions.
#   - v1.0.0: Initial version.
# -----------------------------------------------------------------------------

import os, json, time, re, pathlib, sys
from datetime import datetime
try:
    from dotenv import load_dotenv  # used locally; Actions doesn't require .env
except ImportError:
    def load_dotenv(*args, **kwargs): pass
import requests

# --- Paths -------------------------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root
TV_LIST = ROOT / 'tv_list.txt'
DATA_DIR = ROOT / 'data'
DATA_JSON = DATA_DIR / 'data.json'
STAMP = DATA_DIR / 'last_refresh.txt'

# --- API keys (supports both v3 and v4) --------------------------------------
# Prefer environment variables. For local runs, .env is allowed but optional.
load_dotenv(ROOT / '.env')
TMDB_V3 = os.environ.get('API_TMDB_KEY', '')
TMDB_V4 = os.environ.get('API_TMDB_TOKEN', '')  # bearer

BASE = 'https://api.themoviedb.org/3'  # v3 endpoints also usable with v4 bearer
HEADERS = {'Authorization': f'Bearer {TMDB_V4}', 'Accept': 'application/json'} if TMDB_V4 else None
params_key = {'api_key': TMDB_V3} if TMDB_V3 and not TMDB_V4 else {}

# --- Input line regex (name|id|season_spec) ----------------------------------
re_line = re.compile(r'^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)\s*$')

# --- Helpers -----------------------------------------------------------------
def tmdb_get(path, extra_params=None, max_tries=5, backoff=1.5):
    """GET helper with simple rate-limit backoff. Works with v3 querystring or v4 bearer."""
    url = f"{BASE}{path}"
    params = {}
    if not TMDB_V4:
        params.update(params_key)
    if extra_params:
        params.update(extra_params)

    s = requests.Session()
    if HEADERS:
        s.headers.update(HEADERS)

    for attempt in range(max_tries):
        r = s.get(url, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"TMDB rate-limited or failed after {max_tries} tries: {url}")

def parse_tv_list(path: pathlib.Path):
    """Read tv_list.txt and yield dicts {ref_name, show_id, season_spec}."""
    shows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re_line.match(line)
            if not m:
                print(f"WARN: Skipping unrecognized line: {line}")
                continue
            name, show_id, seasons = m.groups()
            if seasons == '*':
                season_spec = '*'
            else:
                season_spec = [int(s.strip()) for s in seasons.split(',') if s.strip()]
            shows.append({'ref_name': name, 'show_id': int(show_id), 'season_spec': season_spec})
    return shows

def build_links(show_id: int):
    """Return the three per-show links requested for episodes."""
    return {
        'tmdb': f'https://www.themoviedb.org/tv/{show_id}',
        'watch_vidsrc': f'https://vidsrc.net/embed/tv/{show_id}',
        'watch_videasy': f'https://player.videasy.net/tv/{show_id}',
    }

def ensure_title(ep, season_no):
    """If an episode has no name or a placeholder like 'Episode 3', synthesize SxxEyy."""
    name = ep.get('name') or ''
    ep_no = ep.get('episode_number') or 0
    if not name or name.lower().startswith('episode '):
        return f"S{season_no:02d}E{ep_no:02d}"
    return name

def collect_show(show_id: int, season_spec):
    """Fetch show core info + selected seasons + all episodes."""
    show = tmdb_get(f"/tv/{show_id}")
    genres = [g['name'] for g in show.get('genres', [])]
    # ignore season 0 (specials) for now
    seasons_meta = {s['season_number']: s for s in show.get('seasons', []) if s.get('season_number', 0) > 0}

    if season_spec == '*':
        wanted = sorted(seasons_meta.keys())
    else:
        # only keep season numbers that exist on TMDB
        wanted = [s for s in season_spec if s in seasons_meta]

    seasons = []
    for sn in wanted:
        s_info = tmdb_get(f"/tv/{show_id}/season/{sn}")
        episodes = []
        for ep in s_info.get('episodes', []):
            ep_obj = {
                'episode_number': ep.get('episode_number'),
                'name': ensure_title(ep, sn),
                'air_date': ep.get('air_date'),
                'overview': ep.get('overview') or '',
                'still_path': ep.get('still_path'),
            }
            episodes.append(ep_obj)
        seasons.append({
            'season_number': sn,
            'episodes': episodes,
        })

    payload = {
        'show_id': show_id,
        'name': show.get('name'),
        'original_name': show.get('original_name'),
        'first_air_date': show.get('first_air_date'),
        'last_air_date': show.get('last_air_date'),
        'status': show.get('status'),
        'poster_path': show.get('poster_path'),
        'backdrop_path': show.get('backdrop_path'),
        'genres': genres,
        'links': build_links(show_id),
        'seasons': seasons,
    }
    return payload

# --- Main --------------------------------------------------------------------
def main():
    if not TMDB_V3 and not TMDB_V4:
        print('ERROR: Set API_TMDB_KEY or API_TMDB_TOKEN environment variable.')
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    shows = parse_tv_list(TV_LIST)
    out = {'generated_at': datetime.utcnow().isoformat() + 'Z', 'shows': []}

    for item in shows:
        try:
            print(f"Fetching TMDB: {item['ref_name']} ({item['show_id']}) seasons={item['season_spec']}")
            data = collect_show(item['show_id'], item['season_spec'])
            data['ref_name'] = item['ref_name']  # keep user-friendly label
            out['shows'].append(data)
            time.sleep(0.2)  # be nice to API
        except Exception as e:
            print(f"ERROR: {item['ref_name']} ({item['show_id']}): {e}")

    DATA_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    STAMP.write_text(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print(f"Wrote: {DATA_JSON}")

if __name__ == '__main__':
    main()
