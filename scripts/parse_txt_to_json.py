# File: scripts/parse_txt_to_json.py
# Purpose: Parse user-editable TXT inputs into canonical JSON with traceability
# Deterministic, atomic, schema-enforcing

import json
import os
import re
import time
import tempfile
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
INPUT_DIR = os.path.join(REPO_ROOT, "data", "inputs")
OUTPUT_FILE = os.path.join(DATA_DIR, "data.json")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_KEY = os.getenv("API_TMDB_KEY") or os.getenv("API_TMDB_TOKEN")

RETRIES = 3
BACKOFF = 0.6

SCHEMA_KEYS = {
    "tmdb_id", "official_title", "user_title", "year",
    "seasons", "active", "history"
}

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def atomic_write(path: str, payload: Dict[str, Any]) -> None:
    fd, tmp = tempfile.mkstemp(prefix="._tmp_", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        with open(tmp, "r", encoding="utf-8") as f:
            json.load(f)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f.readlines() if l.strip() and not l.strip().startswith("#")]

def tmdb_get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {}
    if TMDB_KEY and TMDB_KEY.startswith("ey"):
        headers["Authorization"] = f"Bearer {TMDB_KEY}"
    else:
        params = params or {}
        params["api_key"] = TMDB_KEY
    for i in range(RETRIES):
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
        time.sleep(BACKOFF * (i + 1))
    raise RuntimeError(f"TMDB request failed: {url}")

def normalize_title_by_id(tmdb_id: int, kind: str) -> Dict[str, Any]:
    endpoint = f"{TMDB_BASE}/{kind}/{tmdb_id}"
    data = tmdb_get(endpoint)
    return {
        "tmdb_id": tmdb_id,
        "official_title": data.get("title") or data.get("name"),
        "year": int((data.get("release_date") or data.get("first_air_date") or "0000")[:4]) if (data.get("release_date") or data.get("first_air_date")) else None
    }

def search_and_resolve(title: str, kind: str) -> Dict[str, Any]:
    data = tmdb_get(f"{TMDB_BASE}/search/{kind}", params={"query": title})
    if not data.get("results"):
        raise RuntimeError(f"No TMDB results for {title}")
    r = data["results"][0]
    return {
        "tmdb_id": r["id"],
        "official_title": r.get("title") or r.get("name"),
        "year": int((r.get("release_date") or r.get("first_air_date") or "0000")[:4]) if (r.get("release_date") or r.get("first_air_date")) else None
    }

def parse_entry(line: str, kind: str) -> Dict[str, Any]:
    parts = [p.strip() for p in line.split("|")]
    user_title = parts[0]
    tmdb_id = None
    seasons = "*"
    year = None

    if len(parts) > 1 and parts[1].isdigit():
        tmdb_id = int(parts[1])
    if len(parts) > 2:
        seasons = "*" if parts[2] == "*" else [int(x) for x in re.split(r"[,\s]+", parts[2]) if x.isdigit()]

    if tmdb_id:
        norm = normalize_title_by_id(tmdb_id, kind)
    else:
        norm = search_and_resolve(user_title, kind)

    entry = {
        "tmdb_id": norm["tmdb_id"],
        "official_title": norm["official_title"],
        "user_title": user_title,
        "year": norm["year"],
        "seasons": seasons,
        "active": True,
        "history": [{
            "timestamp_utc": utc_now(),
            "action": "add",
            "changes": {"source": "parse_txt"}
        }]
    }
    if set(entry.keys()) != SCHEMA_KEYS:
        raise RuntimeError("Schema violation")
    return entry

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {"shows": [], "movies": [], "errors": []}

    for fname, kind, target in [
        ("tv_list.txt", "tv", "shows"),
        ("movies_list.txt", "movie", "movies"),
    ]:
        path = os.path.join(INPUT_DIR, fname)
        if not os.path.exists(path):
            continue
        for line in read_lines(path):
            try:
                payload[target].append(parse_entry(line, kind))
            except Exception as e:
                payload["errors"].append({
                    "timestamp_utc": utc_now(),
                    "source": fname,
                    "line": line,
                    "error": str(e)
                })

    atomic_write(OUTPUT_FILE, payload)

if __name__ == "__main__":
    main()
