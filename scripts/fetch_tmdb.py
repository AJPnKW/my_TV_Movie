# scripts/fetch_tmdb.py
# Purpose: Build data/data.json from tv_list.txt via TMDB API
# Author: AJP + ChatGPT | Last Update: 2025-11-06

import os, json, time, re, pathlib, sys
from datetime import datetime
from dotenv import load_dotenv
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
TV_LIST = ROOT / 'tv_list.txt'
DATA_DIR = ROOT / 'data'
DATA_JSON = DATA_DIR / 'data.json'
STAMP = DATA_DIR / 'last_refresh.txt'

TMDB_V3 = os.environ.get('API_TMDB_KEY', '')
TMDB_V4 = os.environ.get('API_TMDB_TOKEN', '')
BASE = 'https://api.themoviedb.org/3'

HEADERS = {'Authorization': f'Bearer {TMDB_V4}'} if TMDB_V4 else None

load_dotenv(ROOT / '.env')  # allow optional .env

if not TMDB_V3 and not TMDB_V4:
    print('ERROR: Set API_TMDB_KEY or API_TMDB_TOKEN environment variable.')
    sys.exit(1)

if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
if TMDB_V4:
    session.headers.update({'Authorization': f'Bearer {TMDB_V4}', 'Accept': 'application/json'})

params_key = {'api_key': TMDB_V3} if TMDB_V3 and not TMDB_V4 else {}

re_line = re.compile(r'^\s*([^#|]+?)\s*\|\s*(\d+)\s*\|\s*([\d,\*]+)\s*$')


def tmdb_get(path, extra_params=None):
    url = f"{BASE}{path}"
    params = {}
    if not TMDB_V4:
        params.update(params_key)
    if extra_params:
        params.update(extra_params)
    for attempt in range(5):
        r = session.get(url, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"TMDB rate-limited or failed: {url}")


def parse_tv_list(path: pathlib.Path):
    shows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
    main()
