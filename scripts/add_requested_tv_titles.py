#!/usr/bin/env python3
"""Resolve queued TV titles through TMDB and merge verified matches into data/inputs.json."""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "requested_tv_titles.json"
INPUTS = ROOT / "data" / "inputs.json"
REPORT = ROOT / "data" / "requested_tv_lookup_report.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def tmdb_search(api_key: str, title: str, year: int | None):
    params = {"api_key": api_key, "query": title, "include_adult": "false"}
    if year:
        params["first_air_date_year"] = str(year)
    url = "https://api.themoviedb.org/3/search/tv?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "my_TV_Movie/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response).get("results", [])


def norm(value: str) -> str:
    return " ".join(str(value or "").casefold().replace("’", "'").split())


def choose_match(results, title: str, year: int | None):
    wanted = norm(title)
    exact = [r for r in results if norm(r.get("name")) == wanted or norm(r.get("original_name")) == wanted]
    candidates = exact or results
    if year:
        same_year = [r for r in candidates if str(r.get("first_air_date", ""))[:4] == str(year)]
        if same_year:
            candidates = same_year
    if not candidates:
        return None
    candidates.sort(key=lambda r: (float(r.get("popularity") or 0), int(r.get("vote_count") or 0)), reverse=True)
    best = candidates[0]
    if norm(best.get("name")) != wanted and norm(best.get("original_name")) != wanted:
        return None
    if year and str(best.get("first_air_date", ""))[:4] not in {"", str(year)}:
        return None
    return best


def main() -> int:
    api_key = os.getenv("API_TMDB_KEY", "").strip()
    if not api_key:
        print("ERROR: API_TMDB_KEY is not configured")
        return 2

    queue = load_json(QUEUE)
    inputs = load_json(INPUTS)
    tv = inputs.setdefault("tv", [])
    existing_ids = {int(x.get("tmdb_id")) for x in tv if str(x.get("tmdb_id", "")).isdigit()}
    existing_titles = {norm(x.get("title")) for x in tv}

    added = []
    existing = []
    unresolved = []

    for request in queue.get("titles", []):
        title = str(request.get("title") or "").strip()
        year = request.get("year")
        if not title:
            continue
        try:
            results = tmdb_search(api_key, title, year)
            match = choose_match(results, title, year)
        except Exception as exc:  # noqa: BLE001
            unresolved.append({**request, "reason": f"TMDB lookup failed: {exc}"})
            continue
        if not match:
            unresolved.append({**request, "reason": "No exact TMDB TV match for requested title/year"})
            continue
        tmdb_id = int(match["id"])
        canonical_title = str(match.get("name") or title)
        record = {
            "tmdb_id": tmdb_id,
            "title": canonical_title,
            "in_scope": True,
            "season_spec": "*",
            "tags": [],
            "include_future": True,
            "notes": str(request.get("notes") or ""),
        }
        if tmdb_id in existing_ids or norm(canonical_title) in existing_titles:
            existing.append({"requested_title": title, "tmdb_id": tmdb_id, "title": canonical_title})
            continue
        tv.append(record)
        existing_ids.add(tmdb_id)
        existing_titles.add(norm(canonical_title))
        added.append({"requested_title": title, "tmdb_id": tmdb_id, "title": canonical_title, "first_air_date": match.get("first_air_date", "")})

    tv.sort(key=lambda item: norm(item.get("title")))
    write_json(INPUTS, inputs)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "requested": len(queue.get("titles", [])),
        "added_count": len(added),
        "existing_count": len(existing),
        "unresolved_count": len(unresolved),
        "added": added,
        "already_present": existing,
        "unresolved": unresolved,
    }
    write_json(REPORT, report)
    print(json.dumps(report, indent=2))
    return 0 if not unresolved else 3


if __name__ == "__main__":
    sys.exit(main())
