# [CAPABILITY] my_tv_movie_asset_repair=YES
# version: 1.0
# purpose: download missing local poster/backdrop/still assets referenced by data/data.json

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_REPO_ROOT = Path(r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
IMAGE_BASE = "https://image.tmdb.org/t/p/original"

LOCAL_KEYS = {
    "poster": ["poster_local", "poster"],
    "backdrop": ["backdrop_local", "backdrop"],
    "still": ["still_local", "still"],
}
REMOTE_KEYS = {
    "poster": ["poster_path"],
    "backdrop": ["backdrop_path"],
    "still": ["still_path"],
}

def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def normalize_local_path(val: Any) -> str | None:
    if not isinstance(val, str):
        return None
    txt = val.strip().replace("\\", "/").lstrip("./")
    if not txt or not txt.startswith("assets/"):
        return None
    return txt

def first_string(obj: dict[str, Any], keys: list[str]) -> str:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def download_to(url: str, dest: Path, timeout: int = 30) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read()
        if not data:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False

def entity_desc(entity_type: str, obj: dict[str, Any], show_title: str = "", season_number: Any = None, episode_number: Any = None) -> str:
    parts = [entity_type]
    title = obj.get("title") or obj.get("name") or ""
    tmdb_id = obj.get("tmdb_id") or obj.get("id") or ""
    if show_title:
        parts.append(f"show={show_title}")
    if title:
        parts.append(f"title={title}")
    if season_number is not None:
        parts.append(f"season={season_number}")
    if episode_number is not None:
        parts.append(f"episode={episode_number}")
    if tmdb_id:
        parts.append(f"tmdb_id={tmdb_id}")
    return " | ".join(parts)

def process_asset(obj: dict[str, Any], asset_type: str, repo_root: Path, entity_type: str, show_title: str = "", season_number: Any = None, episode_number: Any = None) -> dict[str, Any] | None:
    local_ref = normalize_local_path(first_string(obj, LOCAL_KEYS[asset_type]))
    remote_ref = first_string(obj, REMOTE_KEYS[asset_type])
    if not local_ref:
        return None

    abs_path = repo_root / local_ref.replace("/", os.sep)
    exists = abs_path.exists()
    result = {
        "entity_type": entity_type,
        "title": obj.get("title") or obj.get("name") or "",
        "show_title": show_title,
        "season_number": season_number,
        "episode_number": episode_number,
        "tmdb_id": obj.get("tmdb_id") or obj.get("id") or "",
        "asset_type": asset_type,
        "local_path": local_ref,
        "remote_path": remote_ref,
        "status": "matched" if exists else "missing",
        "detail": "",
    }
    if exists:
        return result

    if isinstance(remote_ref, str) and remote_ref.strip().startswith("/"):
        ok = download_to(f"{IMAGE_BASE}{remote_ref.strip()}", abs_path)
        result["status"] = "downloaded" if ok else "failed_download"
        result["detail"] = "download attempted from TMDB image base"
        return result

    result["status"] = "missing_no_remote"
    result["detail"] = "no remote *_path present to repair local asset"
    return result

def process_show(show: dict[str, Any], repo_root: Path, rows: list[dict[str, Any]]) -> None:
    show_title = show.get("title") or show.get("name") or ""
    for asset_type in ("poster", "backdrop"):
        row = process_asset(show, asset_type, repo_root, "show", show_title=show_title)
        if row:
            rows.append(row)

    for season in show.get("seasons", []) or []:
        season_number = season.get("season_number") or season.get("number")
        for asset_type in ("poster", "backdrop"):
            row = process_asset(season, asset_type, repo_root, "season", show_title=show_title, season_number=season_number)
            if row:
                rows.append(row)

        for ep in season.get("episodes", []) or []:
            episode_number = ep.get("episode_number") or ep.get("number")
            row = process_asset(ep, "still", repo_root, "episode", show_title=show_title, season_number=season_number, episode_number=episode_number)
            if row:
                rows.append(row)

def process_movie(movie: dict[str, Any], repo_root: Path, rows: list[dict[str, Any]]) -> None:
    for asset_type in ("poster", "backdrop"):
        row = process_asset(movie, asset_type, repo_root, "movie")
        if row:
            rows.append(row)

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    import csv
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--no-pause", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    data_path = repo_root / "data" / "data.json"
    if not data_path.exists():
        print(f"ERROR: data.json not found: {data_path}")
        return 1

    data = load_json(data_path)
    rows: list[dict[str, Any]] = []

    for show in data.get("shows", []) or []:
        process_show(show, repo_root, rows)
    for movie in data.get("movies", []) or []:
        process_movie(movie, repo_root, rows)

    counts = Counter(r["status"] for r in rows)
    by_type = Counter((r["asset_type"], r["status"]) for r in rows)

    ts = now_stamp()
    out_dir = repo_root / "logs" / f"asset_repair_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_json(out_dir / "asset_repair_results.json", rows)
    write_csv(out_dir / "asset_repair_results.csv", rows)

    summary = {
        "repo_root": str(repo_root),
        "checked_rows": len(rows),
        "status_counts": dict(counts),
        "by_type_status": {f"{k[0]}::{k[1]}": v for k, v in by_type.items()},
    }
    write_json(out_dir / "summary.json", summary)

    lines = []
    lines.append("ASSET REPAIR SUMMARY")
    lines.append("--------------------")
    lines.append(f"Checked asset refs: {len(rows)}")
    for status in ("matched", "downloaded", "failed_download", "missing_no_remote"):
        lines.append(f"{status}: {counts.get(status, 0)}")
    lines.append("")
    lines.append("By type/status")
    for asset_type in ("poster", "backdrop", "still"):
        for status in ("matched", "downloaded", "failed_download", "missing_no_remote"):
            lines.append(f"  {asset_type:<8} {status:<16} {by_type.get((asset_type, status), 0)}")
    summary_txt = "\n".join(lines)
    (out_dir / "summary.txt").write_text(summary_txt, encoding="utf-8")

    print(summary_txt)
    print("")
    print(f"Detailed report folder: {out_dir}")
    if not args.no_pause:
        input("Press ENTER to exit...")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
