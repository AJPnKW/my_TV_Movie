#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/download_tmdb_assets.py
# [PROJECT] my_TV_Movie
# [ROLE]    Download missing TMDB images referenced by data/data.json into the
#           canonical repo assets folders defined by web/config.json.
# [VERSION] v1.0.0
# [UPDATED] 2026-01-13
# [BUILD]   14.01.13
#
# Inputs:
#   - web/config.json   (image_cache.tmdb_image_base, image_cache.folders, image_sizes)
#   - data/data.json    (poster_path/backdrop_path/still_path + *_local)
#
# Output:
#   - Downloads files into the repo under assets/** (mapped from config folders)
#   - logs/download_tmdb_assets.YYYYMMDD_HHMMSS.log.txt
#
# Notes:
# - Does NOT require git commit. If run inside GitHub Actions before Pages deploy,
#   the downloaded assets will be included in the Pages artifact.
# - Uses download_missing_only semantics: skips existing files.
# ==============================================================================
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception as ex:
    raise SystemExit("Missing dependency: requests. Run: python -m pip install -r requirements.txt") from ex

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
WEB_CONFIG = REPO_ROOT / "web" / "config.json"
DATA_JSON = REPO_ROOT / "data" / "data.json"
LOG_DIR = REPO_ROOT / "logs"

DEFAULT_TIMEOUT = 45
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.8

def _utc_ts() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def _stamp() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y%m%d_%H%M%S")

def _setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lp = LOG_DIR / f"download_tmdb_assets.{_stamp()}.log.txt"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(lp, encoding="utf-8")],
    )
    logging.info("[init] repo_root=%s", REPO_ROOT)
    logging.info("[init] log=%s", lp)
    return lp

def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))

def _ensure_leading_slash(s: str) -> str:
    s = (s or "").replace("\\", "/").strip().strip("/")
    if not s:
        return ""
    return "/" + s

def _tmdb_size_tag(kind: str, sizes_cfg: Dict[str, Any]) -> str:
    width_map = {
        "show_poster": sizes_cfg.get("show_width"),
        "movie_poster": sizes_cfg.get("movie_width"),
        "season_poster": sizes_cfg.get("season_width"),
        "episode_still": sizes_cfg.get("episode_still_w"),
        "backdrop": sizes_cfg.get("backdrop_w"),
    }
    w = width_map.get(kind)
    try:
        w = int(w)
    except Exception:
        w = None
    return f"w{w}" if w else "original"

def _tmdb_url(base: str, size_tag: str, tmdb_path: str) -> str:
    base = (base or "").rstrip("/")
    tmdb_path = (tmdb_path or "").strip()
    if not tmdb_path.startswith("/"):
        tmdb_path = "/" + tmdb_path
    return f"{base}/{size_tag}{tmdb_path}"

def _local_fs_path_from_site_path(site_path: str) -> Path:
    rel = site_path.lstrip("/").replace("/", os.sep)
    return REPO_ROOT / rel

def _download(url: str, dst: Path) -> Tuple[bool, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last = ""
    for attempt in range(1, DEFAULT_RETRIES + 1):
        try:
            r = requests.get(url, timeout=DEFAULT_TIMEOUT)
            if r.status_code == 200 and r.content:
                dst.write_bytes(r.content)
                return True, ""
            last = f"status={r.status_code}"
        except Exception as ex:
            last = str(ex)
        time.sleep(DEFAULT_BACKOFF * attempt)
    return False, last

def main() -> int:
    _setup_logging()

    if not WEB_CONFIG.exists():
        logging.error("Missing required file: %s", WEB_CONFIG)
        return 2
    if not DATA_JSON.exists():
        logging.error("Missing required file: %s", DATA_JSON)
        return 2

    cfg = _read_json(WEB_CONFIG)
    data = _read_json(DATA_JSON)

    image_cache = cfg.get("image_cache") or {}
    if not image_cache.get("enabled", True):
        logging.info("[skip] image_cache.enabled=false")
        return 0

    tmdb_base = str(image_cache.get("tmdb_image_base") or "https://image.tmdb.org/t/p").rstrip("/")
    folders = image_cache.get("folders") or {}
    sizes = cfg.get("image_sizes") or {}

    shows_poster_dir = _ensure_leading_slash(str(folders.get("shows_poster") or ""))
    shows_backdrop_dir = _ensure_leading_slash(str(folders.get("shows_backdrop") or ""))
    movies_poster_dir = _ensure_leading_slash(str(folders.get("movies_poster") or ""))
    movies_backdrop_dir = _ensure_leading_slash(str(folders.get("movies_backdrop") or ""))
    seasons_poster_dir = _ensure_leading_slash(str(folders.get("seasons_poster") or ""))
    episodes_stills_dir = _ensure_leading_slash(str(folders.get("episodes_stills") or ""))

    missing_dirs = [k for k,v in {
        "shows_poster": shows_poster_dir,
        "shows_backdrop": shows_backdrop_dir,
        "movies_poster": movies_poster_dir,
        "movies_backdrop": movies_backdrop_dir,
        "seasons_poster": seasons_poster_dir,
        "episodes_stills": episodes_stills_dir,
    }.items() if not v]
    if missing_dirs:
        logging.error("config.json image_cache.folders missing keys: %s", ", ".join(missing_dirs))
        return 3

    tasks: List[Tuple[str, str]] = []  # (url, site_path)
    seen: set[str] = set()

    def add_task(kind: str, tmdb_path: Optional[str], site_path: Optional[str], folder_site: str) -> None:
        if not tmdb_path:
            return
        tmdb_path = str(tmdb_path).strip()
        if not tmdb_path:
            return
        base_name = Path(tmdb_path).name
        if not base_name:
            return

        sp = str(site_path).strip() if site_path else f"{folder_site}/{base_name}"
        sp = sp.replace("\\", "/")
        if not sp.startswith("/"):
            sp = "/" + sp

        if not sp.startswith("/assets/") and not sp.startswith("/image/"):
            return

        if kind in ("show_poster", "movie_poster"):
            size_tag = _tmdb_size_tag(kind, sizes)
        elif kind == "season_poster":
            size_tag = _tmdb_size_tag("season_poster", sizes)
        elif kind == "episode_still":
            size_tag = _tmdb_size_tag("episode_still", sizes)
        else:
            size_tag = _tmdb_size_tag("backdrop", sizes)

        url = _tmdb_url(tmdb_base, size_tag, tmdb_path)
        key = f"{sp}|{url}"
        if key in seen:
            return
        seen.add(key)

        fs = _local_fs_path_from_site_path(sp)
        if fs.is_file():
            return

        tasks.append((url, sp))

    for s in data.get("shows") or []:
        add_task("show_poster", s.get("poster_path"), s.get("poster_local"), shows_poster_dir)
        add_task("backdrop", s.get("backdrop_path"), s.get("backdrop_local"), shows_backdrop_dir)
        for se in s.get("seasons") or []:
            add_task("season_poster", se.get("poster_path"), se.get("poster_local"), seasons_poster_dir)
            for ep in se.get("episodes") or []:
                add_task("episode_still", ep.get("still_path"), ep.get("still_local"), episodes_stills_dir)

    for m in data.get("movies") or []:
        add_task("movie_poster", m.get("poster_path"), m.get("poster_local"), movies_poster_dir)
        add_task("backdrop", m.get("backdrop_path"), m.get("backdrop_local"), movies_backdrop_dir)

    logging.info("[plan] download_tasks=%s (missing only)", len(tasks))
    ok = 0
    fail = 0

    for i, (url, sp) in enumerate(tasks, start=1):
        fs = _local_fs_path_from_site_path(sp)
        logging.info("[%s/%s] GET %s -> %s", i, len(tasks), url, fs)
        success, err = _download(url, fs)
        if success:
            ok += 1
        else:
            fail += 1
            logging.warning("[fail] %s -> %s (%s)", url, fs, err)

    logging.info("[done] ok=%s fail=%s", ok, fail)
    return 0 if fail == 0 else 4

if __name__ == "__main__":
    raise SystemExit(main())
