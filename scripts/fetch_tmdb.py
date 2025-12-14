#!/usr/bin/env python3
# ======================================================================================
# [FETCH_TMDB-0.0] my_TV_Movie — TMDB builder (config-driven streaming links + image cache)
# --------------------------------------------------------------------------------------
# PURPOSE
#   - Read:  web/config.json   (streaming base URLs + image sizes)
#   - Read:  tv_list.txt, movies_list.txt (TMDB IDs)
#   - Build: data/data.json (show/movie metadata + seasons/episodes + LINKS generated)
#   - Cache: image/*  (download missing only; never overwrite existing)
#
# KEY RULES (P1/P2)
#   - config drives URL generation (NO hard-coded domains in UI)
#   - data.json contains final links for episode/movie playback using config
#   - image cache is optional and "download missing only"
#
# ENV
#   - API_TMDB_KEY must be set (v3 API key)
# ======================================================================================

from __future__ import annotations

import json
import os
import re
import sys
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# stdlib HTTP (avoid requests dependency)
import urllib.request
import urllib.parse
import urllib.error


# ======================================================================================
# [FETCH_TMDB-1.0] Repo paths + constants
# ======================================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]  # .../my_TV_Movie
WEB_DIR = REPO_ROOT / "web"
DATA_DIR = REPO_ROOT / "data"
IMAGE_DIR = REPO_ROOT / "image"

TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"

CONFIG_PATH = WEB_DIR / "config.json"
DATA_JSON_PATH = DATA_DIR / "data.json"

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


# ======================================================================================
# [FETCH_TMDB-1.1] Output image folders (your chosen structure)
# ======================================================================================

IMG_SHOWS_POSTER = IMAGE_DIR / "shows" / "poster"
IMG_SHOWS_BACKDROP = IMAGE_DIR / "shows" / "backdrop"
IMG_SHOWS_SEASONS_POSTER = IMAGE_DIR / "shows" / "seasons" / "poster"
IMG_SHOWS_EPISODES_STILLS = IMAGE_DIR / "shows" / "episodes" / "stills"

IMG_MOVIES_POSTER = IMAGE_DIR / "movies" / "poster"
IMG_MOVIES_BACKDROP = IMAGE_DIR / "movies" / "backdrop"


# ======================================================================================
# [FETCH_TMDB-1.2] Small utilities
# ======================================================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    print(msg, flush=True)


def die(msg: str, code: int = 1) -> None:
    log(f"[fetch_tmdb] ERROR: {msg}")
    raise SystemExit(code)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def read_text_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def extract_first_int(s: str) -> Optional[int]:
    m = re.search(r"(\d{2,})", s)
    return int(m.group(1)) if m else None


def sanitize_tmdb_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    # TMDB paths typically like "/abc.jpg"
    return path if path.startswith("/") else "/" + path


def build_img_url(path: str, size_token: str) -> str:
    # size_token like "w185", "w300", "w780", "original"
    clean = sanitize_tmdb_path(path) or ""
    return f"{TMDB_IMAGE_BASE}/{size_token}{clean}"


def file_exists_nonempty(p: Path) -> bool:
    return p.exists() and p.is_file() and p.stat().st_size > 0


def http_get_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def http_download_file(url: str, out_path: Path, timeout: int = 60) -> bool:
    """
    Download to out_path only if missing. Returns True if downloaded, False if skipped.
    Never overwrites existing.
    """
    if file_exists_nonempty(out_path):
        return False

    ensure_dir(out_path.parent)

    req = urllib.request.Request(url, headers={"User-Agent": "my_TV_Movie/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        out_path.write_bytes(data)
        return True
    except Exception as e:
        # Do not fail build on an image download glitch; leave it missing.
        log(f"[fetch_tmdb] WARN: image download failed: {url} -> {out_path.name} ({e})")
        return False


# ======================================================================================
# [FETCH_TMDB-2.0] Config model + loader
# ======================================================================================

@dataclass
class StreamingConfig:
    vidsrc_tv: str
    vidsrc_movie: str
    videasy_tv: str
    videasy_movie: str


@dataclass
class ImageConfig:
    show_width: int
    movie_width: int
    season_width: int
    episode_still_w: int
    backdrop_w: int


@dataclass
class UiTuningConfig:
    calendar_button_scale: float
    calendar_card_density: float


@dataclass
class AppConfig:
    streaming: StreamingConfig
    images: ImageConfig
    ui: UiTuningConfig


def load_config(path: Path) -> AppConfig:
    # [FETCH_TMDB-2.1] Defaults (safe)
    streaming = StreamingConfig(
        vidsrc_tv="https://vidsrc.net/embed/tv/",
        vidsrc_movie="https://vidsrc.net/embed/movie/",
        videasy_tv="https://player.videasy.net/tv/",
        videasy_movie="https://player.videasy.net/movie/",
    )
    images = ImageConfig(
        show_width=185,
        movie_width=185,
        season_width=185,
        episode_still_w=300,
        backdrop_w=780,
    )
    ui = UiTuningConfig(
        calendar_button_scale=0.75,
        calendar_card_density=1.0,
    )

    if not path.exists():
        log(f"[fetch_tmdb] WARN: config.json not found at {path}. Using defaults.")
        return AppConfig(streaming=streaming, images=images, ui=ui)

    raw = json.loads(path.read_text(encoding="utf-8"))

    # [FETCH_TMDB-2.2] Accept your current schema
    ss = raw.get("streaming_services", {})
    if isinstance(ss, dict):
        streaming.vidsrc_tv = ss.get("vidsrc_tv", streaming.vidsrc_tv)
        streaming.vidsrc_movie = ss.get("vidsrc_movie", streaming.vidsrc_movie)
        streaming.videasy_tv = ss.get("videasy_tv", streaming.videasy_tv)
        streaming.videasy_movie = ss.get("videasy_movie", streaming.videasy_movie)

    # [FETCH_TMDB-2.3] Image sizes
    im = raw.get("image_sizes", {})
    if isinstance(im, dict):
        images.show_width = int(im.get("show_width", images.show_width) or images.show_width)
        images.movie_width = int(im.get("movie_width", images.movie_width) or images.movie_width)
        images.season_width = int(im.get("season_width", images.season_width) or images.season_width)
        images.episode_still_w = int(im.get("episode_still_w", images.episode_still_w) or images.episode_still_w)
        images.backdrop_w = int(im.get("backdrop_w", images.backdrop_w) or images.backdrop_w)

    # [FETCH_TMDB-2.4] UI tuning (not used by python, but preserved as truth-source)
    ut = raw.get("ui_tuning", {})
    if isinstance(ut, dict):
        ui.calendar_button_scale = float(ut.get("calendar_button_scale", ui.calendar_button_scale) or ui.calendar_button_scale)
        ui.calendar_card_density = float(ut.get("calendar_card_density", ui.calendar_card_density) or ui.calendar_card_density)

    return AppConfig(streaming=streaming, images=images, ui=ui)


# ======================================================================================
# [FETCH_TMDB-3.0] TMDB request helpers
# ======================================================================================

def require_api_key() -> str:
    key = os.environ.get("API_TMDB_KEY", "").strip()
    if not key:
        die("API_TMDB_KEY is required in env.")
    return key


def tmdb_url(api_key: str, path: str, params: Optional[Dict[str, str]] = None) -> str:
    # [FETCH_TMDB-3.1] Build TMDB v3 URL with api_key
    p = params or {}
    p["api_key"] = api_key
    qs = urllib.parse.urlencode(p)
    return f"{TMDB_API_BASE}{path}?{qs}"


def tmdb_get(api_key: str, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    url = tmdb_url(api_key, path, params)
    return http_get_json(url)


# ======================================================================================
# [FETCH_TMDB-4.0] List parsing (tv_list.txt, movies_list.txt)
# ======================================================================================

def parse_id_list(path: Path) -> List[int]:
    """
    Flexible parser:
      - ignores blank lines and lines starting with '#'
      - extracts first integer token as TMDB id
    """
    ids: List[int] = []
    for line in read_text_lines(path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        tid = extract_first_int(s)
        if tid:
            ids.append(tid)
    # unique + stable order
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            out.append(i)
            seen.add(i)
    return out


# ======================================================================================
# [FETCH_TMDB-5.0] Link generation (CONFIG DRIVEN)
# ======================================================================================

def make_episode_links(cfg: AppConfig, tv_id: int, season_number: int, episode_number: int) -> Dict[str, str]:
    # [FETCH_TMDB-5.1] Correct bases (per your rule)
    # vidsrc:  https://vidsrc.net/embed/tv/{id}/{season}/{episode}
    # videasy: https://player.videasy.net/tv/{id}/{season}/{episode}
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{tv_id}/season/{season_number}/episode/{episode_number}",
        "vidsrc": f"{cfg.streaming.vidsrc_tv}{tv_id}/{season_number}/{episode_number}",
        "videasy": f"{cfg.streaming.videasy_tv}{tv_id}/{season_number}/{episode_number}",
    }


def make_movie_links(cfg: AppConfig, movie_id: int) -> Dict[str, str]:
    # [FETCH_TMDB-5.2] Movie bases (similar)
    return {
        "tmdb": f"https://www.themoviedb.org/movie/{movie_id}",
        "vidsrc": f"{cfg.streaming.vidsrc_movie}{movie_id}",
        "videasy": f"{cfg.streaming.videasy_movie}{movie_id}",
    }


# ======================================================================================
# [FETCH_TMDB-6.0] Image caching logic (download missing only)
# ======================================================================================

def local_rel(path_from_repo: Path) -> str:
    """
    Convert a repo path into a web-usable relative path from web/index.html.
    index.html lives in /web so it reaches /image via ../image/...
    """
    rel = path_from_repo.relative_to(REPO_ROOT).as_posix()
    if not rel.startswith("image/"):
        # safety, but expected to be image/...
        return f"../{rel}"
    return f"../{rel}"


def cache_show_images(cfg: AppConfig, show: Dict[str, Any]) -> None:
    poster_path = sanitize_tmdb_path(show.get("poster_path"))
    backdrop_path = sanitize_tmdb_path(show.get("backdrop_path"))

    if poster_path:
        url = build_img_url(poster_path, f"w{cfg.images.show_width}")
        out = IMG_SHOWS_POSTER / poster_path.lstrip("/")
        if http_download_file(url, out):
            log(f"[fetch_tmdb] img+ show poster: {out.name}")

        show["local_poster_path"] = local_rel(out)

    if backdrop_path:
        url = build_img_url(backdrop_path, f"w{cfg.images.backdrop_w}")
        out = IMG_SHOWS_BACKDROP / backdrop_path.lstrip("/")
        if http_download_file(url, out):
            log(f"[fetch_tmdb] img+ show backdrop: {out.name}")

        show["local_backdrop_path"] = local_rel(out)


def cache_season_images(cfg: AppConfig, season: Dict[str, Any]) -> None:
    poster_path = sanitize_tmdb_path(season.get("poster_path"))
    if not poster_path:
        return

    url = build_img_url(poster_path, f"w{cfg.images.season_width}")
    out = IMG_SHOWS_SEASONS_POSTER / poster_path.lstrip("/")
    if http_download_file(url, out):
        log(f"[fetch_tmdb] img+ season poster: {out.name}")

    season["local_poster_path"] = local_rel(out)


def cache_episode_images(cfg: AppConfig, ep: Dict[str, Any]) -> None:
    still_path = sanitize_tmdb_path(ep.get("still_path"))
    if not still_path:
        return

    url = build_img_url(still_path, f"w{cfg.images.episode_still_w}")
    out = IMG_SHOWS_EPISODES_STILLS / still_path.lstrip("/")
    if http_download_file(url, out):
        log(f"[fetch_tmdb] img+ episode still: {out.name}")

    ep["local_still_path"] = local_rel(out)


def cache_movie_images(cfg: AppConfig, mv: Dict[str, Any]) -> None:
    poster_path = sanitize_tmdb_path(mv.get("poster_path"))
    backdrop_path = sanitize_tmdb_path(mv.get("backdrop_path"))

    if poster_path:
        url = build_img_url(poster_path, f"w{cfg.images.movie_width}")
        out = IMG_MOVIES_POSTER / poster_path.lstrip("/")
        if http_download_file(url, out):
            log(f"[fetch_tmdb] img+ movie poster: {out.name}")

        mv["local_poster_path"] = local_rel(out)

    if backdrop_path:
        url = build_img_url(backdrop_path, f"w{cfg.images.backdrop_w}")
        out = IMG_MOVIES_BACKDROP / backdrop_path.lstrip("/")
        if http_download_file(url, out):
            log(f"[fetch_tmdb] img+ movie backdrop: {out.name}")

        mv["local_backdrop_path"] = local_rel(out)


# ======================================================================================
# [FETCH_TMDB-7.0] Builders: shows + seasons + episodes, movies
# ======================================================================================

def build_show(api_key: str, cfg: AppConfig, tv_id: int) -> Dict[str, Any]:
    # [FETCH_TMDB-7.1] Show core
    show = tmdb_get(api_key, f"/tv/{tv_id}", params={"language": "en-US"})
    out: Dict[str, Any] = {
        "ref_name": show.get("name") or str(tv_id),
        "show_id": tv_id,
        "tmdb_id": tv_id,
        "name": show.get("name"),
        "overview": show.get("overview") or "",
        "status": show.get("status") or "Unknown",
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "number_of_seasons": show.get("number_of_seasons"),
        "number_of_episodes": show.get("number_of_episodes"),
        "poster_path": sanitize_tmdb_path(show.get("poster_path")),
        "backdrop_path": sanitize_tmdb_path(show.get("backdrop_path")),
        "genres": [g.get("name") for g in (show.get("genres") or []) if isinstance(g, dict) and g.get("name")],
        "networks": [n.get("name") for n in (show.get("networks") or []) if isinstance(n, dict) and n.get("name")],
        "seasons": []
    }

    # [FETCH_TMDB-7.2] Image cache (show level)
    cache_show_images(cfg, out)

    # [FETCH_TMDB-7.3] Seasons (skip "season 0" for specials if you want; keep it but flag)
    seasons = show.get("seasons") or []
    for s in seasons:
        if not isinstance(s, dict):
            continue
        season_number = s.get("season_number")
        if season_number is None:
            continue

        season_detail = tmdb_get(api_key, f"/tv/{tv_id}/season/{season_number}", params={"language": "en-US"})
        season_out: Dict[str, Any] = {
            "season_number": season_number,
            "name": season_detail.get("name") or s.get("name") or f"Season {season_number}",
            "overview": season_detail.get("overview") or "",
            "air_date": season_detail.get("air_date"),
            "poster_path": sanitize_tmdb_path(season_detail.get("poster_path") or s.get("poster_path")),
            "episodes": []
        }

        # season image cache
        cache_season_images(cfg, season_out)

        # episodes
        for ep in (season_detail.get("episodes") or []):
            if not isinstance(ep, dict):
                continue
            ep_num = ep.get("episode_number")
            if ep_num is None:
                continue

            ep_out: Dict[str, Any] = {
                "episode_number": ep_num,
                "season_number": season_number,
                "name": ep.get("name") or "",
                "overview": ep.get("overview") or "",
                "air_date": ep.get("air_date"),
                "runtime": ep.get("runtime"),
                "still_path": sanitize_tmdb_path(ep.get("still_path")),
                # links are CONFIG-DRIVEN (authoritative)
                "links": make_episode_links(cfg, tv_id, season_number, ep_num)
            }

            # episode still cache (download missing only)
            cache_episode_images(cfg, ep_out)

            season_out["episodes"].append(ep_out)

        out["seasons"].append(season_out)

    return out


def build_movie(api_key: str, cfg: AppConfig, movie_id: int) -> Dict[str, Any]:
    # [FETCH_TMDB-7.4] Movie core
    mv = tmdb_get(api_key, f"/movie/{movie_id}", params={"language": "en-US"})
    out: Dict[str, Any] = {
        "movie_id": movie_id,
        "tmdb_id": movie_id,
        "title": mv.get("title") or mv.get("original_title") or str(movie_id),
        "overview": mv.get("overview") or "",
        "release_date": mv.get("release_date"),
        "runtime": mv.get("runtime"),
        "poster_path": sanitize_tmdb_path(mv.get("poster_path")),
        "backdrop_path": sanitize_tmdb_path(mv.get("backdrop_path")),
        "genres": [g.get("name") for g in (mv.get("genres") or []) if isinstance(g, dict) and g.get("name")],
        # links are CONFIG-DRIVEN (authoritative)
        "links": make_movie_links(cfg, movie_id),
    }

    cache_movie_images(cfg, out)
    return out


# ======================================================================================
# [FETCH_TMDB-8.0] Output writer + QA sanity checks
# ======================================================================================

def qa_validate_links(cfg: AppConfig, data: Dict[str, Any]) -> List[str]:
    """
    [FETCH_TMDB-8.1] Ensure links in data.json match config bases (catch domain drift).
    Returns list of issues (empty => OK).
    """
    issues: List[str] = []

    base_videasy_tv = cfg.streaming.videasy_tv
    base_vidsrc_tv = cfg.streaming.vidsrc_tv
    base_videasy_movie = cfg.streaming.videasy_movie
    base_vidsrc_movie = cfg.streaming.vidsrc_movie

    # shows
    for show in data.get("shows", []):
        for season in show.get("seasons", []):
            for ep in season.get("episodes", []):
                links = ep.get("links") or {}
                ve = links.get("videasy", "")
                vs = links.get("vidsrc", "")
                if ve and not ve.startswith(base_videasy_tv):
                    issues.append(f"episode videasy base mismatch: {show.get('tmdb_id')} S{season.get('season_number')}E{ep.get('episode_number')}")
                if vs and not vs.startswith(base_vidsrc_tv):
                    issues.append(f"episode vidsrc base mismatch: {show.get('tmdb_id')} S{season.get('season_number')}E{ep.get('episode_number')}")

    # movies
    for mv in data.get("movies", []):
        links = mv.get("links") or {}
        ve = links.get("videasy", "")
        vs = links.get("vidsrc", "")
        if ve and not ve.startswith(base_videasy_movie):
            issues.append(f"movie videasy base mismatch: {mv.get('tmdb_id')}")
        if vs and not vs.startswith(base_vidsrc_movie):
            issues.append(f"movie vidsrc base mismatch: {mv.get('tmdb_id')}")

    return issues


def write_data_json(data: Dict[str, Any]) -> None:
    ensure_dir(DATA_DIR)
    DATA_JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ======================================================================================
# [FETCH_TMDB-9.0] Main
# ======================================================================================

def main() -> int:
    t0 = time.time()

    # [FETCH_TMDB-9.1] Preconditions
    api_key = require_api_key()
    cfg = load_config(CONFIG_PATH)

    # [FETCH_TMDB-9.2] Ensure image directories exist (safe)
    for p in [
        IMG_SHOWS_POSTER, IMG_SHOWS_BACKDROP, IMG_SHOWS_SEASONS_POSTER, IMG_SHOWS_EPISODES_STILLS,
        IMG_MOVIES_POSTER, IMG_MOVIES_BACKDROP
    ]:
        ensure_dir(p)

    # [FETCH_TMDB-9.3] Parse lists
    show_ids = parse_id_list(TV_LIST_PATH)
    movie_ids = parse_id_list(MOVIES_LIST_PATH)

    log(f"[fetch_tmdb] config: vidsrc_tv={cfg.streaming.vidsrc_tv}")
    log(f"[fetch_tmdb] config: videasy_tv={cfg.streaming.videasy_tv}")
    log(f"[fetch_tmdb] config: vidsrc_movie={cfg.streaming.vidsrc_movie}")
    log(f"[fetch_tmdb] config: videasy_movie={cfg.streaming.videasy_movie}")

    log(f"[fetch_tmdb] input: shows={len(show_ids)} movies={len(movie_ids)}")
    if not show_ids and not movie_ids:
        die("No TMDB IDs found in tv_list.txt or movies_list.txt")

    # [FETCH_TMDB-9.4] Build dataset
    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []

    # Shows
    for i, tv_id in enumerate(show_ids, start=1):
        log(f"[fetch_tmdb] show {i}/{len(show_ids)}: {tv_id}")
        try:
            shows_out.append(build_show(api_key, cfg, tv_id))
        except urllib.error.HTTPError as e:
            log(f"[fetch_tmdb] WARN: show fetch failed (HTTP {e.code}) tv_id={tv_id}")
        except Exception as e:
            log(f"[fetch_tmdb] WARN: show fetch failed tv_id={tv_id} ({e})")

    # Movies
    for i, mid in enumerate(movie_ids, start=1):
        log(f"[fetch_tmdb] movie {i}/{len(movie_ids)}: {mid}")
        try:
            movies_out.append(build_movie(api_key, cfg, mid))
        except urllib.error.HTTPError as e:
            log(f"[fetch_tmdb] WARN: movie fetch failed (HTTP {e.code}) movie_id={mid}")
        except Exception as e:
            log(f"[fetch_tmdb] WARN: movie fetch failed movie_id={mid} ({e})")

    # [FETCH_TMDB-9.5] Final data package
    data: Dict[str, Any] = {
        "meta": {
            "built_at": utc_now_iso(),
            "source": "TMDB",
            "shows_count": len(shows_out),
            "movies_count": len(movies_out),
            "config_used": {
                "streaming_services": {
                    "vidsrc_tv": cfg.streaming.vidsrc_tv,
                    "vidsrc_movie": cfg.streaming.vidsrc_movie,
                    "videasy_tv": cfg.streaming.videasy_tv,
                    "videasy_movie": cfg.streaming.videasy_movie
                },
                "image_sizes": {
                    "show_width": cfg.images.show_width,
                    "movie_width": cfg.images.movie_width,
                    "season_width": cfg.images.season_width,
                    "episode_still_w": cfg.images.episode_still_w,
                    "backdrop_w": cfg.images.backdrop_w
                },
                "ui_tuning": {
                    "calendar_button_scale": cfg.ui.calendar_button_scale,
                    "calendar_card_density": cfg.ui.calendar_card_density
                }
            }
        },
        "shows": shows_out,
        "movies": movies_out,
        "live_tv": []
    }

    # [FETCH_TMDB-9.6] QA sanity checks
    issues = qa_validate_links(cfg, data)
    if issues:
        log("[fetch_tmdb] QA: link-base mismatches detected:")
        for it in issues[:25]:
            log(f"  - {it}")
        die("QA failed: link-base mismatches (config vs generated links)")

    # [FETCH_TMDB-9.7] Write output
    write_data_json(data)

    dt = time.time() - t0
    log(f"[fetch_tmdb] OK: wrote {DATA_JSON_PATH} in {dt:.1f}s")
    log(f"[fetch_tmdb] images: shows/poster={IMG_SHOWS_POSTER} | movies/poster={IMG_MOVIES_POSTER}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
