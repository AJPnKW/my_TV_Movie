#!/usr/bin/env python3
# =============================================================================
# File:        scripts/fetch_tmdb.py
# Project:     my_TV_Movie
# Version:     v2.7.0 (2025-12-13)
#
# [PURPOSE]
# - Read web/config.json (single source of truth)
# - Generate data/data.json for:
#     - Shows + seasons + episodes (air dates)
#     - Movies
#   with streaming links computed from config (NO hard-coded bases).
#
# - Optional image caching (download missing only)
#   Saves TMDB images locally under:
#     image/shows/poster/
#     image/shows/backdrop/
#     image/shows/seasons/poster/
#     image/shows/episodes/stills/
#     image/movies/poster/
#     image/movies/backdrop/
#
# - Writes local_* fields into data.json so UI can use local images:
#     show.local_poster_path, show.local_backdrop_path
#     season.local_poster_path
#     episode.local_still_path
#     movie.local_poster_path, movie.local_backdrop_path
#
# [REQUIRES]
# - Env var: API_TMDB_KEY
# - pip: requests
#
# =============================================================================

from __future__ import annotations

import json
import logging
import os
import pathlib
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


# =============================================================================
# [S-1.0] Repo paths + logging
# =============================================================================

ROOT = pathlib.Path(__file__).resolve().parents[1]

TV_LIST_PATH = ROOT / "tv_list.txt"
MOVIES_LIST_PATH = ROOT / "movies_list.txt"

WEB_DIR = ROOT / "web"
CONFIG_JSON_PATH = WEB_DIR / "config.json"

DATA_DIR = ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"

IMAGE_DIR = ROOT / "image"

LOG_FMT = "[fetch_tmdb] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT, stream=sys.stdout)

SESSION = requests.Session()


# =============================================================================
# [S-2.0] Config model + defaults (config drives everything)
# =============================================================================

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
class AppConfig:
    streaming: StreamingConfig
    img: ImageSizeConfig
    ui: UiTuningConfig


def _ensure_trailing_slash(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    return u if u.endswith("/") else (u + "/")


def load_app_config() -> AppConfig:
    """
    [S-2.1] Load web/config.json (authoritative).
    Defaults match your confirmed correct bases if file is missing/bad.
    """
    default_streaming = StreamingConfig(
        vidsrc_tv=_ensure_trailing_slash("https://vidsrc.net/embed/tv/"),
        vidsrc_movie=_ensure_trailing_slash("https://vidsrc.net/embed/movie/"),
        videasy_tv=_ensure_trailing_slash("https://player.videasy.net/tv/"),
        videasy_movie=_ensure_trailing_slash("https://player.videasy.net/movie/"),
    )

    default_img = ImageSizeConfig(
        show_width=185,
        movie_width=185,
        season_width=185,
        episode_still_w=300,
        backdrop_w=780,
    )

    default_ui = UiTuningConfig(
        calendar_button_scale=0.75,
        calendar_card_density=1.0,
    )

    if not CONFIG_JSON_PATH.exists():
        logging.warning("Missing web/config.json at %s — using defaults", CONFIG_JSON_PATH)
        return AppConfig(default_streaming, default_img, default_ui)

    try:
        raw = json.loads(CONFIG_JSON_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning("Failed to parse web/config.json (%s) — using defaults", e)
        return AppConfig(default_streaming, default_img, default_ui)

    s = raw.get("streaming_services", {}) if isinstance(raw, dict) else {}
    streaming = StreamingConfig(
        vidsrc_tv=_ensure_trailing_slash(s.get("vidsrc_tv", default_streaming.vidsrc_tv)),
        vidsrc_movie=_ensure_trailing_slash(s.get("vidsrc_movie", default_streaming.vidsrc_movie)),
        videasy_tv=_ensure_trailing_slash(s.get("videasy_tv", default_streaming.videasy_tv)),
        videasy_movie=_ensure_trailing_slash(s.get("videasy_movie", default_streaming.videasy_movie)),
    )

    i = raw.get("image_sizes", {}) if isinstance(raw, dict) else {}
    img = ImageSizeConfig(
        show_width=int(i.get("show_width", default_img.show_width)),
        movie_width=int(i.get("movie_width", default_img.movie_width)),
        season_width=int(i.get("season_width", default_img.season_width)),
        episode_still_w=int(i.get("episode_still_w", default_img.episode_still_w)),
        backdrop_w=int(i.get("backdrop_w", default_img.backdrop_w)),
    )

    u = raw.get("ui_tuning", {}) if isinstance(raw, dict) else {}
    ui = UiTuningConfig(
        calendar_button_scale=float(u.get("calendar_button_scale", default_ui.calendar_button_scale)),
        calendar_card_density=float(u.get("calendar_card_density", default_ui.calendar_card_density)),
    )

    return AppConfig(streaming, img, ui)


# =============================================================================
# [S-3.0] TMDB client + env guard
# =============================================================================

TMDB_API_KEY = os.environ.get("API_TMDB_KEY", "").strip()
if not TMDB_API_KEY:
    print("[fetch_tmdb] ERROR: API_TMDB_KEY is required in env.", file=sys.stderr)
    sys.exit(1)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    [S-3.1] TMDB GET with retry.
    """
    url = f"{TMDB_BASE}{path}"
    params = dict(params or {})
    params.setdefault("api_key", TMDB_API_KEY)

    for attempt in range(1, 4):
        try:
            r = SESSION.get(url, params=params, timeout=20)
            if r.status_code == 404:
                logging.warning("TMDB 404: %s", url)
                return {}
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logging.warning("TMDB GET failed attempt %s/3: %s", attempt, e)
            time.sleep(1 + attempt)

    logging.error("TMDB GET hard-failed: %s", url)
    return {}


# =============================================================================
# [S-4.0] List parsing
# =============================================================================

def parse_tv_list(path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    [S-4.1] tv_list.txt format:
      Name|TMDB_ID|season_spec
      Example:
        Abbott Elementary|125935|5
        Stranger Things|66732|*
    """
    out: List[Dict[str, Any]] = []
    if not path.exists():
        logging.warning("tv_list.txt missing at %s", path)
        return out

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            logging.warning("Skipping tv_list line (too few parts): %r", line)
            continue

        name, tmdb_show_id, season_spec = parts[:3]

        try:
            tmdb_show_id_int = int(tmdb_show_id)
        except ValueError:
            logging.warning("Skipping tv_list line (non-numeric TMDB id): %r", line)
            continue

        out.append(
            {
                "ref_name": name,
                "tmdb_id": tmdb_show_id_int,
                "season_spec": season_spec,
            }
        )

    logging.info("Parsed %s TV lines from tv_list.txt", len(out))
    return out


def parse_movies_list(path: pathlib.Path) -> List[Dict[str, Any]]:
    """
    [S-4.2] movies_list.txt format:
      Title|TMDB_ID
    """
    out: List[Dict[str, Any]] = []
    if not path.exists():
        logging.warning("movies_list.txt missing at %s", path)
        return out

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            logging.warning("Skipping movies_list line (too few parts): %r", line)
            continue

        title, tmdb_movie_id = parts[:2]

        try:
            tmdb_movie_id_int = int(tmdb_movie_id)
        except ValueError:
            logging.warning("Skipping movies_list line (non-numeric TMDB id): %r", line)
            continue

        out.append({"ref_name": title, "tmdb_id": tmdb_movie_id_int})

    logging.info("Parsed %s movie lines from movies_list.txt", len(out))
    return out


def expand_season_spec(spec: str, show_json: Dict[str, Any]) -> List[int]:
    """
    [S-4.3] season_spec:
      "5"     -> [5]
      "1,2"   -> [1,2]
      "*"     -> all non-zero seasons from TMDB
    """
    spec = (spec or "").strip()
    if spec == "*":
        nums: List[int] = []
        for s in show_json.get("seasons", []) or []:
            n = s.get("season_number")
            if isinstance(n, int) and n != 0:
                nums.append(n)
        return sorted(set(nums))

    out: List[int] = []
    for part in spec.split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.append(int(p))
        except ValueError:
            logging.warning("Bad season spec piece: %r in %r", p, spec)
    return sorted(set(out))


# =============================================================================
# [S-5.0] Link builders (CONFIG-DRIVEN, authoritative)
# =============================================================================

TMDB_TV_URL = "https://www.themoviedb.org/tv/{tmdb_id}"
TMDB_EP_URL = "https://www.themoviedb.org/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie/{tmdb_id}"


def build_tv_show_links(tmdb_id: int) -> Dict[str, str]:
    return {"tmdb": TMDB_TV_URL.format(tmdb_id=tmdb_id)}


def build_tv_episode_links(cfg: AppConfig, tmdb_id: int, season_number: int, episode_number: int) -> Dict[str, str]:
    """
    [S-5.1] Correct patterns (per your confirmed examples):
      vidsrc:  https://vidsrc.net/embed/tv/{id}/{season}/{ep}
      videasy: https://player.videasy.net/tv/{id}/{season}/{ep}
    """
    return {
        "tmdb": TMDB_EP_URL.format(tmdb_id=tmdb_id, season_number=season_number, episode_number=episode_number),
        "vidsrc": f"{cfg.streaming.vidsrc_tv}{tmdb_id}/{season_number}/{episode_number}",
        "videasy": f"{cfg.streaming.videasy_tv}{tmdb_id}/{season_number}/{episode_number}",
    }


def build_movie_links(cfg: AppConfig, tmdb_id: int) -> Dict[str, str]:
    """
    [S-5.2] Movie patterns:
      vidsrc:  https://vidsrc.net/embed/movie/{id}
      videasy: https://player.videasy.net/movie/{id}
    """
    return {
        "tmdb": TMDB_MOVIE_URL.format(tmdb_id=tmdb_id),
        "vidsrc": f"{cfg.streaming.vidsrc_movie}{tmdb_id}",
        "videasy": f"{cfg.streaming.videasy_movie}{tmdb_id}",
    }


# =============================================================================
# [S-6.0] Image caching (download missing only)
# =============================================================================

def _tmdb_image_url(width: int, tmdb_path: str) -> str:
    return f"{TMDB_IMAGE_BASE}/w{width}{tmdb_path}"


def _safe_basename(tmdb_path: Optional[str]) -> Optional[str]:
    if not tmdb_path or not isinstance(tmdb_path, str):
        return None
    p = tmdb_path.strip()
    if not p:
        return None
    return pathlib.Path(p).name


def _download_file(url: str, dest: pathlib.Path) -> bool:
    """
    [S-6.1] Download with retry.
    Returns True if downloaded now, False if already existed or failed.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size > 0:
        return False

    for attempt in range(1, 4):
        try:
            r = SESSION.get(url, timeout=30)
            r.raise_for_status()
            dest.write_bytes(r.content)
            if dest.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty")
            return True
        except Exception as e:
            logging.warning("Image download failed attempt %s/3: %s", attempt, e)
            time.sleep(1 + attempt)

    logging.error("Image download hard-failed: %s", url)
    return False


def cache_show_images(cfg: AppConfig, show: Dict[str, Any]) -> None:
    """
    [S-6.2] Adds local_* fields using paths resolvable from /web pages:
      ../image/...
    """
    rel_prefix = "../image"

    poster_name = _safe_basename(show.get("poster_path"))
    if poster_name:
        dest = IMAGE_DIR / "shows" / "poster" / poster_name
        url = _tmdb_image_url(cfg.img.show_width, show["poster_path"])
        _download_file(url, dest)
        show["local_poster_path"] = f"{rel_prefix}/shows/poster/{poster_name}"

    backdrop_name = _safe_basename(show.get("backdrop_path"))
    if backdrop_name:
        dest = IMAGE_DIR / "shows" / "backdrop" / backdrop_name
        url = _tmdb_image_url(cfg.img.backdrop_w, show["backdrop_path"])
        _download_file(url, dest)
        show["local_backdrop_path"] = f"{rel_prefix}/shows/backdrop/{backdrop_name}"

    for season in show.get("seasons", []) or []:
        s_poster_name = _safe_basename(season.get("poster_path"))
        if s_poster_name:
            dest = IMAGE_DIR / "shows" / "seasons" / "poster" / s_poster_name
            url = _tmdb_image_url(cfg.img.season_width, season["poster_path"])
            _download_file(url, dest)
            season["local_poster_path"] = f"{rel_prefix}/shows/seasons/poster/{s_poster_name}"

        for ep in season.get("episodes", []) or []:
            still_name = _safe_basename(ep.get("still_path"))
            if still_name:
                dest = IMAGE_DIR / "shows" / "episodes" / "stills" / still_name
                url = _tmdb_image_url(cfg.img.episode_still_w, ep["still_path"])
                _download_file(url, dest)
                ep["local_still_path"] = f"{rel_prefix}/shows/episodes/stills/{still_name}"


def cache_movie_images(cfg: AppConfig, movie: Dict[str, Any]) -> None:
    """
    [S-6.3] Adds local_* fields using ../image/...
    """
    rel_prefix = "../image"

    poster_name = _safe_basename(movie.get("poster_path"))
    if poster_name:
        dest = IMAGE_DIR / "movies" / "poster" / poster_name
        url = _tmdb_image_url(cfg.img.movie_width, movie["poster_path"])
        _download_file(url, dest)
        movie["local_poster_path"] = f"{rel_prefix}/movies/poster/{poster_name}"

    backdrop_name = _safe_basename(movie.get("backdrop_path"))
    if backdrop_name:
        dest = IMAGE_DIR / "movies" / "backdrop" / backdrop_name
        url = _tmdb_image_url(cfg.img.backdrop_w, movie["backdrop_path"])
        _download_file(url, dest)
        movie["local_backdrop_path"] = f"{rel_prefix}/movies/backdrop/{backdrop_name}"


# =============================================================================
# [S-7.0] Builders: show/movie entries
# =============================================================================

def build_show_entry(cfg: AppConfig, source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id = source["tmdb_id"]
    ref_name = source["ref_name"]
    logging.info("Show: %s [%s]", ref_name, tmdb_id)

    show_json = tmdb_get(f"/tv/{tmdb_id}")
    if not show_json:
        return None

    season_numbers = expand_season_spec(source.get("season_spec", ""), show_json)

    seasons_out: List[Dict[str, Any]] = []
    for sn in season_numbers:
        logging.info("  Season %s", sn)
        season_json = tmdb_get(f"/tv/{tmdb_id}/season/{sn}")
        if not season_json:
            continue

        episodes_out: List[Dict[str, Any]] = []
        for ep in (season_json.get("episodes") or []):
            ep_num = ep.get("episode_number")
            if not isinstance(ep_num, int):
                continue

            episodes_out.append(
                {
                    "episode_number": ep_num,
                    "name": ep.get("name") or "",
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview") or "",
                    "runtime": ep.get("runtime"),
                    "still_path": ep.get("still_path"),
                    "links": build_tv_episode_links(cfg, tmdb_id, sn, ep_num),
                }
            )

        seasons_out.append(
            {
                "season_number": sn,
                "name": season_json.get("name") or f"Season {sn}",
                "air_date": season_json.get("air_date"),
                "episode_count": len(episodes_out),
                "overview": season_json.get("overview") or "",
                "poster_path": season_json.get("poster_path"),
                "episodes": episodes_out,
            }
        )

    genres = [g.get("name") for g in (show_json.get("genres") or []) if g.get("name")]
    networks = [n.get("name") for n in (show_json.get("networks") or []) if n.get("name")]

    entry: Dict[str, Any] = {
        "ref_name": ref_name,
        "show_id": show_json.get("id"),
        "tmdb_id": tmdb_id,
        "name": show_json.get("name") or ref_name,
        "poster_path": show_json.get("poster_path"),
        "backdrop_path": show_json.get("backdrop_path"),
        "status": show_json.get("status"),
        "first_air_date": show_json.get("first_air_date"),
        "genres": genres,
        "overview": show_json.get("overview") or "",
        "networks": networks,
        "links": build_tv_show_links(tmdb_id),
        "seasons": seasons_out,
    }

    cache_show_images(cfg, entry)
    return entry


def build_movie_entry(cfg: AppConfig, source: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id = source["tmdb_id"]
    ref_name = source["ref_name"]
    logging.info("Movie: %s [%s]", ref_name, tmdb_id)

    movie_json = tmdb_get(f"/movie/{tmdb_id}")
    if not movie_json:
        return None

    genres = [g.get("name") for g in (movie_json.get("genres") or []) if g.get("name")]

    entry: Dict[str, Any] = {
        "ref_name": ref_name,
        "movie_id": movie_json.get("id"),
        "tmdb_id": tmdb_id,
        "title": movie_json.get("title") or ref_name,
        "poster_path": movie_json.get("poster_path"),
        "backdrop_path": movie_json.get("backdrop_path"),
        "release_date": movie_json.get("release_date"),
        "status": movie_json.get("status"),
        "runtime": movie_json.get("runtime"),
        "overview": movie_json.get("overview") or "",
        "genres": genres,
        "links": build_movie_links(cfg, tmdb_id),
    }

    cache_movie_images(cfg, entry)
    return entry


# =============================================================================
# [S-8.0] QA: no mixed domains, no legacy patterns
# =============================================================================

LEGACY_MARKERS = (
    "vidsrc.to",
    "videasy.org",
    "player.videasy.net/embed",
    "/embed/tv/",
    "/embed/movie/",
)


def qa_validate_links(cfg: AppConfig, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    [S-8.1] Streaming base must match config bases.
    Also fail if legacy domains/patterns appear anywhere.
    """
    errors: List[str] = []

    raw = json.dumps(data, ensure_ascii=False)
    for m in LEGACY_MARKERS:
        if m in raw:
            errors.append(f"Legacy marker found in output: {m}")

    for s in data.get("shows", []) or []:
        for season in s.get("seasons", []) or []:
            for ep in season.get("episodes", []) or []:
                links = ep.get("links") or {}
                v1 = (links.get("vidsrc") or "").strip()
                v2 = (links.get("videasy") or "").strip()
                if v1 and not v1.startswith(cfg.streaming.vidsrc_tv):
                    errors.append(f"Show ep vidsrc base mismatch: {v1}")
                if v2 and not v2.startswith(cfg.streaming.videasy_tv):
                    errors.append(f"Show ep videasy base mismatch: {v2}")

    for m in data.get("movies", []) or []:
        links = m.get("links") or {}
        v1 = (links.get("vidsrc") or "").strip()
        v2 = (links.get("videasy") or "").strip()
        if v1 and not v1.startswith(cfg.streaming.vidsrc_movie):
            errors.append(f"Movie vidsrc base mismatch: {v1}")
        if v2 and not v2.startswith(cfg.streaming.videasy_movie):
            errors.append(f"Movie videasy base mismatch: {v2}")

    return (len(errors) == 0, errors)


# =============================================================================
# [S-9.0] Main
# =============================================================================

def main() -> None:
    cfg = load_app_config()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    raw_tv = parse_tv_list(TV_LIST_PATH)
    raw_movies = parse_movies_list(MOVIES_LIST_PATH)

    shows_out: List[Dict[str, Any]] = []
    for s in raw_tv:
        entry = build_show_entry(cfg, s)
        if entry:
            shows_out.append(entry)

    movies_out: List[Dict[str, Any]] = []
    for m in raw_movies:
        entry = build_movie_entry(cfg, m)
        if entry:
            movies_out.append(entry)

    data: Dict[str, Any] = {
        "shows": shows_out,
        "movies": movies_out,
        "meta": {
            "shows": len(shows_out),
            "movies": len(movies_out),
            "livetv": 0,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "config": {
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
            },
        },
    }

    ok, errs = qa_validate_links(cfg, data)
    if not ok:
        logging.error("QA failed (%s issues):", len(errs))
        for e in errs[:50]:
            logging.error("  %s", e)
        sys.exit(2)

    DATA_JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info("Wrote %s (shows=%s movies=%s)", DATA_JSON_PATH, len(shows_out), len(movies_out))


if __name__ == "__main__":
    main()
