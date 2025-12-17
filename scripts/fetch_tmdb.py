#!/usr/bin/env python3
# ==============================================================================
# File:        scripts/fetch_tmdb.py
# Repo:        my_TV_Movie
# Path:        scripts/fetch_tmdb.py
#
# Version:
#   v2.6.2 (2025-12-16)
#
# Purpose:
#   - Read source lists (root):
#       * tv_list.txt
#       * movies_list.txt
#       * livetv_list.txt  (OPTIONAL; never hard-fail if missing)
#   - Read authoritative configuration:
#       * web/config.json  (streaming bases + image sizes + UI tuning + caching)
#   - Fetch data from TMDB and build:
#       * data/data.json
#         - streaming links generated from config ONLY (no stale domains)
#         - local_* image paths included so UI can use cached images deterministically
#   - Optional image caching (download missing only):
#       * image/shows/poster/
#       * image/shows/backdrop/
#       * image/shows/seasons/poster/
#       * image/shows/episodes/stills/
#       * image/movies/poster/
#       * image/movies/backdrop/
#
# Auth (env):
#   - API_TMDB_KEY     (preferred)
#   - API_TMDB_TOKEN   (Bearer token; fallback)
#
# Output:
#   - data/data.json
#   - data/last_refresh.txt
#
# Logging:
#   - logs/fetch_tmdb.log.txt
#   - logs/fetch_tmdb_YYYYMMDD_HHMMSS.log.txt
#
# Non-negotiable rules:
#   - Config drives everything (bases + sizes); UI must NOT invent domains.
#   - No “embed/” variants for Videasy.
#       TV:    https://player.videasy.net/tv/{id}/{season}/{ep}
#       Movie: https://player.videasy.net/movie/{id}
#   - VidSrc (as per your spec):
#       TV:    https://vidsrc.net/embed/tv/{id}/{season}/{ep}
#       Movie: https://vidsrc.net/embed/movie/{id}
#   - Live TV list is OPTIONAL; missing file => livetv=[]
#   - Cache downloads missing only; never overwrite existing.
#   - Hard QA: any link not starting with configured base => fail build.
# ==============================================================================

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


# ==============================================================================
# [PATHS-1.0] Repo paths (stable)
# ==============================================================================
REPO_ROOT = Path(__file__).resolve().parents[1]

TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"
LIVETV_LIST_PATH = REPO_ROOT / "livetv_list.txt"  # OPTIONAL

WEB_DIR = REPO_ROOT / "web"
CONFIG_JSON_PATH = WEB_DIR / "config.json"

DATA_DIR = REPO_ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"
LAST_REFRESH_PATH = DATA_DIR / "last_refresh.txt"

IMAGE_DIR = REPO_ROOT / "image"
IMG_SHOWS_POSTER_DIR = IMAGE_DIR / "shows" / "poster"
IMG_SHOWS_BACKDROP_DIR = IMAGE_DIR / "shows" / "backdrop"
IMG_SHOWS_SEASONS_POSTER_DIR = IMAGE_DIR / "shows" / "seasons" / "poster"
IMG_SHOWS_EP_STILLS_DIR = IMAGE_DIR / "shows" / "episodes" / "stills"
IMG_MOVIES_POSTER_DIR = IMAGE_DIR / "movies" / "poster"
IMG_MOVIES_BACKDROP_DIR = IMAGE_DIR / "movies" / "backdrop"

LOGS_DIR = REPO_ROOT / "logs"

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


# ==============================================================================
# [CFG-1.0] Config models
# ==============================================================================
@dataclass(frozen=True)
class StreamingConfig:
    vidsrc_tv: str
    vidsrc_movie: str
    videasy_tv: str
    videasy_movie: str


@dataclass(frozen=True)
class ImageSizeConfig:
    show_width: int
    movie_width: int
    season_width: int
    episode_still_w: int
    backdrop_w: int


@dataclass(frozen=True)
class UiTuningConfig:
    calendar_button_scale: float
    calendar_card_density: float


@dataclass(frozen=True)
class CacheConfig:
    enabled: bool


@dataclass(frozen=True)
class AppConfig:
    streaming: StreamingConfig
    img: ImageSizeConfig
    ui: UiTuningConfig
    cache: CacheConfig


# ==============================================================================
# [LOG-1.0] Logging
# ==============================================================================
def setup_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    latest_log = LOGS_DIR / "fetch_tmdb.log.txt"
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    stamped_log = LOGS_DIR / f"fetch_tmdb_{ts}.log.txt"

    fmt = "%(asctime)s | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for h in list(root.handlers):
        root.removeHandler(h)

    fh_latest = logging.FileHandler(latest_log, encoding="utf-8")
    fh_latest.setLevel(logging.INFO)
    fh_latest.setFormatter(logging.Formatter(fmt, datefmt))

    fh_stamped = logging.FileHandler(stamped_log, encoding="utf-8")
    fh_stamped.setLevel(logging.INFO)
    fh_stamped.setFormatter(logging.Formatter(fmt, datefmt))

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter(fmt, datefmt))

    root.addHandler(fh_latest)
    root.addHandler(fh_stamped)
    root.addHandler(sh)

    logging.info("[fetch_tmdb] Logging: %s", latest_log)
    logging.info("[fetch_tmdb] Logging: %s", stamped_log)


# ==============================================================================
# [UTIL-1.0] Small helpers
# ==============================================================================
def _norm_base(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    return u if u.endswith("/") else (u + "/")


def join_base(base: str, *parts: Any) -> str:
    """
    Join a normalized base URL with path tokens.
    """
    base = _norm_base(base)
    tail = "/".join(str(p).strip("/").strip() for p in parts if str(p).strip() != "")
    return base + tail if tail else base


def safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def safe_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def read_text_lines(p: Path) -> List[str]:
    if not p.exists():
        return []
    lines: List[str] = []
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    IMG_SHOWS_POSTER_DIR.mkdir(parents=True, exist_ok=True)
    IMG_SHOWS_BACKDROP_DIR.mkdir(parents=True, exist_ok=True)
    IMG_SHOWS_SEASONS_POSTER_DIR.mkdir(parents=True, exist_ok=True)
    IMG_SHOWS_EP_STILLS_DIR.mkdir(parents=True, exist_ok=True)

    IMG_MOVIES_POSTER_DIR.mkdir(parents=True, exist_ok=True)
    IMG_MOVIES_BACKDROP_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# [CFG-2.0] Load authoritative config (web/config.json)
# ==============================================================================
def load_app_config() -> AppConfig:
    if not CONFIG_JSON_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_JSON_PATH}")

    raw = json.loads(CONFIG_JSON_PATH.read_text(encoding="utf-8"))

    ss = raw.get("streaming_services") or {}
    img = raw.get("image_sizes") or {}
    ui = raw.get("ui_tuning") or {}

    # cache config is optional; default enabled
    cache_raw = raw.get("cache") or raw.get("image_cache") or {}
    cache_enabled = bool(cache_raw.get("enabled", True))

    streaming = StreamingConfig(
        vidsrc_tv=_norm_base(ss.get("vidsrc_tv", "")),
        vidsrc_movie=_norm_base(ss.get("vidsrc_movie", "")),
        videasy_tv=_norm_base(ss.get("videasy_tv", "")),
        videasy_movie=_norm_base(ss.get("videasy_movie", "")),
    )

    img_cfg = ImageSizeConfig(
        show_width=safe_int(img.get("show_width", 185), 185),
        movie_width=safe_int(img.get("movie_width", 185), 185),
        season_width=safe_int(img.get("season_width", 185), 185),
        episode_still_w=safe_int(img.get("episode_still_w", 300), 300),
        backdrop_w=safe_int(img.get("backdrop_w", 780), 780),
    )

    ui_cfg = UiTuningConfig(
        calendar_button_scale=safe_float(ui.get("calendar_button_scale", 0.75), 0.75),
        calendar_card_density=safe_float(ui.get("calendar_card_density", 1.0), 1.0),
    )

    cache_cfg = CacheConfig(enabled=cache_enabled)

    # Hard validation to avoid silent broken builds
    missing = []
    if not streaming.vidsrc_tv:
        missing.append("streaming_services.vidsrc_tv")
    if not streaming.vidsrc_movie:
        missing.append("streaming_services.vidsrc_movie")
    if not streaming.videasy_tv:
        missing.append("streaming_services.videasy_tv")
    if not streaming.videasy_movie:
        missing.append("streaming_services.videasy_movie")
    if missing:
        raise ValueError(f"Invalid config.json, missing: {', '.join(missing)}")

    return AppConfig(streaming=streaming, img=img_cfg, ui=ui_cfg, cache=cache_cfg)


# ==============================================================================
# [TMDB-1.0] TMDB auth + GET
# ==============================================================================
def tmdb_headers() -> Dict[str, str]:
    token = (os.environ.get("API_TMDB_TOKEN") or "").strip()
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json;charset=utf-8"}
    return {"Content-Type": "application/json;charset=utf-8"}


def tmdb_params() -> Dict[str, str]:
    key = (os.environ.get("API_TMDB_KEY") or "").strip()
    if key:
        return {"api_key": key}
    return {}


def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = TMDB_API_BASE + path
    p = dict(tmdb_params())
    if params:
        p.update(params)

    if not p and "Authorization" not in tmdb_headers():
        raise RuntimeError("Missing TMDB auth: set API_TMDB_KEY or API_TMDB_TOKEN")

    r = requests.get(url, headers=tmdb_headers(), params=p, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"TMDB GET failed {r.status_code} for {url}: {r.text[:500]}")
    return r.json()


# ==============================================================================
# [LISTS-1.0] Input parsing (root lists)
# ==============================================================================
def parse_id_list(lines: List[str], label: str) -> List[Dict[str, Any]]:
    """
    Supported formats (per line):
      - 12345
      - 12345 | Optional Name
    """
    out: List[Dict[str, Any]] = []
    for line in lines:
        if "|" in line:
            left, right = line.split("|", 1)
            tid = left.strip()
            name = right.strip()
        else:
            tid = line.strip()
            name = ""

        if not tid.isdigit():
            logging.warning("[%s] Skip invalid line: %s", label, line)
            continue

        out.append({"tmdb_id": int(tid), "ref_name": name or None})

    return out


def read_tv_list() -> List[Dict[str, Any]]:
    if not TV_LIST_PATH.exists():
        raise FileNotFoundError(f"Missing required list file: {TV_LIST_PATH}")
    return parse_id_list(read_text_lines(TV_LIST_PATH), "tv_list")


def read_movies_list() -> List[Dict[str, Any]]:
    if not MOVIES_LIST_PATH.exists():
        raise FileNotFoundError(f"Missing required list file: {MOVIES_LIST_PATH}")
    return parse_id_list(read_text_lines(MOVIES_LIST_PATH), "movies_list")


def read_livetv_list_optional() -> List[Dict[str, Any]]:
    # OPTIONAL: return [] if missing
    if not LIVETV_LIST_PATH.exists():
        logging.warning("[livetv_list] Missing %s (optional) -> livetv=[]", LIVETV_LIST_PATH.name)
        return []
    return [{"raw": s} for s in read_text_lines(LIVETV_LIST_PATH)]


# ==============================================================================
# [IMG-1.0] TMDB image URL + local caching (download missing only)
# ==============================================================================
def tmdb_image_url(width: int, tmdb_path: Optional[str]) -> str:
    if not tmdb_path:
        return ""
    # tmdb_path includes leading "/" (e.g., "/abc.jpg")
    w = f"w{int(width)}"
    return f"{TMDB_IMAGE_BASE}/{w}{tmdb_path}"


def rel_repo_path(p: Path) -> str:
    # web-friendly POSIX path relative to repo root
    return p.relative_to(REPO_ROOT).as_posix()


def cache_image_if_missing(url: str, dest_dir: Path, tmdb_path: Optional[str]) -> Optional[str]:
    """
    Downloads only if missing. Returns local relative path string (POSIX), or None.
    """
    if not url or not tmdb_path:
        return None

    filename = Path(tmdb_path).name
    if not filename:
        return None

    dest = dest_dir / filename
    if dest.exists() and dest.stat().st_size > 0:
        return rel_repo_path(dest)

    try:
        r = requests.get(url, timeout=45)
        if r.status_code >= 400 or not r.content:
            logging.warning("[img] download failed %s (%s)", r.status_code, url)
            return None
        dest.write_bytes(r.content)
        logging.info("[img] cached -> %s", dest)
        return rel_repo_path(dest)
    except Exception as e:
        logging.warning("[img] error caching %s (%s)", url, e)
        return None


# ==============================================================================
# [BUILD-1.0] Build show + season + episodes (incl links + local paths)
# ==============================================================================
def build_show_entry(cfg: AppConfig, show_seed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id = int(show_seed["tmdb_id"])
    try:
        show = tmdb_get(f"/tv/{tmdb_id}", params={"language": "en-US"})
    except Exception as e:
        logging.error("[show] TMDB fail tv/%s (%s)", tmdb_id, e)
        return None

    poster_path = show.get("poster_path")
    backdrop_path = show.get("backdrop_path")

    local_show_poster = None
    local_show_backdrop = None
    if cfg.cache.enabled:
        local_show_poster = cache_image_if_missing(
            tmdb_image_url(cfg.img.show_width, poster_path),
            IMG_SHOWS_POSTER_DIR,
            poster_path,
        )
        local_show_backdrop = cache_image_if_missing(
            tmdb_image_url(cfg.img.backdrop_w, backdrop_path),
            IMG_SHOWS_BACKDROP_DIR,
            backdrop_path,
        )

    seasons_out: List[Dict[str, Any]] = []
    for s in (show.get("seasons") or []):
        season_number = s.get("season_number")
        if season_number is None:
            continue

        try:
            season = tmdb_get(f"/tv/{tmdb_id}/season/{season_number}", params={"language": "en-US"})
        except Exception as e:
            logging.warning("[season] TMDB fail tv/%s/season/%s (%s)", tmdb_id, season_number, e)
            continue

        season_poster_path = season.get("poster_path")
        local_season_poster = None
        if cfg.cache.enabled:
            local_season_poster = cache_image_if_missing(
                tmdb_image_url(cfg.img.season_width, season_poster_path),
                IMG_SHOWS_SEASONS_POSTER_DIR,
                season_poster_path,
            )

        episodes_out: List[Dict[str, Any]] = []
        for ep in (season.get("episodes") or []):
            ep_no = ep.get("episode_number")
            if ep_no is None:
                continue

            still_path = ep.get("still_path")
            local_still = None
            if cfg.cache.enabled:
                local_still = cache_image_if_missing(
                    tmdb_image_url(cfg.img.episode_still_w, still_path),
                    IMG_SHOWS_EP_STILLS_DIR,
                    still_path,
                )

            # Streaming links (generated from config only)
            links = {
                "tmdb": f"https://www.themoviedb.org/tv/{tmdb_id}/season/{season_number}/episode/{ep_no}",
                "vidsrc": join_base(cfg.streaming.vidsrc_tv, tmdb_id, season_number, ep_no),
                "videasy": join_base(cfg.streaming.videasy_tv, tmdb_id, season_number, ep_no),
            }

            episodes_out.append(
                {
                    "episode_number": ep_no,
                    "name": ep.get("name") or "",
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview") or "",
                    "runtime": ep.get("runtime"),
                    "still_path": still_path,
                    "local_still_path": local_still,
                    "links": links,
                }
            )

        seasons_out.append(
            {
                "season_number": season_number,
                "name": season.get("name") or s.get("name") or f"Season {season_number}",
                "air_date": season.get("air_date") or s.get("air_date"),
                "overview": season.get("overview") or "",
                "poster_path": season_poster_path,
                "local_poster_path": local_season_poster,
                "episodes": episodes_out,
            }
        )

    return {
        "ref_name": show_seed.get("ref_name") or show.get("name"),
        "show_id": tmdb_id,
        "tmdb_id": tmdb_id,
        "name": show.get("name") or "",
        "status": show.get("status") or "",
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "number_of_seasons": show.get("number_of_seasons"),
        "number_of_episodes": show.get("number_of_episodes"),
        "genres": [g.get("name") for g in (show.get("genres") or []) if g.get("name")],
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "local_poster_path": local_show_poster,
        "local_backdrop_path": local_show_backdrop,
        "seasons": seasons_out,
        "links": {
            "tmdb": f"https://www.themoviedb.org/tv/{tmdb_id}",
            "vidsrc": join_base(cfg.streaming.vidsrc_tv, tmdb_id),
            "videasy": join_base(cfg.streaming.videasy_tv, tmdb_id),
        },
    }


# ==============================================================================
# [BUILD-2.0] Build movie (incl links + local paths)
# ==============================================================================
def build_movie_entry(cfg: AppConfig, movie_seed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id = int(movie_seed["tmdb_id"])
    try:
        movie = tmdb_get(f"/movie/{tmdb_id}", params={"language": "en-US"})
    except Exception as e:
        logging.error("[movie] TMDB fail movie/%s (%s)", tmdb_id, e)
        return None

    poster_path = movie.get("poster_path")
    backdrop_path = movie.get("backdrop_path")

    local_movie_poster = None
    local_movie_backdrop = None
    if cfg.cache.enabled:
        local_movie_poster = cache_image_if_missing(
            tmdb_image_url(cfg.img.movie_width, poster_path),
            IMG_MOVIES_POSTER_DIR,
            poster_path,
        )
        local_movie_backdrop = cache_image_if_missing(
            tmdb_image_url(cfg.img.backdrop_w, backdrop_path),
            IMG_MOVIES_BACKDROP_DIR,
            backdrop_path,
        )

    links = {
        "tmdb": f"https://www.themoviedb.org/movie/{tmdb_id}",
        "vidsrc": join_base(cfg.streaming.vidsrc_movie, tmdb_id),
        "videasy": join_base(cfg.streaming.videasy_movie, tmdb_id),
    }

    return {
        "ref_name": movie_seed.get("ref_name") or movie.get("title"),
        "movie_id": tmdb_id,
        "tmdb_id": tmdb_id,
        "title": movie.get("title") or "",
        "release_date": movie.get("release_date"),
        "runtime": movie.get("runtime"),
        "status": movie.get("status") or "",
        "genres": [g.get("name") for g in (movie.get("genres") or []) if g.get("name")],
        "overview": movie.get("overview") or "",
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "local_poster_path": local_movie_poster,
        "local_backdrop_path": local_movie_backdrop,
        "links": links,
    }


# ==============================================================================
# [QA-1.0] Streaming base QA (prevents old-domain usage)
# ==============================================================================
def qa_validate_links(cfg: AppConfig, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errs: List[str] = []

    tv_v1 = _norm_base(cfg.streaming.vidsrc_tv)
    tv_v2 = _norm_base(cfg.streaming.videasy_tv)
    mv_v1 = _norm_base(cfg.streaming.vidsrc_movie)
    mv_v2 = _norm_base(cfg.streaming.videasy_movie)

    # Episodes
    for s in data.get("shows") or []:
        for season in (s.get("seasons") or []):
            for ep in (season.get("episodes") or []):
                links = ep.get("links") or {}
                a = (links.get("vidsrc") or "").strip()
                b = (links.get("videasy") or "").strip()
                if a and not a.startswith(tv_v1):
                    errs.append(f"Show(ep) vidsrc base mismatch: {a}")
                if b and not b.startswith(tv_v2):
                    errs.append(f"Show(ep) videasy base mismatch: {b}")

    # Movies
    for m in data.get("movies") or []:
        links = m.get("links") or {}
        a = (links.get("vidsrc") or "").strip()
        b = (links.get("videasy") or "").strip()
        if a and not a.startswith(mv_v1):
            errs.append(f"Movie vidsrc base mismatch: {a}")
        if b and not b.startswith(mv_v2):
            errs.append(f"Movie videasy base mismatch: {b}")

    return (len(errs) == 0, errs)


# ==============================================================================
# [MAIN-1.0] Main
# ==============================================================================
def main() -> None:
    setup_logging()
    ensure_dirs()

    # Auth sanity
    key = (os.environ.get("API_TMDB_KEY") or "").strip()
    token = (os.environ.get("API_TMDB_TOKEN") or "").strip()
    if not key and not token:
        logging.error("[fetch_tmdb] ERROR: API_TMDB_KEY or API_TMDB_TOKEN must be set.")
        sys.exit(1)

    cfg = load_app_config()

    logging.info("[fetch_tmdb] Config: %s", CONFIG_JSON_PATH)
    logging.info(
        "[fetch_tmdb] Bases: vidsrc_tv=%s | videasy_tv=%s | vidsrc_movie=%s | videasy_movie=%s",
        cfg.streaming.vidsrc_tv,
        cfg.streaming.videasy_tv,
        cfg.streaming.vidsrc_movie,
        cfg.streaming.videasy_movie,
    )
    logging.info(
        "[fetch_tmdb] Sizes: show=%s movie=%s season=%s epstill=%s backdrop=%s | cache=%s",
        cfg.img.show_width,
        cfg.img.movie_width,
        cfg.img.season_width,
        cfg.img.episode_still_w,
        cfg.img.backdrop_w,
        cfg.cache.enabled,
    )

    # Inputs (LiveTV optional)
    tv_seeds = read_tv_list()
    movie_seeds = read_movies_list()
    livetv_items = read_livetv_list_optional()

    logging.info("[fetch_tmdb] Inputs: tv=%s movies=%s livetv=%s", len(tv_seeds), len(movie_seeds), len(livetv_items))

    # Build shows
    shows_out: List[Dict[str, Any]] = []
    for seed in tv_seeds:
        entry = build_show_entry(cfg, seed)
        if entry:
            shows_out.append(entry)

    # Build movies
    movies_out: List[Dict[str, Any]] = []
    for seed in movie_seeds:
        entry = build_movie_entry(cfg, seed)
        if entry:
            movies_out.append(entry)

    # Meta
    built_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data: Dict[str, Any] = {
        "shows": shows_out,
        "movies": movies_out,
        "livetv": livetv_items,
        "meta": {
            "version": "v2.6.2",
            "built_at": built_at,
            "shows": len(shows_out),
            "movies": len(movies_out),
            "livetv": len(livetv_items),
            "config_snapshot": {
                "streaming_services": {
                    "vidsrc_tv": cfg.streaming.vidsrc_tv,
                    "vidsrc_movie": cfg.streaming.vidsrc_movie,
                    "videasy_tv": cfg.streaming.videasy_tv,
                    "videasy_movie": cfg.streaming.videasy_movie,
                },
                "image_sizes": {
                    "show_width": cfg.img.show_width,
                    "movie_width": cfg.img.movie_width,
                    "season_width": cfg.img.season_width,
                    "episode_still_w": cfg.img.episode_still_w,
                    "backdrop_w": cfg.img.backdrop_w,
                },
                "ui_tuning": {
                    "calendar_button_scale": cfg.ui.calendar_button_scale,
                    "calendar_card_density": cfg.ui.calendar_card_density,
                },
                "cache": {"enabled": cfg.cache.enabled},
            },
        },
    }

    # QA: bases must match config
    ok, errs = qa_validate_links(cfg, data)
    if not ok:
        logging.error("[fetch_tmdb] QA FAILED: %s base mismatch issues", len(errs))
        for e in errs[:60]:
            logging.error("[fetch_tmdb]   %s", e)
        sys.exit(2)

    # Write outputs
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    LAST_REFRESH_PATH.write_text(built_at, encoding="utf-8")

    logging.info("[fetch_tmdb] Wrote: %s (%s bytes)", DATA_JSON_PATH, DATA_JSON_PATH.stat().st_size)
    logging.info("[fetch_tmdb] Wrote: %s", LAST_REFRESH_PATH)
    logging.info("[fetch_tmdb] DONE | shows=%s movies=%s livetv=%s", len(shows_out), len(movies_out), len(livetv_items))


if __name__ == "__main__":
    main()
