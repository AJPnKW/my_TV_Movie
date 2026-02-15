#!/usr/bin/env python3
# =============================================================================
# export_inputs_tmdb_decisions.py
# Version: 0.1.0
#
# Purpose:
#   Export a TAB-delimited report (TSV) to review/decide fixes for inputs.json:
#     - Reads data/inputs.json
#     - For each item:
#         A) Probes TMDB by ID on BOTH endpoints: /movie/{id} and /tv/{id}
#         B) Searches TMDB by NAME on BOTH endpoints: /search/movie and /search/tv
#     - Writes a TSV you can edit to record decisions, then apply with:
#         scripts/apply_inputs_tmdb_decisions.py
#
# Auth (uses your existing env vars):
#   - API_TMDB_TOKEN (TMDB v4 Read token)  [preferred]
#   - API_TMDB_KEY   (TMDB v3 API key)     [fallback]
#
# Output:
#   - _inputs_tmdb_decisions.tsv
#   - _inputs_tmdb_decisions.tsv.log.txt
#
# Usage (repo root):
#   python .\scripts\export_inputs_tmdb_decisions.py
#
# Decisions (you fill in TSV):
#   DECISION: one of
#     - KEEP
#     - FIX_ID
#     - MOVE_BUCKET
#     - FIX_ID_AND_BUCKET
#     - DELETE
#   NEW_BUCKET: movie|tv   (only if moving)
#   NEW_TMDB_ID: integer   (only if changing ID)
#   NOTES: free text
# =============================================================================

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

SCRIPT = "export_inputs_tmdb_decisions.py"
VERSION = "0.1.0"

REPO_ROOT = Path.cwd()
INPUTS_PATH = REPO_ROOT / "data" / "inputs.json"
OUT_TSV = REPO_ROOT / "_inputs_tmdb_decisions.tsv"
LOG_PATH = OUT_TSV.with_suffix(OUT_TSV.suffix + ".log.txt")

TMDB_BASE = "https://api.themoviedb.org/3"
LANG = "en-US"

V4 = os.getenv("API_TMDB_TOKEN", "").strip()
V3 = os.getenv("API_TMDB_KEY", "").strip()

if not V4 and not V3:
    print("ERROR: Missing TMDB auth. Set API_TMDB_TOKEN or API_TMDB_KEY.", file=sys.stderr)
    raise SystemExit(3)


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def _as_list(x: Any) -> List[Dict[str, Any]]:
    return x if isinstance(x, list) else []


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[\s\-_]+", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    return s.strip()


def token_overlap_score(a: str, b: str) -> float:
    a2, b2 = norm(a), norm(b)
    if not a2 or not b2:
        return 0.0
    if a2 == b2:
        return 1.0
    if a2 in b2 or b2 in a2:
        return 0.92
    ta, tb = set(a2.split()), set(b2.split())
    return len(ta & tb) / max(1, len(ta | tb))


def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 20) -> Tuple[int, Optional[Dict[str, Any]]]:
    url = f"{TMDB_BASE}/{path.lstrip('/')}"
    p = dict(params or {})
    p["language"] = LANG

    headers: Dict[str, str] = {}
    if V4:
        headers["Authorization"] = f"Bearer {V4}"
    else:
        p["api_key"] = V3

    try:
        r = requests.get(url, headers=headers, params=p, timeout=timeout)
        if r.status_code != 200:
            return r.status_code, None
        return r.status_code, r.json()
    except Exception:
        return 0, None


def probe_id(tmdb_id: int) -> Dict[str, Any]:
    m_code, m_json = tmdb_get(f"movie/{tmdb_id}")
    t_code, t_json = tmdb_get(f"tv/{tmdb_id}")

    m_title = ""
    t_title = ""
    if isinstance(m_json, dict):
        m_title = str(m_json.get("title") or m_json.get("original_title") or "").strip()
    if isinstance(t_json, dict):
        t_title = str(t_json.get("name") or t_json.get("original_name") or "").strip()

    return {
        "movie_status": m_code,
        "tv_status": t_code,
        "movie_title": m_title,
        "tv_title": t_title,
    }


def search_best(kind: str, query: str) -> Dict[str, Any]:
    endpoint = "search/movie" if kind == "movie" else "search/tv"
    code, data = tmdb_get(endpoint, params={"query": query, "include_adult": "false"})
    if code != 200 or not isinstance(data, dict):
        return {"status": code, "id": "", "title": "", "score": ""}

    results = data.get("results") or []
    if not isinstance(results, list) or not results:
        return {"status": code, "id": "", "title": "", "score": ""}

    best_id: Any = ""
    best_title = ""
    best_score = 0.0

    for r in results[:10]:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        title = str(r.get("title") if kind == "movie" else r.get("name") or "").strip()
        if not isinstance(rid, int) or not title:
            continue
        score = token_overlap_score(query, title)
        if score > best_score:
            best_score = score
            best_id = rid
            best_title = title

    return {"status": code, "id": best_id, "title": best_title, "score": f"{best_score:.4f}" if best_id != "" else ""}


def iter_items(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add(group: str, bucket: str, items: List[Dict[str, Any]]) -> None:
        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            out.append({
                "group": group,
                "bucket": bucket,  # movie|tv|unknown
                "index": idx,
                "slug": str(it.get("slug", "")).strip(),
                "title": str(it.get("title", "")).strip(),
                "tmdb_id": it.get("tmdb_id"),
            })

    add("movies", "movie", _as_list(doc.get("movies")))
    add("tv", "tv", _as_list(doc.get("tv")))

    w = doc.get("watchlist")
    if isinstance(w, dict):
        add("watchlist.movies", "movie", _as_list(w.get("movies")))
        add("watchlist.tv", "tv", _as_list(w.get("tv")))
    elif isinstance(w, list):
        add("watchlist", "unknown", _as_list(w))

    return out


def tsv_escape(s: Any) -> str:
    # TSV-safe single field; replace tabs/newlines
    s2 = "" if s is None else str(s)
    return s2.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def main() -> int:
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    log(f"{SCRIPT} v{VERSION} start")
    log(f"inputs={INPUTS_PATH}")
    log(f"auth={'V4' if V4 else 'V3'}")

    if not INPUTS_PATH.exists():
        print(f"ERROR: Not found: {INPUTS_PATH}", file=sys.stderr)
        log("ERROR inputs.json not found")
        return 2

    doc = load_json(INPUTS_PATH)
    if not isinstance(doc, dict):
        print("ERROR: inputs.json root must be an object", file=sys.stderr)
        log("ERROR inputs.json invalid root")
        return 2

    rows = iter_items(doc)
    total = len(rows)

    cache_probe: Dict[int, Dict[str, Any]] = {}
    cache_search_movie: Dict[str, Dict[str, Any]] = {}
    cache_search_tv: Dict[str, Dict[str, Any]] = {}

    headers = [
        "GROUP",
        "BUCKET",
        "INDEX",
        "SLUG",
        "LOCAL_TITLE",
        "LOCAL_TMDB_ID",
        "PROBE_MOVIE_STATUS",
        "PROBE_TV_STATUS",
        "PROBE_MOVIE_TITLE",
        "PROBE_TV_TITLE",
        "SEARCH_MOVIE_STATUS",
        "SEARCH_MOVIE_ID",
        "SEARCH_MOVIE_TITLE",
        "SEARCH_MOVIE_SCORE",
        "SEARCH_TV_STATUS",
        "SEARCH_TV_ID",
        "SEARCH_TV_TITLE",
        "SEARCH_TV_SCORE",
        # you fill these:
        "DECISION",
        "NEW_BUCKET",
        "NEW_TMDB_ID",
        "NOTES",
    ]

    tmp = OUT_TSV.with_suffix(OUT_TSV.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(headers) + "\n")

        for i, r in enumerate(rows, start=1):
            local_title = r["title"]
            local_id_raw = r["tmdb_id"]

            try:
                local_id = int(local_id_raw)
            except Exception:
                local_id = -1

            if local_id > 0 and local_id not in cache_probe:
                cache_probe[local_id] = probe_id(local_id)

            pr = cache_probe.get(local_id, {"movie_status": "", "tv_status": "", "movie_title": "", "tv_title": ""})

            key = norm(local_title)
            if key and key not in cache_search_movie:
                cache_search_movie[key] = search_best("movie", local_title)
            if key and key not in cache_search_tv:
                cache_search_tv[key] = search_best("tv", local_title)

            sm = cache_search_movie.get(key, {"status": "", "id": "", "title": "", "score": ""})
            st = cache_search_tv.get(key, {"status": "", "id": "", "title": "", "score": ""})

            line = [
                r["group"],
                r["bucket"],
                r["index"],
                tsv_escape(r["slug"]),
                tsv_escape(local_title),
                tsv_escape(local_id_raw),
                tsv_escape(pr.get("movie_status")),
                tsv_escape(pr.get("tv_status")),
                tsv_escape(pr.get("movie_title")),
                tsv_escape(pr.get("tv_title")),
                tsv_escape(sm.get("status")),
                tsv_escape(sm.get("id")),
                tsv_escape(sm.get("title")),
                tsv_escape(sm.get("score")),
                tsv_escape(st.get("status")),
                tsv_escape(st.get("id")),
                tsv_escape(st.get("title")),
                tsv_escape(st.get("score")),
                "",  # DECISION
                "",  # NEW_BUCKET
                "",  # NEW_TMDB_ID
                "",  # NOTES
            ]
            f.write("\t".join(tsv_escape(x) for x in line) + "\n")

            if i == 1 or i == total or (i % 50) == 0:
                print(f"[{i}/{total}] exporting...", end="\r", flush=True)

    print(" " * 80, end="\r")
    tmp.replace(OUT_TSV)

    log(f"wrote={OUT_TSV}")
    print(f"Wrote: {OUT_TSV}")
    print(f"Log:   {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
