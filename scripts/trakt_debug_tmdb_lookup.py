#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/trakt_debug_tmdb_lookup.py
# [PROJECT] my_TV_Movie
# [ROLE]    Debug: show exactly what Trakt returns for a TMDB show/movie id
# [VERSION] v1.0.1
# [UPDATED] 2026-01-01
#
# IMPORTANT:
# - This debug tool uses the SAME auth approach as your current fetch_trakt.py:
#   * Public endpoints only
#   * NO OAuth Bearer token
#   * Only "trakt-api-key" (Client ID) + "trakt-api-version"
# - Your earlier 401 happened because an Authorization: Bearer header was sent
#   using API_TRAKT_KEY (which is NOT an access token).
# ==============================================================================

import json
import os
import time
import datetime as _dt
from pathlib import Path
from typing import Any, Dict

import requests


def _utc_ts() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_dirs(repo: Path) -> Dict[str, Path]:
    logs = repo / "logs"
    reports = repo / "reports"
    logs.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    return {"logs": logs, "reports": reports}


def _log_line(fp: Path, msg: str) -> None:
    line = f"{_utc_ts()} | {msg}"
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("a", encoding="utf-8", errors="replace") as f:
        f.write(line + "\n")
    print(line)


def _hdrs_public() -> Dict[str, str]:
    # Use client id ONLY (public endpoints). Do not send Authorization header.
    client_id = os.environ.get("API_TRAKT_ID", "").strip()
    if not client_id:
        raise RuntimeError("Missing API_TRAKT_ID (Trakt Client ID) in environment.")
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": client_id,
    }


def _try_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return None


def _get(url: str, headers: Dict[str, str], logfp: Path) -> Dict[str, Any]:
    _log_line(logfp, f"GET {url}")
    r = requests.get(url, headers=headers, timeout=30)
    _log_line(logfp, f"HTTP {r.status_code}")

    j = _try_json(r)
    if j is None:
        body = (r.text or "")[:5000]
        _log_line(logfp, "WARN: response not JSON; captured first 5k chars to report")
        return {"status": r.status_code, "json": None, "text_head": body}

    return {"status": r.status_code, "json": j}


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main() -> int:
    repo = _repo_root()
    dirs = _ensure_dirs(repo)

    # Your two missing shows (from qa_missing_trakt_ids.py output)
    tmdb_show_ids = [203397, 203755]

    stamp = _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logfp = dirs["logs"] / f"trakt_debug_tmdb_lookup_{stamp}.log.txt"
    outfp = dirs["reports"] / f"_trakt_debug_tmdb_lookup_{stamp}.json"

    _log_line(logfp, f"START repo_root={repo}")
    hdrs = _hdrs_public()
    _log_line(logfp, f"API_TRAKT_ID present (len={len(hdrs['trakt-api-key'])})")
    _log_line(logfp, "Authorization header: NOT USED (public endpoints)")

    results: Dict[str, Any] = {"generated_utc": _utc_ts(), "requests": []}

    # 1) Primary: lookup by external id (TMDB) for SHOW
    for tid in tmdb_show_ids:
        url = f"https://api.trakt.tv/search/tmdb/{tid}?type=show"
        res = _get(url, hdrs, logfp)
        results["requests"].append(
            {"tmdb_id": tid, "type": "show", "endpoint": "search/tmdb", "result": res}
        )
        time.sleep(0.25)

    # 2) Fallback: title search (to see if show exists under a different external mapping)
    data_path = repo / "data" / "data.json"
    if data_path.exists():
        with data_path.open("r", encoding="utf-8", errors="replace") as f:
            d = json.load(f)
        shows = d.get("shows", []) or []
        tmdb_to_title = {}
        for s in shows:
            try:
                tmdb_to_title[int(str(s.get("tmdb_id")).strip())] = (s.get("title") or "").strip()
            except Exception:
                continue

        for tid in tmdb_show_ids:
            title = tmdb_to_title.get(tid, "")
            if title:
                q = requests.utils.quote(title)
                url = f"https://api.trakt.tv/search/show?query={q}&limit=10"
                res = _get(url, hdrs, logfp)
                results["requests"].append(
                    {
                        "tmdb_id": tid,
                        "type": "show",
                        "endpoint": "search/show?query=title",
                        "title": title,
                        "result": res,
                    }
                )
                time.sleep(0.25)

    _save_json(outfp, results)
    _log_line(logfp, f"WROTE report={outfp}")
    _log_line(logfp, "DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
