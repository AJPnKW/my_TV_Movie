#!/usr/bin/env python3
# ======================================================================================
# File:        scripts/fetch_tmdb.py
# Project:     my_TV_Movie
#
# Purpose:
#   - Read input lists:
#       - tv_list.txt
#       - movies_list.txt
#       - livetv_list.txt   (OPTIONAL; do not fail build if missing/empty)
#   - Read config:
#       - web/config.json   (streaming base URLs + image sizes + UI tuning + cache options)
#   - Fetch metadata from TMDB and build static outputs:
#       - data/data.json
#       - data/last_refresh.txt
#   - Generate streaming URLs from config (NO hard-coded domains)
#   - Optional: cache TMDB images locally (download missing only) under:
#       - image/shows/poster
#       - image/shows/backdrop
#       - image/shows/seasons/poster
#       - image/shows/episodes/stills
#       - image/movies/poster
#       - image/movies/backdrop
#
# Version:
#   v2.6.1 (2025-12-16)
#
# Compatibility:
#   - Windows / Linux
#   - Python 3.12+
#
# Required env:
#   - API_TMDB_KEY   (TMDB v3 key)  OR
#   - API_TMDB_TOKEN (TMDB v4 read access token)
#
# Logging:
#   - logs/fetch_tmdb.log.txt (append)
#
# Design rules:
#   - Source of truth for streaming base URLs is web/config.json.
#   - data/data.json should contain link fields generated from config (consistent domains).
#   - Never hard-fail for missing Live TV list (optional feature).
# ======================================================================================

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------
# [TMDB-0.0] Repo paths
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

PATH_TV_LIST = REPO_ROOT / "tv_list.txt"
PATH_MOVIES_LIST = REPO_ROOT / "movies_list.txt"
PATH_LIVETV_LIST = REPO_ROOT / "livetv_list.txt"  # NOTE: OPTIONAL (do not fail if missing)

PATH_CONFIG_JSON = REPO_ROOT / "web" / "config.json"

PATH_DATA_DIR = REPO_ROOT / "data"
PATH_DATA_JSON = PATH_DATA_DIR / "data.json"
PATH_LAST_REFRESH = PATH_DATA_DIR / "last_refresh.txt"

PATH_LOG_DIR = REPO_ROOT / "logs"
PATH_LOG_FILE = PATH_LOG_DIR / "fetch_tmdb.log.txt"

PATH_IMAGE_ROOT = REPO_ROOT / "image"

# -----------------------------
# [TMDB-0.1] TMDB endpoints
# -----------------------------
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

# -----------------------------
# [TMDB-0.2] Optional progress bar
# -----------------------------
try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # type: ignore


# ======================================================================================
# [UTIL-1.0] Logging + exits
# ======================================================================================
def _now_utc_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    PATH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{_now_utc_iso()} {msg}"
    print(line)
    with PATH_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def die(msg: str, code: int = 1) -> None:
    log(f"[fetch_tmdb] ERROR: {msg}")
    raise SystemExit(code)


def warn(msg: str) -> None:
    log(f"[fetch_tmdb] WARN: {msg}")


# ======================================================================================
# [CFG-2.0] Config schema + load/validate
# ======================================================================================
@dataclasses.dataclass
class StreamingServices:
    vidsrc_tv: str
    vidsrc_movie: str
    videasy_tv: str
    videasy_movie: str


@dataclasses.dataclass
class ImageSizes:
    show_width: int = 185
    movie_width: int = 185
    season_width: int = 185
    episode_still_w: int = 300
    backdrop_w: int = 780


@dataclasses.dataclass
class UiTuning:
    calendar_button_scale: float = 0.75
    calendar_card_density: float = 1.0


@dataclasses.dataclass
class ImageCache:
    enabled: bool = False
    # if True, UI can prefer local_*_path; if False, local_* may still be written but empty
    write_local_paths: bool = True


@dataclasses.dataclass
class AppConfig:
    streaming_services: StreamingServices
    image_sizes: ImageSizes
    ui_tuning: UiTuning
    image_cache: ImageCache


def load_config() -> AppConfig:
    if not PATH_CONFIG_JSON.exists():
        die(f"Missing config: {PATH_CONFIG_JSON}")

    try:
        raw = json.loads(PATH_CONFIG_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Invalid JSON in {PATH_CONFIG_JSON}: {e}")

    ss = raw.get("streaming_services", {}) or {}
    required = ["vidsrc_tv", "vidsrc_movie", "videasy_tv", "videasy_movie"]
    missing = [k for k in required if not str(ss.get(k, "")).strip()]
    if missing:
        die(f"config.json missing required streaming_services keys: {', '.join(missing)}")

    streaming = StreamingServices(
        vidsrc_tv=str(ss["vidsrc_tv"]).strip(),
        vidsrc_movie=str(ss["vidsrc_movie"]).strip(),
        videasy_tv=str(ss["videasy_tv"]).strip(),
        videasy_movie=str(ss["videasy_movie"]).strip(),
    )

    img = raw.get("image_sizes", {}) or {}
    image_sizes = ImageSizes(
        show_width=int(img.get("show_width", 185)),
        movie_width=int(img.get("movie_width", 185)),
        season_width=int(img.get("season_width", 185)),
        episode_still_w=int(img.get("episode_still_w", 300)),
        backdrop_w=int(img.get("backdrop_w", 780)),
    )

    ui = raw.get("ui_tuning", {}) or {}
    ui_tuning = UiTuning(
        calendar_button_scale=float(ui.get("calendar_button_scale", 0.75)),
        calendar_card_density=float(ui.get("calendar_card_density", 1.0)),
    )

    cache = raw.get("image_cache", {}) or {}
    image_cache = ImageCache(
        enabled=bool(cache.get("enabled", False)),
        write_local_paths=bool(cache.get("write_local_paths", True)),
    )

    return AppConfig(
        streaming_services=streaming,
        image_sizes=image_sizes,
        ui_tuning=ui_tuning,
        image_cache=image_cache,
    )


# ======================================================================================
# [LIST-3.0] Input list parsing
# ======================================================================================
_ID_RE = re.compile(r"(\d+)")


def parse_list_file(path: Path) -> List[Tuple[str, int]]:
    """
    Accepts flexible formats, examples:
      - Abbott Elementary | 125935
      - 125935 | Abbott Elementary
      - 125935
      - Abbott Elementary (125935)
    Ignores blank lines and # comments.
    Returns: [(ref_name, tmdb_id), ...]
    """
    if not path.exists():
        die(f"Missing required list file: {path}")

    out: List[Tuple[str, int]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # normalize separators
        parts = [p.strip() for p in re.split(r"[|,;\t]", line) if p.strip()]
        joined = " ".join(parts) if parts else line

        m = _ID_RE.search(joined)
        if not m:
            warn(f"Skipping line without TMDB id in {path.name}: {raw}")
            continue
        tmdb_id = int(m.group(1))

        # name: prefer non-numeric text
        name = re.sub(r"\b\d+\b", "", joined).strip(" -|,;()[]\t") or str(tmdb_id)
        out.append((name, tmdb_id))

    # de-dupe by id, keep first name
    seen: set[int] = set()
    deduped: List[Tuple[str, int]] = []
    for name, tid in out:
        if tid in seen:
            continue
        seen.add(tid)
        deduped.append((name, tid))
    return deduped


def parse_livetv_optional(path: Path) -> List[str]:
    """
    OPTIONAL input.
    If missing, return [] and do not fail.
    """
    if not path.exists():
        warn(f"Live TV list not found (optional): {path.name}")
        return []
    items: List[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


# ======================================================================================
# [HTTP-4.0] TMDB client
# ======================================================================================
class TmdbClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("API_TMDB_KEY", "").strip()
        self.api_token = os.getenv("API_TMDB_TOKEN", "").strip()

        if not self.api_key and not self.api_token:
            die("API_TMDB_KEY or API_TMDB_TOKEN is required in env.")

        import requests  # local import so error is obvious if missing
        self._requests = requests
        self._session = requests.Session()

        self._headers = {"Accept": "application/json"}
        if self.api_token:
            # v4 token for v3 endpoints works via Authorization bearer
            self._headers["Authorization"] = f"Bearer {self.api_token}"

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = dict(params or {})
        if self.api_key and "api_key" not in params:
            params["api_key"] = self.api_key

        url = f"{TMDB_API_BASE}{path}"
        r = self._session.get(url, headers=self._headers, params=params, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"TMDB {r.status_code} for {url}: {r.text[:200]}")
        return r.json()

    def download(self, url: str, dest: Path) -> bool:
        """
        Download only if missing. Returns True if downloaded, False if already existed.
        """
        if dest.exists() and dest.stat().st_size > 0:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = self._session.get(url, headers=self._headers, timeout=90)
        if r.status_code >= 400:
            raise RuntimeError(f"TMDB image {r.status_code} for {url}")
        dest.write_bytes(r.content)
        return True


# ======================================================================================
# [URL-5.0] Streaming URLs (config-driven only)
# ======================================================================================
def _join_base(base: str, suffix: str) -> str:
    base = base.strip()
    if not base.endswith("/"):
        base += "/"
    return base + suffix.lstrip("/")


def build_tv_links(cfg: AppConfig, tmdb_id: int, season_number: int, episode_number: int) -> Dict[str, str]:
    # Required format (user-confirmed):
    #   vidsrc.net/embed/tv/ID/season/ep
    #   player.videasy.net/tv/ID/season/ep
    suffix = f"{tmdb_id}/{season_number}/{episode_number}"
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}",
        "vidsrc": _join_base(cfg.streaming_services.vidsrc_tv, suffix),
        "videasy": _join_base(cfg.streaming_services.videasy_tv, suffix),
    }


def build_movie_links(cfg: AppConfig, tmdb_id: int) -> Dict[str, str]:
    # Expected format:
    #   vidsrc.net/embed/movie/ID
    #   player.videasy.net/movie/ID
    suffix = f"{tmdb_id}"
    return {
        "tmdb": f"https://www.themoviedb.org/movie/{tmdb_id}",
        "vidsrc": _join_base(cfg.streaming_services.vidsrc_movie, suffix),
        "videasy": _join_base(cfg.streaming_services.videasy_movie, suffix),
    }


# ======================================================================================
# [IMG-6.0] Image caching + local paths
# ======================================================================================
def _img_url(width: int, tmdb_path: str) -> str:
    # width -> "w185", "w300", "w780", etc.
    key = f"w{int(width)}"
    return f"{TMDB_IMAGE_BASE}{key}{tmdb_path}"


def _safe_filename(tmdb_path: str) -> str:
    # tmdb_path already includes leading "/", keep basename only
    name = Path(tmdb_path).name
    if not name:
        name = hashlib.sha1(tmdb_path.encode("utf-8")).hexdigest() + ".jpg"
    return name


def rel_path_from_web_to_repo_image(rel_under_image: Path) -> str:
    """
    web/* files need to reference images using relative path up to repo root.
    From web/index.html => ../image/...
    """
    return str(Path("..") / "image" / rel_under_image).replace("\\", "/")


def cache_show_images(client: TmdbClient, cfg: AppConfig, show: Dict[str, Any]) -> None:
    if not cfg.image_cache.write_local_paths:
        return

    def _cache(subdir: Path, tmdb_path: Optional[str], out_key: str, width: int) -> None:
        if not tmdb_path:
            return
        fn = _safe_filename(tmdb_path)
        rel_under_image = subdir / fn
        show[out_key] = rel_path_from_web_to_repo_image(rel_under_image)

        if not cfg.image_cache.enabled:
            return

        dest = PATH_IMAGE_ROOT / rel_under_image
        url = _img_url(width, tmdb_path)
        try:
            downloaded = client.download(url, dest)
            if downloaded:
                log(f"[cache] + {dest.as_posix()}")
        except Exception as e:
            warn(f"Image download failed (show): {url} -> {e}")

    _cache(Path("shows/poster"), show.get("poster_path"), "local_poster_path", cfg.image_sizes.show_width)
    _cache(Path("shows/backdrop"), show.get("backdrop_path"), "local_backdrop_path", cfg.image_sizes.backdrop_w)

    for season in show.get("seasons", []) or []:
        sp = season.get("poster_path")
        if sp:
            fn = _safe_filename(sp)
            rel_under_image = Path("shows/seasons/poster") / fn
            season["local_poster_path"] = rel_path_from_web_to_repo_image(rel_under_image)
            if cfg.image_cache.enabled:
                dest = PATH_IMAGE_ROOT / rel_under_image
                url = _img_url(cfg.image_sizes.season_width, sp)
                try:
                    downloaded = client.download(url, dest)
                    if downloaded:
                        log(f"[cache] + {dest.as_posix()}")
                except Exception as e:
                    warn(f"Image download failed (season): {url} -> {e}")

        for ep in season.get("episodes", []) or []:
            st = ep.get("still_path")
            if not st:
                continue
            fn = _safe_filename(st)
            rel_under_image = Path("shows/episodes/stills") / fn
            ep["local_still_path"] = rel_path_from_web_to_repo_image(rel_under_image)
            if cfg.image_cache.enabled:
                dest = PATH_IMAGE_ROOT / rel_under_image
                url = _img_url(cfg.image_sizes.episode_still_w, st)
                try:
                    downloaded = client.download(url, dest)
                    if downloaded:
                        log(f"[cache] + {dest.as_posix()}")
                except Exception as e:
                    warn(f"Image download failed (episode): {url} -> {e}")


def cache_movie_images(client: TmdbClient, cfg: AppConfig, movie: Dict[str, Any]) -> None:
    if not cfg.image_cache.write_local_paths:
        return

    def _cache(subdir: Path, tmdb_path: Optional[str], out_key: str, width: int) -> None:
        if not tmdb_path:
            return
        fn = _safe_filename(tmdb_path)
        rel_under_image = subdir / fn
        movie[out_key] = rel_path_from_web_to_repo_image(rel_under_image)

        if not cfg.image_cache.enabled:
            return

        dest = PATH_IMAGE_ROOT / rel_under_image
        url = _img_url(width, tmdb_path)
        try:
            downloaded = client.download(url, dest)
            if downloaded:
                log(f"[cache] + {dest.as_posix()}")
        except Exception as e:
            warn(f"Image download failed (movie): {url} -> {e}")

    _cache(Path("movies/poster"), movie.get("poster_path"), "local_poster_path", cfg.image_sizes.movie_width)
    _cache(Path("movies/backdrop"), movie.get("backdrop_path"), "local_backdrop_path", cfg.image_sizes.backdrop_w)


# ======================================================================================
# [BUILD-7.0] Build show + seasons + episodes
# ======================================================================================
def fetch_show(client: TmdbClient, cfg: AppConfig, ref_name: str, tmdb_id: int) -> Dict[str, Any]:
    show = client.get_json(f"/tv/{tmdb_id}", params={"language": "en-US"})

    out: Dict[str, Any] = {
        "ref_name": ref_name,
        "tmdb_id": tmdb_id,
        "show_id": tmdb_id,
        "name": show.get("name") or ref_name,
        "original_name": show.get("original_name"),
        "overview": show.get("overview"),
        "first_air_date": show.get("first_air_date"),
        "last_air_date": show.get("last_air_date"),
        "status": show.get("status"),
        "in_production": show.get("in_production"),
        "number_of_seasons": show.get("number_of_seasons"),
        "number_of_episodes": show.get("number_of_episodes"),
        "genres": [g.get("name") for g in (show.get("genres") or []) if g.get("name")],
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "networks": [n.get("name") for n in (show.get("networks") or []) if n.get("name")],
        "seasons": [],
    }

    seasons = show.get("seasons") or []
    seasons_out: List[Dict[str, Any]] = []

    for s in seasons:
        season_number = int(s.get("season_number") or 0)
        if season_number <= 0:
            continue

        season = client.get_json(f"/tv/{tmdb_id}/season/{season_number}", params={"language": "en-US"})
        season_out: Dict[str, Any] = {
            "season_number": season_number,
            "name": season.get("name"),
            "overview": season.get("overview"),
            "air_date": season.get("air_date"),
            "poster_path": season.get("poster_path") or s.get("poster_path"),
            "episodes": [],
        }

        episodes_out: List[Dict[str, Any]] = []
        for ep in (season.get("episodes") or []):
            ep_num = int(ep.get("episode_number") or 0)
            if ep_num <= 0:
                continue

            ep_out: Dict[str, Any] = {
                "season_number": season_number,
                "episode_number": ep_num,
                "name": ep.get("name"),
                "air_date": ep.get("air_date"),
                "overview": ep.get("overview"),
                "runtime": ep.get("runtime"),  # often None in season payload; kept for schema continuity
                "still_path": ep.get("still_path"),
                "links": build_tv_links(cfg, tmdb_id, season_number, ep_num),
            }
            episodes_out.append(ep_out)

        season_out["episodes"] = episodes_out
        seasons_out.append(season_out)

    out["seasons"] = seasons_out

    # local cache paths (and optionally download)
    cache_show_images(client, cfg, out)
    return out


def fetch_movie(client: TmdbClient, cfg: AppConfig, ref_name: str, tmdb_id: int) -> Dict[str, Any]:
    m = client.get_json(f"/movie/{tmdb_id}", params={"language": "en-US"})

    out: Dict[str, Any] = {
        "ref_name": ref_name,
        "tmdb_id": tmdb_id,
        "movie_id": tmdb_id,
        "name": m.get("title") or ref_name,
        "original_title": m.get("original_title"),
        "overview": m.get("overview"),
        "release_date": m.get("release_date"),
        "status": m.get("status"),
        "runtime": m.get("runtime"),
        "genres": [g.get("name") for g in (m.get("genres") or []) if g.get("name")],
        "poster_path": m.get("poster_path"),
        "backdrop_path": m.get("backdrop_path"),
        "links": build_movie_links(cfg, tmdb_id),
    }

    cache_movie_images(client, cfg, out)
    return out


# ======================================================================================
# [OUT-8.0] Write outputs
# ======================================================================================
def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    t0 = time.time()
    log("[fetch_tmdb] START")

    cfg = load_config()
    log(f"[fetch_tmdb] config: web/config.json loaded (image_cache.enabled={cfg.image_cache.enabled})")

    tv_items = parse_list_file(PATH_TV_LIST)
    movie_items = parse_list_file(PATH_MOVIES_LIST)
    livetv_items = parse_livetv_optional(PATH_LIVETV_LIST)

    client = TmdbClient()

    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []

    # progress helper
    def _iter(items: List[Tuple[str, int]], label: str):
        if tqdm:
            return tqdm(items, desc=label)
        return items

    # build shows
    for ref_name, tmdb_id in _iter(tv_items, "TMDB Shows"):
        try:
            shows_out.append(fetch_show(client, cfg, ref_name, tmdb_id))
        except Exception as e:
            warn(f"Show fetch failed tmdb_id={tmdb_id} ({ref_name}): {e}")

    # build movies
    for ref_name, tmdb_id in _iter(movie_items, "TMDB Movies"):
        try:
            movies_out.append(fetch_movie(client, cfg, ref_name, tmdb_id))
        except Exception as e:
            warn(f"Movie fetch failed tmdb_id={tmdb_id} ({ref_name}): {e}")

    built_at = _now_utc_iso()
    meta = {
        "builder": "scripts/fetch_tmdb.py",
        "version": "v2.6.1",
        "built_at": built_at,
        "counts": {"shows": len(shows_out), "movies": len(movies_out), "livetv": len(livetv_items)},
        "config_snapshot": {
            "streaming_services": dataclasses.asdict(cfg.streaming_services),
            "image_sizes": dataclasses.asdict(cfg.image_sizes),
            "ui_tuning": dataclasses.asdict(cfg.ui_tuning),
            "image_cache": dataclasses.asdict(cfg.image_cache),
        },
    }

    payload = {
        "meta": meta,
        "shows": shows_out,
        "movies": movies_out,
        "livetv": livetv_items,
    }

    write_json(PATH_DATA_JSON, payload)
    PATH_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PATH_LAST_REFRESH.write_text(built_at + "\n", encoding="utf-8")

    dt = time.time() - t0
    log(f"[fetch_tmdb] DONE in {dt:.1f}s -> data/data.json ({PATH_DATA_JSON.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        die("Interrupted by user", 130)
