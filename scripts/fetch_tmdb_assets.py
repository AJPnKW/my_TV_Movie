from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import socket
import ssl
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
DEFAULT_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_local_path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip().replace("\\", "/").lstrip("./")
    if text.startswith("/"):
        text = text[1:]
    return text if text.startswith("assets/") else ""


def normalize_remote_path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    return text if text.startswith("/") else ""


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_asset_refs(data: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []

    def add_ref(entity: str, title: str, asset_type: str, local_key: str, remote_key: str, obj: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
      local_path = normalize_local_path(obj.get(local_key))
      remote_path = normalize_remote_path(obj.get(remote_key))
      if not local_path or not remote_path:
          return
      refs.append({
          "entity": entity,
          "title": title,
          "asset_type": asset_type,
          "local_path": local_path,
          "remote_path": remote_path,
          **(extra or {}),
      })

    for show in data.get("shows", []) or []:
        show_title = str(show.get("title") or show.get("name") or "")
        add_ref("show", show_title, "poster", "poster_local", "poster_path", show, {"tmdb_id": show.get("tmdb_id")})
        add_ref("show", show_title, "backdrop", "backdrop_local", "backdrop_path", show, {"tmdb_id": show.get("tmdb_id")})
        for season in show.get("seasons", []) or []:
            season_number = season.get("season_number") or season.get("number")
            add_ref("season", show_title, "poster", "poster_local", "poster_path", season, {
                "tmdb_id": show.get("tmdb_id"),
                "season_number": season_number,
            })
            add_ref("season", show_title, "backdrop", "backdrop_local", "backdrop_path", season, {
                "tmdb_id": show.get("tmdb_id"),
                "season_number": season_number,
            })
            for episode in season.get("episodes", []) or []:
                add_ref("episode", show_title, "still", "still_local", "still_path", episode, {
                    "tmdb_id": show.get("tmdb_id"),
                    "season_number": season_number,
                    "episode_number": episode.get("episode_number") or episode.get("number"),
                })

    for movie in data.get("movies", []) or []:
        movie_title = str(movie.get("title") or movie.get("name") or "")
        add_ref("movie", movie_title, "poster", "poster_local", "poster_path", movie, {"tmdb_id": movie.get("tmdb_id")})
        add_ref("movie", movie_title, "backdrop", "backdrop_local", "backdrop_path", movie, {"tmdb_id": movie.get("tmdb_id")})

    # Unique by local target so repeated refs do not redownload.
    deduped: dict[str, dict[str, Any]] = {}
    for ref in refs:
        deduped.setdefault(ref["local_path"], ref)
    return list(deduped.values())


def download_asset(image_base: str, repo_root: Path, ref: dict[str, Any], timeout: int, retries: int) -> dict[str, Any]:
    local_path = repo_root / ref["local_path"]
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if local_path.exists():
        return {**ref, "status": "matched", "bytes": local_path.stat().st_size, "sha1": sha1_file(local_path)}

    url = f"{image_base.rstrip('/')}{ref['remote_path']}"
    request = urllib.request.Request(url, headers={"User-Agent": "my_TV_Movie-asset-fetch/1.0"})
    context = ssl.create_default_context()
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                content = response.read()
            if not content:
                last_error = "empty response"
                continue
            local_path.write_bytes(content)
            return {
                **ref,
                "status": "downloaded",
                "bytes": len(content),
                "sha1": sha1_file(local_path),
                "source_url": url,
            }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, ssl.SSLError) as exc:  # type: ignore[attr-defined]
            last_error = str(exc)
    return {**ref, "status": "failed", "error": last_error, "source_url": url}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-json", default=str(DATA_JSON))
    parser.add_argument("--image-base", default=DEFAULT_IMAGE_BASE)
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    data_json = Path(args.data_json).resolve()
    if not data_json.exists():
        print(f"ERROR: missing data file {data_json}")
        return 1

    data = load_json(data_json)
    refs = iter_asset_refs(data)
    print("[START] fetch_tmdb_assets")
    print(f"[INFO] unique referenced assets with remote paths: {len(refs)}")

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futures = [pool.submit(download_asset, args.image_base, repo_root, ref, args.timeout, args.retries) for ref in refs]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item["local_path"])
    counts = Counter(item["status"] for item in results)
    by_type = Counter((item["asset_type"], item["status"]) for item in results)

    out_dir = repo_root / "logs" / f"asset_fetch_{now_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "asset_fetch_results.json", results)
    write_json(out_dir / "summary.json", {
        "data_json": str(data_json),
        "total": len(results),
        "status_counts": dict(counts),
        "by_type_status": {f"{asset_type}::{status}": value for (asset_type, status), value in by_type.items()},
    })

    print(f"[DONE] assets checked={len(results)} matched={counts.get('matched', 0)} downloaded={counts.get('downloaded', 0)} failed={counts.get('failed', 0)}")
    print(f"[LOG] {out_dir}")
    return 1 if counts.get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
