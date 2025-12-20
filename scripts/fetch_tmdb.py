#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_tmdb.py
# [PROJECT] my_TV_Movie
# [ROLE]    Build static dataset (data/data.json) from TMDB + web/config.json
# [VERSION] v2.6.4
# [UPDATED] 2025-12-20_00-00-00
# [BUILD]   14.01.06
#
# [INPUTS]
#   - tv_list.txt      (format: name | tmdb_show_id | season_spec | tvmaze_id)
#   - movies_list.txt  (format: name|tmdb_movie_id)
#   - livetv_list.txt  (optional)
#   - web/config.json  (authoritative config; read-only)
#
# [OUTPUTS]
#   - data/data.json (atomic write)
#   - data/last_refresh.txt
#   - logs/fetch_tmdb_YYYY-MM-DD_HHMMSS.log.txt
#
# [ENV]
#   - API_TMDB_KEY   (v3 api_key OR bearer token; auto-detected)
#   - API_TMDB_TOKEN (optional; bearer token; if present, preferred for bearer auth)
#
# [BINDING]
#   - Canonical assets only (assets/...), never "image/"
#   - data.json is not edited manually
#   - Atomic write, read-back validation
#   - Parser MUST handle extra spaces + pipe-delimited formats
#   - TV season_spec:
#       * '*' or blank -> ALL seasons
#       * '5' -> season 5 only
#       * '1,3,5' -> seasons list
#       * '2-6' -> seasons range inclusive
#       * If no season_spec provided -> assume ALL seasons
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
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import requests  # type: ignore
except Exception:
    print("ERROR: Missing dependency 'requests'.", file=sys.stderr)
    print("Install: python -m pip install -r requirements.txt", file=sys.stderr)
    raise

try:
    import orjson  # type: ignore
except Exception:
    orjson = None  # noqa

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

# Canonical, binding asset hierarchy
ASSETS_DIR = REPO_ROOT / "assets"

ASSETS_POSTERS_SHOWS = ASSETS_DIR / "posters" / "shows"
ASSETS_POSTERS_SEASONS = ASSETS_DIR / "posters" / "seasons"
ASSETS_POSTERS_MOVIES = ASSETS_DIR / "posters" / "movies"
ASSETS_POSTERS_COLLECTIONS = ASSETS_DIR / "posters" / "collections"

ASSETS_BACKDROPS_SHOWS = ASSETS_DIR / "backdrops" / "shows"
ASSETS_BACKDROPS_MOVIES = ASSETS_DIR / "backdrops" / "movies"

ASSETS_STILLS_EPISODES = ASSETS_DIR / "stills" / "episodes"


# -------------------------
# Constants
# -------------------------
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"
DEFAULT_TIMEOUT = 30
DEFAULT_SLEEP_SECONDS = 0.12
USER_AGENT = "my_TV_Movie fetch_tmdb.py (static data builder)"

HTTP_RETRIES = 3
HTTP_BACKOFF = 0.6

RE_TRAILING_YEAR_PARENS = re.compile(r"\((\d{4})\)\s*$")
RE_TRAILING_YEAR_SEP = re.compile(r"[\|\-]\s*(\d{4})\s*$")

RE_TMDB_ID_TOKEN = re.compile(r"(?i)\b(tmdb)\s*[:=]\s*(\d{3,10})\b")
RE_INT = re.compile(r"^\s*(\d{1,10})\s*$")

RE_SEASON_RANGE = re.compile(r"^\s*(\d{1,3})\s*-\s*(\d{1,3})\s*$")
RE_SEASON_LIST = re.compile(r"^\s*(\d{1,3})\s*(,\s*\d{1,3}\s*)+$")


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


@dataclass(frozen=True)
class TmdbAuth:
    mode: str  # "v3" or "bearer"
    value: str


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
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    logging.info("[fetch_tmdb] log=%s", log_path)
    return log_path


# -------------------------
# Helpers
# -------------------------
def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for d in [
        ASSETS_POSTERS_SHOWS,
        ASSETS_POSTERS_SEASONS,
        ASSETS_POSTERS_MOVIES,
        ASSETS_POSTERS_COLLECTIONS,
        ASSETS_BACKDROPS_SHOWS,
        ASSETS_BACKDROPS_MOVIES,
        ASSETS_STILLS_EPISODES,
    ]:
        d.mkdir(parents=True, exist_ok=True)


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


def _looks_like_bearer(token: str) -> bool:
    t = token.strip()
    if not t:
        return False
    if len(t) >= 60:
        return True
    if t.startswith("eyJ") and len(t) > 40:
        return True
    return False


def load_tmdb_auth_candidates() -> List[TmdbAuth]:
    # We may have BOTH; we will test and pick a working one deterministically.
    v_key = (os.getenv("API_TMDB_KEY") or "").strip()
    v_tok = (os.getenv("API_TMDB_TOKEN") or "").strip()

    cands: List[TmdbAuth] = []

    # Prefer token env as bearer if it looks like bearer
    if v_tok:
        if _looks_like_bearer(v_tok):
            cands.append(TmdbAuth(mode="bearer", value=v_tok))
        else:
            cands.append(TmdbAuth(mode="v3", value=v_tok))

    if v_key:
        if _looks_like_bearer(v_key):
            cands.append(TmdbAuth(mode="bearer", value=v_key))
        else:
            cands.append(TmdbAuth(mode="v3", value=v_key))

    # de-dupe exact duplicates
    uniq: List[TmdbAuth] = []
    seen: Set[Tuple[str, str]] = set()
    for c in cands:
        k = (c.mode, c.value)
        if k not in seen:
            uniq.append(c)
            seen.add(k)

    if not uniq:
        raise RuntimeError("Missing TMDB credentials: set API_TMDB_KEY (or API_TMDB_TOKEN).")
    return uniq


def _http_get_json(url: str, headers: Dict[str, str], params: Dict[str, Any]) -> Dict[str, Any]:
    last_err = ""
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code} {r.text[:250]}"
                raise RuntimeError(last_err)
            return r.json()
        except Exception as e:
            last_err = str(e)
            if attempt < HTTP_RETRIES:
                time.sleep(HTTP_BACKOFF * attempt)
                continue
            raise RuntimeError(last_err) from e


def tmdb_get(auth: TmdbAuth, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{TMDB_API_BASE}{path}"
    params = dict(params or {})
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    if auth.mode == "v3":
        params["api_key"] = auth.value
    else:
        headers["Authorization"] = f"Bearer {auth.value}"

    return _http_get_json(url, headers=headers, params=params)


def tmdb_precheck_pick_auth(cands: List[TmdbAuth]) -> TmdbAuth:
    # Deterministically pick the first candidate that succeeds on /configuration.
    last_err = ""
    for c in cands:
        try:
            _ = tmdb_get(c, "/configuration", params={})
            logging.info("[fetch_tmdb] tmdb_auth_mode=%s (precheck OK)", c.mode)
            return c
        except Exception as e:
            last_err = str(e)
            logging.warning("[fetch_tmdb] precheck failed auth_mode=%s (%s)", c.mode, last_err)
            continue
    raise RuntimeError(f"TMDB precheck failed for all credential candidates. Last error: {last_err}")


def tmdb_search_tv(auth: TmdbAuth, query: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {"query": query}
    if year:
        params["first_air_date_year"] = year
    j = tmdb_get(auth, "/search/tv", params=params)
    results = j.get("results") or []
    return results[0] if results else None


def tmdb_search_movie(auth: TmdbAuth, query: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {"query": query}
    if year:
        params["year"] = year
    j = tmdb_get(auth, "/search/movie", params=params)
    results = j.get("results") or []
    return results[0] if results else None


def tmdb_tv_details(auth: TmdbAuth, tmdb_id: int) -> Dict[str, Any]:
    return tmdb_get(auth, f"/tv/{tmdb_id}", params={"language": "en-US"})


def tmdb_tv_season(auth: TmdbAuth, tmdb_id: int, season_number: int) -> Dict[str, Any]:
    return tmdb_get(auth, f"/tv/{tmdb_id}/season/{season_number}", params={"language": "en-US"})


def tmdb_movie_details(auth: TmdbAuth, tmdb_id: int) -> Dict[str, Any]:
    return tmdb_get(auth, f"/movie/{tmdb_id}", params={"language": "en-US"})


def tmdb_image_url(width: int, tmdb_path: Optional[str]) -> Optional[str]:
    if not tmdb_path:
        return None
    size_tag = f"w{int(width)}"
    return f"{TMDB_IMAGE_BASE}{size_tag}{tmdb_path}"


def download_if_missing(url: Optional[str], dst: Path) -> bool:
    if not url:
        return False
    if dst.exists() and dst.stat().st_size > 0:
        return False

    last_err = ""
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"}, timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                raise RuntimeError(last_err)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(r.content)
            if dst.stat().st_size <= 0:
                raise RuntimeError("wrote 0 bytes")
            return True
        except Exception as e:
            last_err = str(e)
            if attempt < HTTP_RETRIES:
                time.sleep(HTTP_BACKOFF * attempt)
                continue
            logging.warning("[img] download failed %s -> %s (%s)", url, dst, last_err)
            return False
    return False


def rel_web_path(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return "/" + rel


# -------------------------
# Parsing helpers
# -------------------------
def _split_pipes(line: str) -> List[str]:
    # split into trimmed cells, preserving empty trailing cells
    parts = [p.strip() for p in line.split("|")]
    # drop only fully-empty tail beyond 4 (but keep 4-col structure when present)
    while len(parts) > 0 and parts[-1] == "" and len(parts) > 4:
        parts.pop()
    return parts


def parse_title_year(s: str) -> Tuple[str, Optional[int]]:
    s = (s or "").strip()
    if not s:
        return "", None

    m = RE_TRAILING_YEAR_PARENS.search(s)
    if m:
        y = int(m.group(1))
        title = s[: m.start()].strip()
        return title, y

    m = RE_TRAILING_YEAR_SEP.search(s)
    if m:
        y = int(m.group(1))
        title = s[: m.start()].strip()
        return title, y

    return s, None


def parse_season_spec(spec: str) -> Optional[Set[int]]:
    """
    Returns:
      - None => ALL seasons
      - set({n...}) => filtered seasons
    Rules:
      '*' or '' => ALL seasons (None)
      '5' => {5}
      '1,3,5' => {1,3,5}
      '2-6' => {2,3,4,5,6}
    """
    s = (spec or "").strip()
    if not s or s == "*":
        return None

    # tolerate "S5", "Season 5"
    s = re.sub(r"(?i)\bseason\b", "", s).strip()
    s = re.sub(r"(?i)\bs\b", "", s).strip()

    m = RE_SEASON_RANGE.match(s)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        if a <= 0 or b <= 0:
            return None
        lo, hi = (a, b) if a <= b else (b, a)
        return set(range(lo, hi + 1))

    if RE_SEASON_LIST.match(s):
        out: Set[int] = set()
        for part in s.split(","):
            part = part.strip()
            if part.isdigit():
                n = int(part)
                if n > 0:
                    out.add(n)
        return out if out else None

    if s.isdigit():
        n = int(s)
        return {n} if n > 0 else None

    # unknown token -> treat as ALL (but log for visibility)
    logging.warning("[parse] unknown season_spec=%r -> treating as ALL", spec)
    return None


def parse_tv_list(path: Path) -> List[Dict[str, Any]]:
    """
    tv_list.txt binding format:
      name | tmdb_show_id | season_spec | tvmaze_id

    Must handle:
      - extra spaces around pipes
      - missing columns
      - lines like: Beef|*               (season_spec only, no tmdb_id)
      - lines like: Curb|521|           (tmdb_id present, season_spec blank)
      - lines like: Watson | 242867 | * (spaces)
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    rows: List[Dict[str, Any]] = []
    seen_ids: Set[int] = set()
    seen_titles: Set[str] = set()

    for raw in read_text_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = _split_pipes(line)
        # normalize to at most 4 columns
        if len(parts) > 4:
            parts = parts[:4]

        name = parts[0].strip() if len(parts) >= 1 else ""
        c2 = parts[1].strip() if len(parts) >= 2 else ""
        c3 = parts[2].strip() if len(parts) >= 3 else ""
        c4 = parts[3].strip() if len(parts) >= 4 else ""

        title, year = parse_title_year(name)
        tmdb_id: Optional[int] = None
        season_spec_raw: str = ""
        tvmaze_id: Optional[int] = None

        # Decide meaning of column2/3 based on content
        # If col2 is numeric -> tmdb_id
        if c2 and RE_INT.match(c2):
            tmdb_id = int(c2)
            season_spec_raw = c3 or ""
        else:
            # col2 is not numeric; it may be season_spec (like '*') or blank
            season_spec_raw = c2 or ""
            # If col3 is numeric, treat it as tmdb_id (handles "Name|*|12345" style if ever)
            if c3 and RE_INT.match(c3):
                tmdb_id = int(c3)

        # tvmaze_id: if col4 numeric, else ignore
        if c4 and RE_INT.match(c4):
            tvmaze_id = int(c4)

        season_filter = parse_season_spec(season_spec_raw)

        # De-dupe (stable): by tmdb_id when present; otherwise by normalized title
        if tmdb_id and tmdb_id in seen_ids:
            logging.warning("[parse] duplicate tmdb_id in tv_list: %s (%s) -> skipping", tmdb_id, title)
            continue

        key_title = re.sub(r"\s+", " ", (title or "").strip().lower())
        if not tmdb_id and key_title and key_title in seen_titles:
            logging.warning("[parse] duplicate title in tv_list: %s -> skipping", title)
            continue

        row: Dict[str, Any] = {
            "title": title,
            "year": year,
            "tmdb_id": tmdb_id,
            "season_spec": season_spec_raw.strip() if season_spec_raw else "",
            "season_filter": sorted(list(season_filter)) if isinstance(season_filter, set) else None,
            "tvmaze_id": tvmaze_id,
        }

        # Keep minimal correctness: title must exist if no tmdb_id
        if not tmdb_id and not title:
            logging.warning("[parse] skipping tv_list line with no title and no tmdb_id: %r", line)
            continue

        rows.append(row)
        if tmdb_id:
            seen_ids.add(tmdb_id)
        if key_title:
            seen_titles.add(key_title)

    return rows


def parse_movies_list(path: Path) -> List[Dict[str, Any]]:
    """
    movies_list.txt binding format:
      name|tmdb_movie_id

    Must handle:
      - extra spaces around pipes
      - trailing comments/blank lines
      - title with year in parentheses (optional)
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    rows: List[Dict[str, Any]] = []
    seen_ids: Set[int] = set()

    for raw in read_text_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = _split_pipes(line)
        if len(parts) == 1:
            # allow "12345" or "Title (2024)"
            s = parts[0].strip()
            m = RE_INT.match(s)
            if m:
                tmdb_id = int(m.group(1))
                if tmdb_id in seen_ids:
                    continue
                rows.append({"title": "", "year": None, "tmdb_id": tmdb_id})
                seen_ids.add(tmdb_id)
                continue

            title, year = parse_title_year(s)
            rows.append({"title": title, "year": year, "tmdb_id": None})
            continue

        title_raw = parts[0].strip()
        id_raw = parts[1].strip() if len(parts) >= 2 else ""

        title, year = parse_title_year(title_raw)

        tmdb_id = None
        if id_raw and RE_INT.match(id_raw):
            tmdb_id = int(id_raw)

        if tmdb_id and tmdb_id in seen_ids:
            logging.warning("[parse] duplicate tmdb_id in movies_list: %s (%s) -> skipping", tmdb_id, title)
            continue

        # title may be blank when tmdb_id present (allowed)
        if not tmdb_id and not title:
            logging.warning("[parse] skipping movies_list line with no title and no tmdb_id: %r", line)
            continue

        rows.append({"title": title, "year": year, "tmdb_id": tmdb_id})
        if tmdb_id:
            seen_ids.add(tmdb_id)

    return rows


def parse_livetv_list_optional(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        logging.warning("[fetch_tmdb] livetv_list.txt not found -> continuing (optional).")
        return []
    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rows.append({"raw": line})
    return rows


# -------------------------
# Streaming link builders
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


# -------------------------
# QA: link base validation
# -------------------------
def qa_validate_links(cfg: Config, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errs: List[str] = []

    def _starts(url: str, base: str) -> bool:
        return url.startswith(base)

    for s in data.get("shows", []) or []:
        for season in (s.get("seasons") or []):
            for ep in (season.get("episodes") or []):
                links = ep.get("links") or {}
                u = links.get("vidsrc") or ""
                if u and not _starts(u, cfg.streaming.vidsrc_tv):
                    errs.append(f"show ep vidsrc base mismatch: {u}")
                u = links.get("videasy") or ""
                if u and not _starts(u, cfg.streaming.videasy_tv):
                    errs.append(f"show ep videasy base mismatch: {u}")

    for m in data.get("movies", []) or []:
        links = m.get("links") or {}
        u = links.get("vidsrc") or ""
        if u and not _starts(u, cfg.streaming.vidsrc_movie):
            errs.append(f"movie vidsrc base mismatch: {u}")
        u = links.get("videasy") or ""
        if u and not _starts(u, cfg.streaming.videasy_movie):
            errs.append(f"movie videasy base mismatch: {u}")

    return (len(errs) == 0), errs


# -------------------------
# Build show entry
# -------------------------
def build_show_entry(cfg: Config, auth: TmdbAuth, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id: Optional[int] = item.get("tmdb_id")
    title = (item.get("title") or "").strip()
    year = item.get("year")

    # season filter: None => ALL; otherwise set of allowed season numbers
    season_filter_raw = item.get("season_filter")
    season_filter: Optional[Set[int]] = None
    if isinstance(season_filter_raw, list) and all(isinstance(x, int) for x in season_filter_raw):
        season_filter = set(season_filter_raw)

    if tmdb_id:
        details = tmdb_tv_details(auth, int(tmdb_id))
    else:
        hit = tmdb_search_tv(auth, title, year)
        if not hit:
            logging.warning("[show] not found: %s (%s)", title, year)
            return None
        tmdb_id = int(hit["id"])
        details = tmdb_tv_details(auth, tmdb_id)

    poster_path = details.get("poster_path")
    backdrop_path = details.get("backdrop_path")

    local_poster = None
    local_backdrop = None

    if poster_path:
        dst = ASSETS_POSTERS_SHOWS / poster_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.show_width, poster_path)
        download_if_missing(url, dst)
        local_poster = rel_web_path(dst)

    if backdrop_path:
        dst = ASSETS_BACKDROPS_SHOWS / backdrop_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.backdrop_w, backdrop_path)
        download_if_missing(url, dst)
        local_backdrop = rel_web_path(dst)

    seasons_out: List[Dict[str, Any]] = []
    seasons = details.get("seasons") or []

    # Build only requested seasons if filter provided; otherwise ALL seasons
    for s in seasons:
        season_number = int(s.get("season_number") or 0)
        if season_number <= 0:
            continue
        if season_filter is not None and season_number not in season_filter:
            continue

        season_details = tmdb_tv_season(auth, tmdb_id, season_number)
        season_poster_path = season_details.get("poster_path")

        season_local_poster = None
        if season_poster_path:
            dst = ASSETS_POSTERS_SEASONS / season_poster_path.lstrip("/")
            url = tmdb_image_url(cfg.image_sizes.season_width, season_poster_path)
            download_if_missing(url, dst)
            season_local_poster = rel_web_path(dst)

        episodes_out: List[Dict[str, Any]] = []
        for ep in (season_details.get("episodes") or []):
            ep_num = int(ep.get("episode_number") or 0)
            still_path = ep.get("still_path")
            ep_local_still = None

            if still_path:
                dst = ASSETS_STILLS_EPISODES / still_path.lstrip("/")
                url = tmdb_image_url(cfg.image_sizes.episode_still_w, still_path)
                download_if_missing(url, dst)
                ep_local_still = rel_web_path(dst)

            episodes_out.append(
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
                "episodes": episodes_out,
            }
        )

    return {
        "tmdb_id": tmdb_id,
        "name": details.get("name") or title or "",
        "first_air_date": details.get("first_air_date"),
        "overview": details.get("overview") or "",
        "poster_path": poster_path,
        "local_poster_path": local_poster,
        "backdrop_path": backdrop_path,
        "local_backdrop_path": local_backdrop,
        "seasons": seasons_out,
        # keep source ids in the dataset (non-breaking; consumers may ignore)
        "tvmaze_id": item.get("tvmaze_id"),
        "season_spec": item.get("season_spec") or "",
    }


# -------------------------
# Build movie entry
# -------------------------
def build_movie_entry(cfg: Config, auth: TmdbAuth, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id: Optional[int] = item.get("tmdb_id")
    title = (item.get("title") or "").strip()
    year = item.get("year")

    if tmdb_id:
        details = tmdb_movie_details(auth, int(tmdb_id))
    else:
        hit = tmdb_search_movie(auth, title, year)
        if not hit:
            logging.warning("[movie] not found: %s (%s)", title, year)
            return None
        tmdb_id = int(hit["id"])
        details = tmdb_movie_details(auth, tmdb_id)

    poster_path = details.get("poster_path")
    backdrop_path = details.get("backdrop_path")

    local_poster = None
    local_backdrop = None

    if poster_path:
        dst = ASSETS_POSTERS_MOVIES / poster_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.movie_width, poster_path)
        download_if_missing(url, dst)
        local_poster = rel_web_path(dst)

    if backdrop_path:
        dst = ASSETS_BACKDROPS_MOVIES / backdrop_path.lstrip("/")
        url = tmdb_image_url(cfg.image_sizes.backdrop_w, backdrop_path)
        download_if_missing(url, dst)
        local_backdrop = rel_web_path(dst)

    return {
        "tmdb_id": tmdb_id,
        "title": details.get("title") or title or "",
        "release_date": details.get("release_date"),
        "overview": details.get("overview") or "",
        "poster_path": poster_path,
        "local_poster_path": local_poster,
        "backdrop_path": backdrop_path,
        "local_backdrop_path": local_backdrop,
        "links": build_movie_links(cfg, tmdb_id),
    }


# -------------------------
# Atomic write
# -------------------------
def safe_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")

    if orjson is not None:
        tmp.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    else:
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    _ = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def utc_now_iso() -> str:
    # timezone-aware UTC ISO (no utcnow deprecation)
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# -------------------------
# Main
# -------------------------
def main() -> int:
    setup_logging()
    ensure_dirs()

    # config
    try:
        cfg = load_config()
    except Exception as e:
        logging.error("[fetch_tmdb] config load failed: %s", e)
        return 2

    # auth (pick working candidate)
    try:
        cands = load_tmdb_auth_candidates()
        auth = tmdb_precheck_pick_auth(cands)
    except Exception as e:
        logging.error("[fetch_tmdb] %s", e)
        return 3

    # parse lists
    try:
        tv_rows = parse_tv_list(TV_LIST_PATH)
        movie_rows = parse_movies_list(MOVIES_LIST_PATH)
        livetv_raw = parse_livetv_list_optional(LIVETV_LIST_PATH)
        logging.info("[fetch_tmdb] parsed tv=%s movies=%s livetv=%s", len(tv_rows), len(movie_rows), len(livetv_raw))
    except Exception as e:
        logging.error("[fetch_tmdb] list parse failed: %s", e)
        return 4

    shows_out: List[Dict[str, Any]] = []
    movies_out: List[Dict[str, Any]] = []

    # shows
    it = tv_rows
    if tqdm is not None:
        it = tqdm(tv_rows, desc="TMDB shows", unit="show")  # type: ignore
    for s in it:
        try:
            entry = build_show_entry(cfg, auth, s)
            if entry is not None:
                shows_out.append(entry)
        except Exception as e:
            logging.error("[show] hard failure: %s", e)
        time.sleep(DEFAULT_SLEEP_SECONDS)

    # movies
    it2 = movie_rows
    if tqdm is not None:
        it2 = tqdm(movie_rows, desc="TMDB movies", unit="movie")  # type: ignore
    for m in it2:
        try:
            entry = build_movie_entry(cfg, auth, m)
            if entry is not None:
                movies_out.append(entry)
        except Exception as e:
            logging.error("[movie] hard failure: %s", e)
        time.sleep(DEFAULT_SLEEP_SECONDS)

    data: Dict[str, Any] = {
        "shows": shows_out,
        "movies": movies_out,
        "live_tv": livetv_raw,
        "collections": [],
        "people": [],
        "profiles": [],
        "watchlist": [],
        "metadata": {
            "build_timestamp_utc": utc_now_iso(),
            "version": {"script": "fetch_tmdb.py", "script_version": "v2.6.4", "build": "14.01.06"},
            "inputs": {
                "tv_list": str(TV_LIST_PATH.name),
                "movies_list": str(MOVIES_LIST_PATH.name),
                "livetv_list": str(LIVETV_LIST_PATH.name),
                "config_sha256": cfg.raw_hash,
                "tmdb_auth_mode": auth.mode,
            },
            "counts": {
                "shows": len(shows_out),
                "movies": len(movies_out),
                "live_tv": len(livetv_raw),
                "collections": 0,
                "people": 0,
                "profiles": 0,
                "watchlist": 0,
            },
        },
        "errors": [],
    }

    ok, errs = qa_validate_links(cfg, data)
    if not ok:
        logging.error("[fetch_tmdb] QA FAILED: streaming base mismatch (%s issues)", len(errs))
        for e in errs[:50]:
            logging.error("[fetch_tmdb]   %s", e)
        return 5

    if len(shows_out) == 0 and len(movies_out) == 0:
        logging.error("[fetch_tmdb] Refusing to write data.json: shows=0 AND movies=0 (bad run)")
        return 6

    safe_write_json(DATA_JSON_PATH, data)
    LAST_REFRESH_PATH.write_text(_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")

    logging.info("[fetch_tmdb] Wrote: %s (shows=%s movies=%s livetv=%s)", DATA_JSON_PATH, len(shows_out), len(movies_out), len(livetv_raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
