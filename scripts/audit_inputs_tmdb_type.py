#!/usr/bin/env python3
# =============================================================================
# audit_inputs_tmdb_type.py
# Version: 0.1.1
# Purpose:
#   Deterministically validate whether each TMDB ID in inputs.json is a MOVIE or TV
#   by querying TMDB's API for BOTH endpoints:
#     - /3/movie/{id}
#     - /3/tv/{id}
#   Then flag active rows for:
#     - items stored in the wrong list (movies vs tv vs watchlist)
#     - title mismatches (stored title vs TMDB title/name)
#     - active IDs that do not resolve on the expected TMDB endpoint
#
# Requirements:
#   - Python 3.10+ (tested with 3.12)
#   - requests
#
# Auth (pick ONE) — uses your existing env vars:
#   A) TMDB v4 Read Access Token (recommended):
#        setx API_TMDB_TOKEN "eyJhbGciOi..."
#   B) TMDB v3 API Key:
#        setx API_TMDB_KEY "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#
# Usage (PowerShell):
#   python .\audit_inputs_tmdb_type.py --inputs .\inputs.json --out .\_audit_tmdb_type.json
#
# Exit codes:
#   0 = OK (no active blocking issues)
#   2 = Active misfiled, unresolved, or title-mismatch items found
#   3 = Auth missing
#   4 = Network/API failure
#
# =============================================================================

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


TMDB_BASE = "https://api.themoviedb.org/3"


@dataclass(frozen=True)
class TmdbHit:
    kind: str  # "movie" | "tv"
    tmdb_id: int
    title: str
    status_code: int


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _title_close(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # containment check catches subtitles/years/punctuation differences
    if (na in nb) or (nb in na):
        return True
    stop = {"a", "an", "and", "in", "of", "part", "the", "to", "with"}
    tokens_a = {token for token in na.split(" ") if token and token not in stop and not token.isdigit()}
    tokens_b = {token for token in nb.split(" ") if token and token not in stop and not token.isdigit()}
    if not tokens_a or not tokens_b:
        return False
    overlap = tokens_a & tokens_b
    return len(overlap) >= min(len(tokens_a), len(tokens_b))


def _auth_headers_and_params() -> Tuple[Dict[str, str], Dict[str, str]]:
    # Updated to use user's existing env vars:
    v4 = os.environ.get("API_TMDB_TOKEN", "").strip()
    v3 = os.environ.get("API_TMDB_KEY", "").strip()

    if v4:
        return ({"Authorization": f"Bearer {v4}"}, {"language": "en-US"})
    if v3:
        return ({}, {"api_key": v3, "language": "en-US"})

    return ({}, {})


def _get_json(
    url: str,
    headers: Dict[str, str],
    params: Dict[str, str],
    timeout: int = 20
) -> Tuple[int, Optional[Dict[str, Any]]]:
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        if r.status_code != 200:
            return (r.status_code, None)
        return (r.status_code, r.json())
    except Exception:
        return (0, None)


def tmdb_probe(tmdb_id: int, headers: Dict[str, str], params: Dict[str, str]) -> Tuple[TmdbHit, TmdbHit]:
    movie_url = f"{TMDB_BASE}/movie/{tmdb_id}"
    tv_url = f"{TMDB_BASE}/tv/{tmdb_id}"

    m_code, m_json = _get_json(movie_url, headers, params)
    t_code, t_json = _get_json(tv_url, headers, params)

    movie_title = str(m_json.get("title", "")).strip() if isinstance(m_json, dict) else ""
    tv_title = str(t_json.get("name", "")).strip() if isinstance(t_json, dict) else ""

    movie_hit = TmdbHit("movie", tmdb_id, movie_title, m_code)
    tv_hit = TmdbHit("tv", tmdb_id, tv_title, t_code)
    return (movie_hit, tv_hit)


def load_inputs(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="Path to inputs.json")
    ap.add_argument("--out", required=True, help="Path to write audit JSON output")
    ap.add_argument("--sleep-ms", type=int, default=120, help="Delay between TMDB calls (rate-limit friendly)")
    ap.add_argument("--include-inactive", action="store_true", help="Also audit rows where in_scope is false")
    args = ap.parse_args()

    headers, params = _auth_headers_and_params()
    if not headers and "api_key" not in params:
        print("ERROR: Missing TMDB auth. Set API_TMDB_TOKEN or API_TMDB_KEY.", file=sys.stderr)
        return 3

    doc = load_inputs(args.inputs)

    # Support both watchlist shapes:
    # 1) list:  "watchlist": [ ... ]
    # 2) dict:  "watchlist": { "movies": [...], "tv": [...] }
    watchlist = doc.get("watchlist", [])
    watchlist_groups: List[Tuple[str, List[Dict[str, Any]], str]] = []

    if isinstance(watchlist, dict):
        watchlist_groups = [
            ("watchlist.movies", _as_list(watchlist.get("movies")), "movie"),
            ("watchlist.tv", _as_list(watchlist.get("tv")), "tv"),
        ]
    else:
        watchlist_groups = [
            ("watchlist", _as_list(watchlist), "unknown"),
        ]

    groups: List[Tuple[str, List[Dict[str, Any]], str]] = [
        ("movies", _as_list(doc.get("movies", [])), "movie"),
        ("tv", _as_list(doc.get("tv", [])), "tv"),
        *watchlist_groups,
    ]

    misfiled: List[Dict[str, Any]] = []
    title_mismatch: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    skipped_inactive: List[Dict[str, Any]] = []

    total = sum(len(lst) for _, lst, _ in groups)
    audited = 0

    idx = 0
    for group_name, items, expected in groups:
        for item in items:
            idx += 1
            if isinstance(item, dict) and item.get("in_scope") is False and not args.include_inactive:
                skipped_inactive.append({
                    "group": group_name,
                    "tmdb_id": item.get("tmdb_id"),
                    "local_title": str(item.get("title", "")).strip(),
                })
                continue
            audited += 1

            tmdb_raw = item.get("tmdb_id")
            try:
                tmdb_id = int(tmdb_raw)
            except Exception:
                unresolved.append({
                    "group": group_name,
                    "tmdb_id": tmdb_raw,
                    "local_title": str(item.get("title", "")).strip(),
                    "movie_status": 0,
                    "tv_status": 0,
                })
                continue

            local_title = str(item.get("title", "")).strip()

            movie_hit, tv_hit = tmdb_probe(tmdb_id, headers, params)

            # Determine actual kind:
            # - If one endpoint 200 and the other not 200 => definitive
            # - If both 200 => ambiguous (flag)
            # - If neither 200 => unresolved (flag)
            actual: str = "unresolved"
            tmdb_title: str = ""

            expected_hit = movie_hit if expected == "movie" else tv_hit if expected == "tv" else None
            other_hit = tv_hit if expected == "movie" else movie_hit if expected == "tv" else None

            if expected_hit and expected_hit.status_code == 200:
                actual = expected
                tmdb_title = expected_hit.title
            elif expected_hit and other_hit and expected_hit.status_code != 200 and other_hit.status_code == 200:
                actual = other_hit.kind
                tmdb_title = other_hit.title
            elif movie_hit.status_code == 200 and tv_hit.status_code != 200:
                actual = "movie"
                tmdb_title = movie_hit.title
            elif tv_hit.status_code == 200 and movie_hit.status_code != 200:
                actual = "tv"
                tmdb_title = tv_hit.title
            elif tv_hit.status_code == 200 and movie_hit.status_code == 200:
                actual = "ambiguous"
                tmdb_title = tv_hit.title or movie_hit.title
            else:
                actual = "unresolved"

            if actual in ("unresolved", "ambiguous"):
                unresolved.append({
                    "group": group_name,
                    "tmdb_id": tmdb_id,
                    "local_title": local_title,
                    "movie_status": movie_hit.status_code,
                    "tv_status": tv_hit.status_code,
                })
            else:
                # misfiled (only when group has a known expected type)
                if expected in ("movie", "tv") and actual != expected:
                    misfiled.append({
                        "group": group_name,
                        "expected": expected,
                        "actual": actual,
                        "tmdb_id": tmdb_id,
                        "local_title": local_title,
                        "tmdb_title": tmdb_title,
                    })

                # title mismatch (only when actual resolved)
                if local_title and tmdb_title and not _title_close(local_title, tmdb_title):
                    title_mismatch.append({
                        "group": group_name,
                        "actual": actual,
                        "tmdb_id": tmdb_id,
                        "local_title": local_title,
                        "tmdb_title": tmdb_title,
                    })

            if args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000.0)

            # minimal console progress (single line)
            print(f"[{idx}/{total}] {group_name} {tmdb_id}", end="\r", flush=True)

    print(" " * 80, end="\r")

    out = {
        "inputs_path": os.path.abspath(args.inputs),
        "misfiled": misfiled,
        "title_mismatch": title_mismatch,
        "unresolved_or_ambiguous": unresolved,
        "skipped_inactive": skipped_inactive,
        "summary": {
            "total_items": total,
            "audited_items": audited,
            "skipped_inactive_count": len(skipped_inactive),
            "misfiled_count": len(misfiled),
            "title_mismatch_count": len(title_mismatch),
            "unresolved_or_ambiguous_count": len(unresolved),
        },
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if misfiled or title_mismatch or unresolved:
        print(
            f"FAIL: misfiled={len(misfiled)} title_mismatch={len(title_mismatch)} "
            f"unresolved_or_ambiguous={len(unresolved)} (see {args.out})"
        )
        return 2

    print(f"OK: no active TMDB identity issues (see {args.out})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
