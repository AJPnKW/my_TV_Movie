#!/usr/bin/env python3
# ==============================================================================
# [FILE]        scripts/fetch_tmdb.py
# [PROJECT]     my_TV_Movie
# [ROLE]        Build static dataset (data/data.json) from TMDB + config.json
# [VERSION]     v2.6.2
# [UPDATED]     2025-12-17_16-20-00
# [BUILD]       14.01.05
#
# [DEPENDS ON]
#   - tv_list.txt
#   - movies_list.txt
#   - livetv_list.txt                 (OPTIONAL)
#   - web/config.json                 (source-of-truth for streaming bases + sizing)
#
# [OUTPUTS]
#   - data/data.json                  (ALWAYS generated on success)
#   - data/last_refresh.txt
#   - image/shows/poster/*.jpg
#   - image/shows/backdrop/*.jpg
#   - image/shows/seasons/poster/*.jpg
#   - image/shows/episodes/stills/*.jpg
#   - image/movies/poster/*.jpg
#   - image/movies/backdrop/*.jpg
#   - logs/fetch_tmdb_YYYY-MM-DD_HHMMSS.log.txt
#
# [RULES]
#   - Config drives everything: script reads web/config.json and generates ALL links in data.json
#   - Streaming URL patterns (TV):
#       vidsrc:  https://vidsrc.net/embed/tv/{TMDB_ID}/{season}/{episode}
#       videasy: https://player.videasy.net/tv/{TMDB_ID}/{season}/{episode}
#     Movies:
#       vidsrc:  https://vidsrc.net/embed/movie/{TMDB_ID}
#       videasy: https://player.videasy.net/movie/{TMDB_ID}
#   - Live TV list is OPTIONAL: if missing, continue (do NOT hard-fail)
#   - Image caching: download ONLY missing files (never overwrite existing)
#   - Write data.json atomically (temp -> validate -> replace)
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---- Optional deps (nice-to-have) ----
try:
    import orjson  # type: ignore
except Exception:
    orjson = None  # noqa

try:
    import requests  # type: ignore
except Exception as e:
    print("ERROR: Missing dependency 'requests'. Install it inside your venv:", file=sys.stderr)
    print("  python -m pip install requests", file=sys.stderr)
    raise

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # noqa


# -------------------------
# Paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]

TV_LIST_PATH = REPO_ROOT / "tv_list.txt"
MOVIES_LIST_PATH = REPO_ROOT / "movies_list.txt"
LIVETV_LIST_PATH = REPO_ROOT / "livetv_list.txt"  # OPTIONAL

WEB_DIR = REPO_ROOT / "web"
CONFIG_JSON_PATH = WEB_DIR / "config.json"

DATA_DIR = REPO_ROOT / "data"
DATA_JSON_PATH = DATA_DIR / "data.json"
LAST_REFRESH_PATH = DATA_DIR / "last_refresh.txt"

LOGS_DIR = REPO_ROOT / "logs"

IMAGE_DIR = REPO_ROOT / "image"
IMG_SHOWS = IMAGE_DIR / "shows"
IMG_MOVIES = IMAGE_DIR / "movies"

IMG_SHOWS_POSTER = IMG_SHOWS / "poster"
IMG_SHOWS_BACKDROP = IMG_SHOWS / "backdrop"
IMG_SHOWS_SEASON_POSTER = IMG_SHOWS / "seasons" / "poster"
IMG_SHOWS_EP_STILLS = IMG_SHOWS / "episodes" / "stills"

IMG_MOVIES_POSTER = IMG_MOVIES / "poster"
IMG_MOVIES_BACKDROP = IMG_MOVIES / "backdrop"


# -------------------------
# Config + constants
# -------------------------
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

DEFAULT_TIMEOUT = 30
DEFAULT_SLEEP_SECONDS = 0.20  # gentle on TMDB
USER_AGENT = "my_TV_Movie fetch_tmdb.py (static data builder)"

RE_ID = re.compile(r"\b(\d{3,10})\b")


@dataclass(frozen=True)
class StreamingBases:
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
class Config:
    streaming: StreamingBases
    image_sizes: ImageSizes
    ui: UiTuning
    raw_hash: str


# -------------------------
# Logging
# -------------------------
def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def setup_logging() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"fetch_tmdb_{_now_stamp()}.log.txt"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("[fetch_tmdb] log=%s", log_path)
    return log_path


# -------------------------
# Helpers
# -------------------------
def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    IMG_SHOWS_POSTER.mkdir(parents=True, exist_ok=True)
    IMG_SHOWS_BACKDROP.mkdir(parents=True, exist_ok=True)
    IMG_SHOWS_SEASON_POSTER.mkdir(parents=True, exist_ok=True)
    IMG_SHOWS_EP_STILLS.mkdir(parents=True, exist_ok=True)

    IMG_MOVIES_POSTER.mkdir(parents=True, exist_ok=True)
    IMG_MOVIES_BACKDROP.mkdir(parents=True, exist_ok=True)


def norm_base(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    return url if url.endswith("/") else (url + "/")


def load_config() -> Config:
    if not CONFIG_JSON_PATH.exists():
        raise FileNotFoundError(f"Missing config: {CONFIG_JSON_PATH}")

    raw = read_text_file(CONFIG_JSON_PATH)
    raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    cfg = json.loads(raw)

    ss = cfg.get("streaming_services", {}) or {}
    streaming = StreamingBases(
        vidsrc_tv=norm_base(ss.get("vidsrc_tv", "https://vidsrc.net/embed/tv/")),
        vidsrc_movie=norm_base(ss.get("vidsrc_movie", "https://vidsrc.net/embed/movie/")),
        videasy_tv=norm_base(ss.get("videasy_tv", "https://player.videasy.net/tv/")),
        videasy_movie=norm_base(ss.get("videasy_movie", "https://player.videasy.net/movie/")),
    )

    im = cfg.get("image_sizes", {}) or {}
    image_sizes = ImageSizes(
        show_width=int(im.get("show_width", 185)),
        movie_width=int(im.get("movie_width", 185)),
        season_width=int(im.get("season_width", int(im.get("show_width", 185)))),
        episode_still_w=int(im.get("episode_still_w", 300)),
        backdrop_w=int(im.get("backdrop_w", 780)),
    )

    ui = cfg.get("ui_tuning", {}) or {}
    ui_tuning = UiTuning(
        calendar_button_scale=float(ui.get("calendar_button_scale", 0.75)),
        calendar_card_density=float(ui.get("calendar_card_density", 1.0)),
    )

    return Config(streaming=streaming, image_sizes=image_sizes, ui=ui_tuning, raw_hash=raw_hash)


def get_tmdb_key() -> Optional[str]:
    # Accept both names (some older setups used token vs key)
    k = os.getenv("API_TMDB_KEY") or os.getenv("API_TMDB_TOKEN")
    if k:
        return k.strip()
    return None


def tmdb_get(path: str, api_key: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{TMDB_API_BASE}{path}"
    params = dict(params or {})
    params["api_key"] = api_key

    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"TMDB {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()


def tmdb_search_tv(api_key: str, query: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {"query": query}
    if year:
        params["first_air_date_year"] = year
    j = tmdb_get("/search/tv", api_key, params=params)
    results = j.get("results") or []
    return results[0] if results else None


def tmdb_search_movie(api_key: str, query: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {"query": query}
    if year:
        params["year"] = year
    j = tmdb_get("/search/movie", api_key, params=params)
    results = j.get("results") or []
    return results[0] if results else None


def tmdb_tv_details(api_key: str, tmdb_id: int) -> Dict[str, Any]:
    # include seasons in base response; episodes require per-season call
    return tmdb_get(f"/tv/{tmdb_id}", api_key, params={"language": "en-US"})


def tmdb_tv_season(api_key: str, tmdb_id: int, season_number: int) -> Dict[str, Any]:
    return tmdb_get(f"/tv/{tmdb_id}/season/{season_number}", api_key, params={"language": "en-US"})


def tmdb_movie_details(api_key: str, tmdb_id: int) -> Dict[str, Any]:
    return tmdb_get(f"/movie/{tmdb_id}", api_key, params={"language": "en-US"})


def tmdb_image_url(width: int, poster_or_backdrop_path: Optional[str]) -> Optional[str]:
    if not poster_or_backdrop_path:
        return None
    # TMDB expects sizes like w185, w300, w780, original
    size_tag = f"w{int(width)}"
    return f"{TMDB_IMAGE_BASE}{size_tag}{poster_or_backdrop_path}"


def download_if_missing(url: Optional[str], dst: Path) -> bool:
    if not url:
        return False
    if dst.exists() and dst.stat().st_size > 0:
        return False

    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            logging.warning("[img] download failed %s -> %s (status=%s)", url, dst, r.status_code)
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(r.content)
        return True
    except Exception as e:
        logging.warning("[img] download error %s -> %s (%s)", url, dst, e)
        return False


def rel_web_path(path: Path) -> str:
    # UI uses site-root-relative paths
    rel = path.relative_to(REPO_ROOT).as_posix()
    return "/" + rel


# -------------------------
# List parsing
# -------------------------
def parse_title_year(line: str) -> Tuple[str, Optional[int]]:
    # Accept "Title (2021)" or "Title - 2021" or "Title|2021" etc.
    s = line.strip()
    if not s:
        return "", None

    # year in parentheses
    m = re.search(r"\((\d{4})\)\s*$", s)
    if m:
        y = int(m.group(1))
        title = s[: m.start()].strip()
        return title, y

    # year at end with separator
    m = re.search(r"[\|\-]\s*(\d{4})\s*$", s)
    if m:
        y = int(m.group(1))
        title = s[: m.start()].strip()
        return title, y

    return s, None


def parse_tv_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        title, year = parse_title_year(line)
        if not title:
            continue
        rows.append({"title": title, "year": year})
    return rows


def parse_movies_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        title, year = parse_title_year(line)
        if not title:
            continue
        rows.append({"title": title, "year": year})
    return rows


def parse_livetv_list_optional(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        logging.warning("[fetch_tmdb] livetv_list.txt not found -> continuing (optional). expected=%s", path)
        return []
    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rows.append({"name": line})
    return rows


# -------------------------
# Link generation + QA
# -------------------------
def build_tv_links(cfg: Config, tmdb_id: int, season: int, episode: int) -> Dict[str, str]:
    return {
        "vidsrc": f"{cfg.streaming.vidsrc_tv}{tmdb_id}/{season}/{episode}",
        "videasy": f"{cfg.streaming.videasy_tv}{tmdb_id}/{season}/{episode}",
    }


def build_movie_links(cfg: Config, tmdb_id: int) -> Dict[str, str]:
    return {
        "vidsrc": f"{cfg.streaming.vidsrc_movie}{tmdb_id}",
        "videasy": f"{cfg.streaming.videasy_movie}{tmdb_id}",
    }


def qa_validate_links(cfg: Config, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    allowed_bases = {
        "vidsrc_tv": cfg.streaming.vidsrc_tv,
        "vidsrc_movie": cfg.streaming.vidsrc_movie,
        "videasy_tv": cfg.streaming.videasy_tv,
        "videasy_movie": cfg.streaming.videasy_movie,
    }

    def _starts(url: str, base: str) -> bool:
        return url.startswith(base)

    # shows -> seasons -> episodes
    for s in data.get("shows", []) or []:
        for season in (s.get("seasons") or []):
            for ep in (season.get("episodes") or []):
                links = ep.get("links") or {}
                v1 = links.get("vidsrc") or ""
                v2 = links.get("videasy") or ""
                if v1 and not _starts(v1, allowed_bases["vidsrc_tv"]):
                    errs.append(f"TV vidsrc base mismatch: {v1}")
                if v2 and not _starts(v2, allowed_bases["videasy_tv"]):
                    errs.append(f"TV videasy base mismatch: {v2}")

    for m in data.get("movies", []) or []:
        links = m.get("links") or {}
        v1 = links.get("vidsrc") or ""
        v2 = links.get("videasy") or ""
        if v1 and not _starts(v1, allowed_bases["vidsrc_movie"]):
            errs.append(f"Movie vidsrc base mismatch: {v1}")
        if v2 and not _starts(v2, allowed_bases["videasy_movie"]):
            errs.append(f"Movie videasy base mismatch: {v2}")

    return (len(errs) == 0), errs


# -------------------------
# Builders
# -------------------------
def build_show_entry(cfg: Config, api_key: str, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = item["title"]
    year = item.get("year")

    hit = tmdb_search_tv(api_key, title, year)
    if not hit:
        logging.warning("[show] not found: %s (%s)", title, year)
        return None

    tmdb_id = int(hit["id"])
    details = tmdb_tv_details(api_key, tmdb_id)

    poster_path = details.get("poster_path")
    backdrop_path = details.get("backdrop_path")

    # cache show poster/backdrop
    local_poster = None
    local_backdrop = None

    if poster_path:
        dst = IMG_SHOWS_POSTER / poster_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.show_width, poster_path)
        download_if_missing(url, dst)
        local_poster = rel_web_path(dst)

    if backdrop_path:
        dst = IMG_SHOWS_BACKDROP / backdrop_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.backdrop_w, backdrop_path)
        download_if_missing(url, dst)
        local_backdrop = rel_web_path(dst)

    seasons_out: List[Dict[str, Any]] = []
    seasons = details.get("seasons") or []
    for s in seasons:
        season_number = int(s.get("season_number") or 0)
        if season_number <= 0:
            continue

        season_details = tmdb_tv_season(api_key, tmdb_id, season_number)
        season_poster_path = season_details.get("poster_path")

        season_local_poster = None
        if season_poster_path:
            dst = IMG_SHOWS_SEASON_POSTER / season_poster_path.lstrip("/")
            url = tmdb_image_url(cfg.image_sizes.season_width, season_poster_path)
            download_if_missing(url, dst)
            season_local_poster = rel_web_path(dst)

        eps_out: List[Dict[str, Any]] = []
        for ep in (season_details.get("episodes") or []):
            ep_num = int(ep.get("episode_number") or 0)
            still_path = ep.get("still_path")

            ep_local_still = None
            if still_path:
                dst = IMG_SHOWS_EP_STILLS / still_path.lstrip("/")
                url = tmdb_image_url(cfg.image_sizes.episode_still_w, still_path)
                download_if_missing(url, dst)
                ep_local_still = rel_web_path(dst)

            eps_out.append(
                {
                    "episode_number": ep_num,
                    "name": ep.get("name") or "",
                    "air_date": ep.get("air_date"),
                    "overview": ep.get("overview") or "",
                    "still_path": still_path,
                    "local_still_path": ep_local_still,
                    "links": build_tv_links(cfg, tmdb_id, season_number, ep_num),
                }
            )

        seasons_out.append(
            {
                "season_number": season_number,
                "name": season_details.get("name") or f"Season {season_number}",
                "air_date": season_details.get("air_date"),
                "overview": season_details.get("overview") or "",
                "poster_path": season_poster_path,
                "local_poster_path": season_local_poster,
                "episodes": eps_out,
            }
        )

        time.sleep(DEFAULT_SLEEP_SECONDS)

    return {
        "title": details.get("name") or title,
        "tmdb_id": tmdb_id,
        "first_air_date": details.get("first_air_date"),
        "genres": [g.get("name") for g in (details.get("genres") or []) if g.get("name")],
        "overview": details.get("overview") or "",
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "local_poster_path": local_poster,
        "local_backdrop_path": local_backdrop,
        "seasons": seasons_out,
    }


def build_movie_entry(cfg: Config, api_key: str, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = item["title"]
    year = item.get("year")

    hit = tmdb_search_movie(api_key, title, year)
    if not hit:
        logging.warning("[movie] not found: %s (%s)", title, year)
        return None

    tmdb_id = int(hit["id"])
    details = tmdb_movie_details(api_key, tmdb_id)

    poster_path = details.get("poster_path")
    backdrop_path = details.get("backdrop_path")

    local_poster = None
    local_backdrop = None

    if poster_path:
        dst = IMG_MOVIES_POSTER / poster_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.movie_width, poster_path)
        download_if_missing(url, dst)
        local_poster = rel_web_path(dst)

    if backdrop_path:
        dst = IMG_MOVIES_BACKDROP / backdrop_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.backdrop_w, backdrop_path)
        download_if_missing(url, dst)
        local_backdrop = rel_web_path(dst)

    return {
        "title": details.get("title") or title,
        "tmdb_id": tmdb_id,
        "release_date": details.get("release_date"),
        "genres": [g.get("name") for g in (details.get("genres") or []) if g.get("name")],
        "overview": details.get("overview") or "",
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "local_poster_path": local_poster,
        "local_backdrop_path": local_backdrop,
        "links": build_movie_links(cfg, tmdb_id),
    }


# -------------------------
# Output write (safe)
# -------------------------
def dumps_json(obj: Any) -> str:
    if orjson:
        return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode("utf-8")
    return json.dumps(obj, ensure_ascii=False, indent=2)


def safe_write_json(path: Path, obj: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = dumps_json(obj)

    # Validate not empty / not trivially broken before replacing
    if len(payload.strip()) < 10:
        raise RuntimeError("Refusing to write suspiciously small JSON payload")

    # parse back
    _ = json.loads(payload)

    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


# -------------------------
# Main
# -------------------------
def main() -> int:
    setup_logging()
    ensure_dirs()

    cfg = load_config()
    api_key = get_tmdb_key()
    if not api_key:
        logging.error("Missing API key. Set env var API_TMDB_KEY (or API_TMDB_TOKEN).")
        return 2

    tv_raw = parse_tv_list(TV_LIST_PATH)
    movies_raw = parse_movies_list(MOVIES_LIST_PATH)
    livetv_raw = parse_livetv_list_optional(LIVETV_LIST_PATH)

    logging.info("[fetch_tmdb] Inputs: tv=%s movies=%s livetv=%s", len(tv_raw), len(movies_raw), len(livetv_raw))
    logging.info(
        "[fetch_tmdb] Streaming bases: vidsrc_tv=%s videasy_tv=%s vidsrc_movie=%s videasy_movie=%s",
        cfg.streaming.vidsrc_tv,
        cfg.streaming.videasy_tv,
        cfg.streaming.vidsrc_movie,
        cfg.streaming.videasy_movie,
    )

    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []

    show_iter = tqdm(tv_raw, desc="Shows", unit="show") if tqdm else tv_raw
    for s in show_iter:
        try:
            entry = build_show_entry(cfg, api_key, s)
            if entry:
                shows_out.append(entry)
        except Exception as e:
            logging.exception("[show] error for %s: %s", s, e)
        time.sleep(DEFAULT_SLEEP_SECONDS)

    movie_iter = tqdm(movies_raw, desc="Movies", unit="movie") if tqdm else movies_raw
    for m in movie_iter:
        try:
            entry = build_movie_entry(cfg, api_key, m)
            if entry:
                movies_out.append(entry)
        except Exception as e:
            logging.exception("[movie] error for %s: %s", m, e)
        time.sleep(DEFAULT_SLEEP_SECONDS)

    data: Dict[str, Any] = {
        "meta": {
            "generated_at": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config_sha256": cfg.raw_hash,
            "script_version": "v2.6.2",
            "build": "14.01.05",
            "inputs": {
                "tv_list": str(TV_LIST_PATH.name),
                "movies_list": str(MOVIES_LIST_PATH.name),
                "livetv_list": str(LIVETV_LIST_PATH.name),
            },
        },
        "config_echo": {
            "streaming_services": {
                "vidsrc_tv": cfg.streaming.vidsrc_tv,
                "vidsrc_movie": cfg.streaming.vidsrc_movie,
                "videasy_tv": cfg.streaming.videasy_tv,
                "videasy_movie": cfg.streaming.videasy_movie,
            },
            "image_sizes": {
                "show_width": cfg.image_sizes.show_width,
                "movie_width": cfg.image_sizes.movie_width,
                "season_width": cfg.image_sizes.season_width,
                "episode_still_w": cfg.image_sizes.episode_still_w,
                "backdrop_w": cfg.image_sizes.backdrop_w,
            },
            "ui_tuning": {
                "calendar_button_scale": cfg.ui.calendar_button_scale,
                "calendar_card_density": cfg.ui.calendar_card_density,
            },
        },
        "shows": shows_out,
        "movies": movies_out,
        "live_tv": livetv_raw,
    }

    ok, errs = qa_validate_links(cfg, data)
    if not ok:
        logging.error("[fetch_tmdb] QA FAILED: streaming base mismatch (%s issues)", len(errs))
        for e in errs[:100]:
            logging.error("[fetch_tmdb]   %s", e)
        return 3

    # Refuse to overwrite with empty lists (prevents “data.json blank again”)
    if len(shows_out) == 0 and len(movies_out) == 0:
        logging.error("[fetch_tmdb] Refusing to write data.json: shows=0 AND movies=0 (bad run)")
        return 4

    safe_write_json(DATA_JSON_PATH, data)
    LAST_REFRESH_PATH.write_text(_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")

    logging.info("[fetch_tmdb] Wrote: %s (%s shows, %s movies, %s livetv)",
                 DATA_JSON_PATH, len(shows_out), len(movies_out), len(livetv_raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
