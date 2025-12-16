#!/usr/bin/env python3
# ======================================================================================
# File: scripts/fetch_tmdb.py
# Project: my_TV_Movie
#
# Purpose
#   - Read input lists (tv_list.txt, movies_list.txt, livetv_list.txt)
#   - Read config (web/config.json)
#   - Fetch metadata from TMDB and build static outputs (data/data.json)
#   - Generate streaming URLs from config (no hard-coded domains)
#   - Optionally cache TMDB images locally (download missing only) into /image/...
#
# Version
#   v2.6.0 (2025-12-16)
#
# Compatibility
#   - Windows / Linux
#   - Python 3.12+
#
# Required env
#   - API_TMDB_KEY   (TMDB v3 key)  OR
#   - API_TMDB_TOKEN (TMDB v4 read access token)
#
# Outputs
#   - data/data.json
#   - data/last_refresh.txt
#   - images under /image/ (if enabled in config.json)
#
# Conventions
#   - No snippets: whole-file replacement only.
#   - Logging: logs/fetch_tmdb.log.txt (append).
# ======================================================================================

from __future__ import annotations

import json
import os
import sys
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from tqdm import tqdm


# -----------------------------
# Paths (repo-relative)
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

PATH_TV_LIST = REPO_ROOT / "tv_list.txt"
PATH_MOVIES_LIST = REPO_ROOT / "movies_list.txt"
PATH_LIVETV_LIST = REPO_ROOT / "livetv_list.txt"

PATH_CONFIG_JSON = REPO_ROOT / "web" / "config.json"

PATH_DATA_DIR = REPO_ROOT / "data"
PATH_DATA_JSON = PATH_DATA_DIR / "data.json"
PATH_LAST_REFRESH = PATH_DATA_DIR / "last_refresh.txt"

PATH_LOG_DIR = REPO_ROOT / "logs"
PATH_LOG_FILE = PATH_LOG_DIR / "fetch_tmdb.log.txt"

# image cache root: repo_root/image/...
PATH_IMAGE_ROOT = REPO_ROOT / "image"


TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


# -----------------------------
# Config model
# -----------------------------
@dataclass(frozen=True)
class StreamingServices:
    vidsrc_tv: str
    vidsrc_movie: str
    videasy_tv: str
    videasy_movie: str


@dataclass(frozen=True)
class ImageSizes:
    show_width: int
    movie_width: int
    season_width: int
    episode_still_w: int
    backdrop_w: int


@dataclass(frozen=True)
class UiTuning:
    calendar_button_scale: float
    calendar_card_density: float


@dataclass(frozen=True)
class CacheImages:
    enabled: bool
    download_missing_only: bool
    timeout_seconds: int
    retries: int
    sleep_seconds_between_retries: float


@dataclass(frozen=True)
class Config:
    streaming_services: StreamingServices
    image_sizes: ImageSizes
    ui_tuning: UiTuning
    cache_images: CacheImages

    @property
    def sha256(self) -> str:
        raw = json.dumps(
            {
                "streaming_services": self.streaming_services.__dict__,
                "image_sizes": self.image_sizes.__dict__,
                "ui_tuning": self.ui_tuning.__dict__,
                "cache_images": self.cache_images.__dict__,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


# -----------------------------
# Logging
# -----------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    PATH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{_now_iso()} | fetch_tmdb | {msg}"
    print(line)
    with PATH_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# -----------------------------
# Helpers
# -----------------------------
def die(msg: str, exit_code: int = 1) -> None:
    log(f"ERROR: {msg}")
    raise SystemExit(exit_code)


def read_text_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    out: List[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def normalize_base_url(url: str) -> str:
    # ensure trailing slash for safe concatenation
    url = (url or "").strip()
    if not url:
        return url
    return url if url.endswith("/") else (url + "/")


def load_config(path: Path) -> Config:
    if not path.exists():
        die(f"Missing config file: {path}")

    cfg_raw = json.loads(path.read_text(encoding="utf-8"))

    ss = cfg_raw.get("streaming_services", {})
    img = cfg_raw.get("image_sizes", {})
    ui = cfg_raw.get("ui_tuning", {})
    cache = cfg_raw.get("cache_images", {})

    def req(d: Dict[str, Any], k: str) -> Any:
        if k not in d or d[k] in (None, ""):
            die(f"config.json missing required key: {k}")
        return d[k]

    streaming = StreamingServices(
        vidsrc_tv=normalize_base_url(req(ss, "vidsrc_tv")),
        vidsrc_movie=normalize_base_url(req(ss, "vidsrc_movie")),
        videasy_tv=normalize_base_url(req(ss, "videasy_tv")),
        videasy_movie=normalize_base_url(req(ss, "videasy_movie")),
    )

    image_sizes = ImageSizes(
        show_width=int(img.get("show_width", 185)),
        movie_width=int(img.get("movie_width", 185)),
        season_width=int(img.get("season_width", 185)),
        episode_still_w=int(img.get("episode_still_w", 300)),
        backdrop_w=int(img.get("backdrop_w", 780)),
    )

    ui_tuning = UiTuning(
        calendar_button_scale=float(ui.get("calendar_button_scale", 0.75)),
        calendar_card_density=float(ui.get("calendar_card_density", 1.0)),
    )

    cache_images = CacheImages(
        enabled=bool(cache.get("enabled", True)),
        download_missing_only=bool(cache.get("download_missing_only", True)),
        timeout_seconds=int(cache.get("timeout_seconds", 30)),
        retries=int(cache.get("retries", 2)),
        sleep_seconds_between_retries=float(cache.get("sleep_seconds_between_retries", 0.7)),
    )

    return Config(
        streaming_services=streaming,
        image_sizes=image_sizes,
        ui_tuning=ui_tuning,
        cache_images=cache_images,
    )


def tmdb_session() -> requests.Session:
    key = os.environ.get("API_TMDB_KEY", "").strip()
    token = os.environ.get("API_TMDB_TOKEN", "").strip()

    if not key and not token:
        die("API_TMDB_KEY or API_TMDB_TOKEN is required in environment")

    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def tmdb_get(session: requests.Session, url: str, params: Optional[Dict[str, Any]] = None, *, cfg: Config) -> Dict[str, Any]:
    params = dict(params or {})
    if "API_TMDB_TOKEN" not in os.environ or not os.environ.get("API_TMDB_TOKEN", "").strip():
        # v3 key style
        params.setdefault("api_key", os.environ.get("API_TMDB_KEY", "").strip())

    for attempt in range(1, cfg.cache_images.retries + 2):
        try:
            r = session.get(url, params=params, timeout=cfg.cache_images.timeout_seconds)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt >= (cfg.cache_images.retries + 1):
                raise
            time.sleep(cfg.cache_images.sleep_seconds_between_retries)


def safe_filename(name: str) -> str:
    # keep it simple: not used for paths that come from TMDB (they already safe),
    # but handy for any future caching by title.
    return "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_", ".")).strip("._")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(session: requests.Session, url: str, dest: Path, *, cfg: Config) -> bool:
    """
    Returns True if downloaded in this run, False if skipped.
    Skips when:
      - download_missing_only enabled AND file already exists AND size > 0
    """
    if cfg.cache_images.download_missing_only and dest.exists() and dest.stat().st_size > 0:
        return False

    ensure_dir(dest.parent)

    for attempt in range(1, cfg.cache_images.retries + 2):
        try:
            with session.get(url, stream=True, timeout=cfg.cache_images.timeout_seconds) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".tmp")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)
                tmp.replace(dest)
            return True
        except Exception:
            if attempt >= (cfg.cache_images.retries + 1):
                raise
            time.sleep(cfg.cache_images.sleep_seconds_between_retries)

    return False


def tmdb_image_url(path_fragment: Optional[str]) -> Optional[str]:
    if not path_fragment:
        return None
    if not path_fragment.startswith("/"):
        path_fragment = "/" + path_fragment
    return TMDB_IMAGE_BASE + path_fragment


def rel_path_from_web_to_repo_image(path_under_image: Path) -> str:
    # Pages live under /web/*.html. Images live under /image/... at repo root.
    # So from /web/index.html, the relative path is ../image/...
    rel = Path("..") / "image" / path_under_image.as_posix()
    return rel.as_posix()


# -----------------------------
# Input parsing
# -----------------------------
def parse_tv_list(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Accepted formats per line:
      - Title | 12345
      - Title | 12345 | S01-S05
      - Title | 12345 | S01
      - 12345 (TMDB id only)
    """
    out: List[Dict[str, Any]] = []
    for s in lines:
        parts = [p.strip() for p in s.split("|")]
        if len(parts) == 1:
            # id-only
            if parts[0].isdigit():
                out.append({"tmdb_id": int(parts[0]), "title": None, "season_hint": None})
            else:
                # title-only not supported; force deterministic id usage
                die(f"tv_list.txt line must include TMDB id: {s}")
            continue

        title = parts[0] or None
        tmdb_id = parts[1]
        if not tmdb_id.isdigit():
            die(f"tv_list.txt invalid TMDB id: {s}")

        season_hint = parts[2] if len(parts) >= 3 and parts[2] else None
        out.append({"tmdb_id": int(tmdb_id), "title": title, "season_hint": season_hint})
    return out


def parse_movies_list(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Accepted formats per line:
      - Title | 12345
      - 12345
    """
    out: List[Dict[str, Any]] = []
    for s in lines:
        parts = [p.strip() for p in s.split("|")]
        if len(parts) == 1:
            if parts[0].isdigit():
                out.append({"tmdb_id": int(parts[0]), "title": None})
            else:
                die(f"movies_list.txt line must include TMDB id: {s}")
            continue
        title = parts[0] or None
        tmdb_id = parts[1]
        if not tmdb_id.isdigit():
            die(f"movies_list.txt invalid TMDB id: {s}")
        out.append({"tmdb_id": int(tmdb_id), "title": title})
    return out


# -----------------------------
# Streaming URLs (config-driven)
# -----------------------------
def build_tv_episode_links(cfg: Config, show_tmdb_id: int, season_number: int, episode_number: int) -> Dict[str, str]:
    # REQUIRED patterns (validated by user):
    #   vidsrc:  https://vidsrc.net/embed/tv/ID/season/ep
    #   videasy: https://player.videasy.net/tv/ID/season/ep
    ss = cfg.streaming_services
    return {
        "vidsrc": f"{ss.vidsrc_tv}{show_tmdb_id}/{season_number}/{episode_number}",
        "videasy": f"{ss.videasy_tv}{show_tmdb_id}/{season_number}/{episode_number}",
    }


def build_movie_links(cfg: Config, movie_tmdb_id: int) -> Dict[str, str]:
    # REQUIRED patterns:
    #   vidsrc:  https://vidsrc.net/embed/movie/ID
    #   videasy: https://player.videasy.net/movie/ID
    ss = cfg.streaming_services
    return {
        "vidsrc": f"{ss.vidsrc_movie}{movie_tmdb_id}",
        "videasy": f"{ss.videasy_movie}{movie_tmdb_id}",
    }


# -----------------------------
# TMDB Fetch
# -----------------------------
def fetch_show(session: requests.Session, cfg: Config, tmdb_id: int) -> Dict[str, Any]:
    show = tmdb_get(session, f"{TMDB_API_BASE}/tv/{tmdb_id}", {"append_to_response": "external_ids"}, cfg=cfg)

    seasons_out: List[Dict[str, Any]] = []
    for s in show.get("seasons", []) or []:
        season_number = s.get("season_number")
        if season_number is None:
            continue

        season = tmdb_get(session, f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season_number}", {}, cfg=cfg)

        episodes_out: List[Dict[str, Any]] = []
        for ep in season.get("episodes", []) or []:
            ep_num = ep.get("episode_number")
            if ep_num is None:
                continue

            # links generated from config ONLY
            links = build_tv_episode_links(cfg, tmdb_id, int(season_number), int(ep_num))

            episodes_out.append(
                {
                    "season_number": int(season_number),
                    "episode_number": int(ep_num),
                    "name": ep.get("name"),
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview"),
                    "runtime": ep.get("runtime"),
                    "still_path": ep.get("still_path"),
                    "links": links,
                    # local path filled later (if caching enabled)
                }
            )

        seasons_out.append(
            {
                "season_number": int(season_number),
                "name": season.get("name"),
                "air_date": season.get("air_date"),
                "overview": season.get("overview"),
                "poster_path": season.get("poster_path"),
                "episodes": episodes_out,
                # local path filled later (if caching enabled)
            }
        )

    out = {
        "tmdb_id": int(tmdb_id),
        "name": show.get("name"),
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "number_of_seasons": show.get("number_of_seasons"),
        "number_of_episodes": show.get("number_of_episodes"),
        "status": show.get("status"),
        "genres": [g.get("name") for g in (show.get("genres") or []) if g.get("name")],
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "external_ids": show.get("external_ids", {}),
        "seasons": seasons_out,
        # links for show-level buttons (optional use)
        "links": {
            "tmdb": f"https://www.themoviedb.org/tv/{tmdb_id}",
        },
    }
    return out


def fetch_movie(session: requests.Session, cfg: Config, tmdb_id: int) -> Dict[str, Any]:
    movie = tmdb_get(session, f"{TMDB_API_BASE}/movie/{tmdb_id}", {"append_to_response": "external_ids"}, cfg=cfg)
    links = build_movie_links(cfg, tmdb_id)

    return {
        "tmdb_id": int(tmdb_id),
        "title": movie.get("title"),
        "release_date": movie.get("release_date"),
        "runtime": movie.get("runtime"),
        "status": movie.get("status"),
        "genres": [g.get("name") for g in (movie.get("genres") or []) if g.get("name")],
        "overview": movie.get("overview"),
        "poster_path": movie.get("poster_path"),
        "backdrop_path": movie.get("backdrop_path"),
        "external_ids": movie.get("external_ids", {}),
        "links": links,
        "tmdb_url": f"https://www.themoviedb.org/movie/{tmdb_id}",
        # local paths filled later (if caching enabled)
    }


# -----------------------------
# Image caching + local path fields
# -----------------------------
def attach_local_paths_and_cache_images(session: requests.Session, cfg: Config, show: Dict[str, Any]) -> Tuple[int, int]:
    """
    Adds local_* fields and optionally caches images.
    Returns (downloaded_count, skipped_count).
    """
    downloaded = 0
    skipped = 0

    def _cache(kind_dir: Path, tmdb_path_fragment: Optional[str], local_key: str) -> None:
        nonlocal downloaded, skipped
        if not tmdb_path_fragment:
            return

        filename = tmdb_path_fragment.lstrip("/")
        dest = PATH_IMAGE_ROOT / kind_dir / filename

        show[local_key] = rel_path_from_web_to_repo_image(kind_dir / filename)

        if not cfg.cache_images.enabled:
            return

        url = tmdb_image_url(tmdb_path_fragment)
        if not url:
            return

        did = download_file(session, url, dest, cfg=cfg)
        if did:
            downloaded += 1
        else:
            skipped += 1

    _cache(Path("shows/poster"), show.get("poster_path"), "local_poster_path")
    _cache(Path("shows/backdrop"), show.get("backdrop_path"), "local_backdrop_path")

    for season in show.get("seasons", []) or []:
        sp = season.get("poster_path")
        if sp:
            fn = sp.lstrip("/")
            season["local_poster_path"] = rel_path_from_web_to_repo_image(Path("shows/seasons/poster") / fn)
            if cfg.cache_images.enabled:
                url = tmdb_image_url(sp)
                dest = PATH_IMAGE_ROOT / "shows" / "seasons" / "poster" / fn
                did = download_file(session, url, dest, cfg=cfg)
                downloaded += 1 if did else 0
                skipped += 0 if did else 1

        for ep in season.get("episodes", []) or []:
            st = ep.get("still_path")
            if not st:
                continue
            fn = st.lstrip("/")
            ep["local_still_path"] = rel_path_from_web_to_repo_image(Path("shows/episodes/stills") / fn)
            if cfg.cache_images.enabled:
                url = tmdb_image_url(st)
                dest = PATH_IMAGE_ROOT / "shows" / "episodes" / "stills" / fn
                did = download_file(session, url, dest, cfg=cfg)
                downloaded += 1 if did else 0
                skipped += 0 if did else 1

    return downloaded, skipped


def attach_local_paths_and_cache_images_movie(session: requests.Session, cfg: Config, movie: Dict[str, Any]) -> Tuple[int, int]:
    downloaded = 0
    skipped = 0

    def _cache(kind_dir: Path, tmdb_path_fragment: Optional[str], local_key: str) -> None:
        nonlocal downloaded, skipped
        if not tmdb_path_fragment:
            return
        filename = tmdb_path_fragment.lstrip("/")
        dest = PATH_IMAGE_ROOT / kind_dir / filename
        movie[local_key] = rel_path_from_web_to_repo_image(kind_dir / filename)

        if not cfg.cache_images.enabled:
            return

        url = tmdb_image_url(tmdb_path_fragment)
        if not url:
            return
        did = download_file(session, url, dest, cfg=cfg)
        if did:
            downloaded += 1
        else:
            skipped += 1

    _cache(Path("movies/poster"), movie.get("poster_path"), "local_poster_path")
    _cache(Path("movies/backdrop"), movie.get("backdrop_path"), "local_backdrop_path")

    return downloaded, skipped


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    t0 = time.time()

    log("START")

    cfg = load_config(PATH_CONFIG_JSON)
    log(f"config: {PATH_CONFIG_JSON} sha256={cfg.sha256[:12]} cache_images.enabled={cfg.cache_images.enabled}")

    tv_lines = read_text_lines(PATH_TV_LIST)
    mv_lines = read_text_lines(PATH_MOVIES_LIST)
    lv_lines = read_text_lines(PATH_LIVETV_LIST)

    tv_items = parse_tv_list(tv_lines)
    mv_items = parse_movies_list(mv_lines)

    log(f"inputs: tv={len(tv_items)} movies={len(mv_items)} livetv={len(lv_lines)}")

    s = tmdb_session()

    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []

    img_downloaded = 0
    img_skipped = 0

    for item in tqdm(tv_items, desc="TMDB TV", unit="show"):
        tmdb_id = int(item["tmdb_id"])
        try:
            show = fetch_show(s, cfg, tmdb_id)
            d, k = attach_local_paths_and_cache_images(s, cfg, show)
            img_downloaded += d
            img_skipped += k
            shows_out.append(show)
        except Exception as e:
            log(f"WARN: TV {tmdb_id} failed: {e}")

    for item in tqdm(mv_items, desc="TMDB Movies", unit="movie"):
        tmdb_id = int(item["tmdb_id"])
        try:
            movie = fetch_movie(s, cfg, tmdb_id)
            d, k = attach_local_paths_and_cache_images_movie(s, cfg, movie)
            img_downloaded += d
            img_skipped += k
            movies_out.append(movie)
        except Exception as e:
            log(f"WARN: Movie {tmdb_id} failed: {e}")

    shows_out.sort(key=lambda x: (x.get("name") or "").lower())
    movies_out.sort(key=lambda x: (x.get("title") or "").lower())

    build_ts = _now_iso()

    payload = {
        "meta": {
            "data_version": "v3.3.x",
            "built_utc": build_ts,
            "config_sha256": cfg.sha256,
            "counts": {
                "shows": len(shows_out),
                "movies": len(movies_out),
                "livetv": len(lv_lines),
            },
            "image_cache": {
                "enabled": cfg.cache_images.enabled,
                "downloaded": img_downloaded,
                "skipped": img_skipped,
            },
            "streaming_services": cfg.streaming_services.__dict__,
            "image_sizes": cfg.image_sizes.__dict__,
            "ui_tuning": cfg.ui_tuning.__dict__,
        },
        "shows": shows_out,
        "movies": movies_out,
        "livetv": [],  # reserved
    }

    PATH_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PATH_DATA_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    PATH_LAST_REFRESH.write_text(build_ts + "\n", encoding="utf-8")

    dt = time.time() - t0
    log(f"WRITE: {PATH_DATA_JSON} bytes={PATH_DATA_JSON.stat().st_size}")
    log(f"DONE: shows={len(shows_out)} movies={len(movies_out)} img_downloaded={img_downloaded} img_skipped={img_skipped} sec={dt:.2f}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        die("Interrupted", exit_code=130)
