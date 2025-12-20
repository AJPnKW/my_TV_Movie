#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_tmdb.py
# [PROJECT] my_TV_Movie
# [ROLE]    Build static dataset (data/data.json) from TMDB + web/config.json
# [VERSION] v2.6.4
# [UPDATED] 2025-12-20_01-15-00
# [BUILD]   14.01.05
#
# [FIX TARGET]
# - Prevent “worked before, now 0/0” failures by:
#   1) Supporting direct TMDB-ID lines in tv_list.txt / movies_list.txt
#   2) Supporting BOTH TMDB v3 api_key AND v4 bearer token auth from same env vars
#   3) Adding deterministic retries + clearer hard failures (no silent “None storms”)
#
# [ENV]
#   - API_TMDB_KEY   (v3 key OR v4 bearer token; auto-detected)
#   - API_TMDB_TOKEN (optional; treated as bearer if present)
#
# [BINDING]
# - Canonical assets only (assets/...), never "image/"
# - Do not overwrite existing images
# - tv_list.txt parser must tolerate extra spaces and default seasons to ALL if not specified
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
except Exception:
    print("ERROR: Missing dependency 'requests'.", file=sys.stderr)
    print("Install it inside your venv:", file=sys.stderr)
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

ASSETS_DIR = REPO_ROOT / "assets"
ASSETS_POSTERS = ASSETS_DIR / "posters"
ASSETS_BACKDROPS = ASSETS_DIR / "backdrops"
ASSETS_STILLS = ASSETS_DIR / "stills"
ASSETS_LOGOS = ASSETS_DIR / "logos"
ASSETS_ICONS = ASSETS_DIR / "icons"
ASSETS_FALLBACK = ASSETS_DIR / "fallback"

ASSETS_POSTERS_SHOWS = ASSETS_POSTERS / "shows"
ASSETS_POSTERS_SEASONS = ASSETS_POSTERS / "seasons"
ASSETS_POSTERS_MOVIES = ASSETS_POSTERS / "movies"
ASSETS_POSTERS_COLLECTIONS = ASSETS_POSTERS / "collections"

ASSETS_BACKDROPS_SHOWS = ASSETS_BACKDROPS / "shows"
ASSETS_BACKDROPS_MOVIES = ASSETS_BACKDROPS / "movies"

ASSETS_STILLS_EPISODES = ASSETS_STILLS / "episodes"


# -------------------------
# Config + constants
# -------------------------
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"
DEFAULT_TIMEOUT = 30
DEFAULT_SLEEP_SECONDS = 0.15
USER_AGENT = "my_TV_Movie fetch_tmdb.py (static data builder)"

# retries for transient HTTP issues
HTTP_RETRIES = 3
HTTP_BACKOFF = 0.6

RE_TRAILING_YEAR_PARENS = re.compile(r"\((\d{4})\)\s*$")
RE_TRAILING_YEAR_SEP = re.compile(r"[\|\-]\s*(\d{4})\s*$")
RE_TMDB_ID_TOKEN = re.compile(r"(?i)\b(tmdb)\s*[:=]\s*(\d{3,10})\b")
RE_ANY_ID_TOKEN = re.compile(r"\b(\d{3,10})\b")


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
    api_key: Optional[str] = None
    bearer: Optional[str] = None


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
    ASSETS_POSTERS_SHOWS.mkdir(parents=True, exist_ok=True)
    ASSETS_POSTERS_SEASONS.mkdir(parents=True, exist_ok=True)
    ASSETS_POSTERS_MOVIES.mkdir(parents=True, exist_ok=True)
    ASSETS_POSTERS_COLLECTIONS.mkdir(parents=True, exist_ok=True)
    ASSETS_BACKDROPS_SHOWS.mkdir(parents=True, exist_ok=True)
    ASSETS_BACKDROPS_MOVIES.mkdir(parents=True, exist_ok=True)
    ASSETS_STILLS_EPISODES.mkdir(parents=True, exist_ok=True)


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


def load_tmdb_auth() -> TmdbAuth:
    """
    Supports:
      - v3 key via API_TMDB_KEY
      - bearer token via API_TMDB_TOKEN OR API_TMDB_KEY (if it looks like JWT)
    """
    key = (os.getenv("API_TMDB_KEY") or "").strip()
    tok = (os.getenv("API_TMDB_TOKEN") or "").strip()

    # Prefer explicit token
    bearer = tok if tok else ""

    # If API_TMDB_KEY itself looks like a bearer/JWT, treat it as bearer
    if not bearer and key.startswith("ey") and "." in key and len(key) > 40:
        bearer = key
        key = ""

    if bearer:
        return TmdbAuth(mode="bearer", bearer=bearer)

    if key:
        return TmdbAuth(mode="v3", api_key=key)

    raise RuntimeError("Missing TMDB auth. Set API_TMDB_KEY (v3) or API_TMDB_TOKEN (bearer).")


def _request_get(url: str, *, headers: Dict[str, str], params: Optional[Dict[str, Any]] = None) -> "requests.Response":
    last_exc: Optional[Exception] = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            return requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            last_exc = e
            if attempt < HTTP_RETRIES:
                time.sleep(HTTP_BACKOFF * attempt)
    raise RuntimeError(f"HTTP GET failed after {HTTP_RETRIES} tries: {url} ({last_exc})")


def tmdb_get(auth: TmdbAuth, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{TMDB_API_BASE}{path}"
    params = dict(params or {})
    headers = {"User-Agent": USER_AGENT}

    if auth.mode == "bearer":
        headers["Authorization"] = f"Bearer {auth.bearer}"
    else:
        params["api_key"] = auth.api_key

    r = _request_get(url, headers=headers, params=params)
    if r.status_code != 200:
        raise RuntimeError(f"TMDB {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()


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


def tmdb_image_url(width: int, poster_or_backdrop_path: Optional[str]) -> Optional[str]:
    if not poster_or_backdrop_path:
        return None
    size_tag = f"w{int(width)}"
    return f"{TMDB_IMAGE_BASE}{size_tag}{poster_or_backdrop_path}"


def download_if_missing(url: Optional[str], dst: Path) -> bool:
    if not url:
        return False
    if dst.exists() and dst.stat().st_size > 0:
        return False
    try:
        r = _request_get(url, headers={"User-Agent": USER_AGENT})
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
    rel = path.relative_to(REPO_ROOT).as_posix()
    return "/" + rel


# -------------------------
# List parsing
# -------------------------
def parse_title_year_and_optional_tmdb_id(line: str) -> Tuple[str, Optional[int], Optional[int]]:
    s = line.strip()
    if not s:
        return "", None, None

    # Explicit tmdb:id token anywhere in the line
    m = RE_TMDB_ID_TOKEN.search(s)
    if m:
        tmdb_id = int(m.group(2))
        s2 = (s[: m.start()] + s[m.end() :]).strip()
        title, year = parse_title_year(s2)
        return title, year, tmdb_id

    title, year = parse_title_year(s)
    # If line has a lone ID token, prefer it as tmdb_id (unless it looks like a year)
    m2 = RE_ANY_ID_TOKEN.search(s)
    if m2:
        cand = int(m2.group(1))
        if cand < 1900 or cand > 2100:
            return title, year, cand

    return title, year, None


def parse_title_year(line: str) -> Tuple[str, Optional[int]]:
    s = line.strip()
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


def _norm_spaces(s: str) -> str:
    # collapse internal whitespace; keep punctuation as-is
    return re.sub(r"\s+", " ", (s or "").strip())


def parse_season_spec(season_spec_raw: Optional[str]) -> Any:
    """Return "*" for all seasons, or a sorted list[int].

    Accepted inputs (case-insensitive, whitespace-tolerant):
      - "" / None  => "*"  (binding rule: unspecified means ALL seasons)
      - "*"        => "*"
      - "1"        => [1]
      - "1,2,5"    => [1,2,5]
      - "1-3,7"    => [1,2,3,7]
    """
    s = (season_spec_raw or "").strip()
    if not s or s == "*":
        return "*"
    s = s.replace(" ", "")
    out: List[int] = []
    for part in s.split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            if a.isdigit() and b.isdigit():
                lo, hi = int(a), int(b)
                if lo > 0 and hi > 0:
                    if lo <= hi:
                        out.extend(list(range(lo, hi + 1)))
                    else:
                        out.extend(list(range(hi, lo + 1)))
            continue
        if part.isdigit():
            n = int(part)
            if n > 0:
                out.append(n)
    # de-dupe + sort; fallback to "*" if nothing valid parsed
    out = sorted(set(out))
    return out if out else "*"


def parse_tv_line(line: str) -> Optional[Dict[str, Any]]:
    """tv_list.txt line parser.

    Binding source format (comments in tv_list.txt):
      name | tmdb_show_id | season_spec | tvmaze_id

    Robustness requirements:
      - tolerate extra spaces around pipes
      - tolerate missing/blank season_spec -> assume ALL ("*")
      - tolerate lines without pipes by extracting the first ID found
    """
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    # Prefer pipe-delimited format if present
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
        # normalize length
        while len(parts) < 4:
            parts.append("")
        title_raw, id_raw, seasons_raw, tvmaze_raw = parts[0], parts[1], parts[2], parts[3]
        title = _norm_spaces(title_raw)
        title, year, _ = parse_title_year_and_optional_tmdb_id(title)
        tmdb_id = int(id_raw) if (id_raw or "").strip().isdigit() else None
        # if ID missing in col2, fall back to any ID in the full line
        if tmdb_id is None:
            m = RE_ANY_ID_TOKEN.search(raw)
            tmdb_id = int(m.group(1)) if m else None
        seasons = parse_season_spec(seasons_raw)
        tvmaze_id = int(tvmaze_raw) if (tvmaze_raw or "").strip().isdigit() else None
        if not title and tmdb_id is None:
            return None
        row: Dict[str, Any] = {
            "title": title,
            "year": year,
            "tmdb_id": tmdb_id,
            "seasons": seasons,
        }
        if tvmaze_id is not None:
            row["tvmaze_id"] = tvmaze_id
        return row

    # Non-pipe fallback: accept "Title (2025) tmdb:12345" or "Title 12345"
    title, year, tmdb_id = parse_title_year_and_optional_tmdb_id(raw)
    title = _norm_spaces(title)
    if tmdb_id is None:
        m = RE_ANY_ID_TOKEN.search(raw)
        tmdb_id = int(m.group(1)) if m else None
    if not title and tmdb_id is None:
        return None
    return {"title": title, "year": year, "tmdb_id": tmdb_id, "seasons": "*"}


def parse_tv_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        row = parse_tv_line(raw)
        if row is None:
            continue
        # binding rule: unspecified seasons means ALL
        if not row.get("seasons"):
            row["seasons"] = "*"
        rows.append(row)
    return rows


def parse_movie_line(line: str) -> Optional[Dict[str, Any]]:
    """movies_list.txt line parser.

    Binding source format (comments in movies_list.txt):
      name|tmdb_movie_id
    """
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
        while len(parts) < 2:
            parts.append("")
        title_raw, id_raw = parts[0], parts[1]
        title = _norm_spaces(title_raw)
        title, year = parse_title_year(title)
        tmdb_id = int(id_raw) if (id_raw or "").strip().isdigit() else None
        if tmdb_id is None:
            # allow ID in the title if col2 is missing
            _t, _y, tid = parse_title_year_and_optional_tmdb_id(raw)
            tmdb_id = tid
        if tmdb_id:
            return {"tmdb_id": tmdb_id, "title": title, "year": year}
        if title:
            return {"title": title, "year": year}
        return None

    title, year, tmdb_id = parse_title_year_and_optional_tmdb_id(raw)
    title = _norm_spaces(title)
    if tmdb_id:
        return {"tmdb_id": tmdb_id, "title": title, "year": year}
    if title:
        return {"title": title, "year": year}
    return None


def parse_movies_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        row = parse_movie_line(raw)
        if row is None:
            continue
        rows.append(row)
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
# Link builders
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
def validate_link_bases(cfg: Config) -> None:
    for k, v in {
        "vidsrc_tv": cfg.streaming.vidsrc_tv,
        "vidsrc_movie": cfg.streaming.vidsrc_movie,
        "videasy_tv": cfg.streaming.videasy_tv,
        "videasy_movie": cfg.streaming.videasy_movie,
    }.items():
        if not v.startswith("http"):
            raise RuntimeError(f"Config streaming_services.{k} must be a URL. Got: {v!r}")


# -------------------------
# Writer
# -------------------------
def safe_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if orjson is not None:
        data = orjson.dumps(obj, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
        tmp.write_bytes(data)
    else:
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


# -------------------------
# Builders
# -------------------------
def build_show_entry(cfg: Config, auth: TmdbAuth, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id: Optional[int] = item.get("tmdb_id")
    title = item.get("title") or ""
    year = item.get("year")

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

    # Season selection (binding: if not specified in list file => ALL seasons)
    seasons_filter = item.get("seasons", "*")
    want_all_seasons = (seasons_filter == "*" or seasons_filter is None)
    want_seasons: Optional[set] = None
    if (not want_all_seasons) and isinstance(seasons_filter, list):
        want_seasons = set(int(x) for x in seasons_filter if isinstance(x, int) or (isinstance(x, str) and str(x).isdigit()))
        if not want_seasons:
            want_all_seasons = True

    seasons_out: List[Dict[str, Any]] = []
    seasons = details.get("seasons") or []
    for s in seasons:
        season_number = int(s.get("season_number") or 0)
        if season_number <= 0:
            continue

        if (not want_all_seasons) and (want_seasons is not None) and (season_number not in want_seasons):
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

            local_still = None
            if still_path:
                dst = ASSETS_STILLS_EPISODES / still_path.lstrip("/")
                url = tmdb_image_url(cfg.image_sizes.episode_still_w, still_path)
                download_if_missing(url, dst)
                local_still = rel_web_path(dst)

            episodes_out.append(
                {
                    "episode_number": ep_num,
                    "name": ep.get("name"),
                    "overview": ep.get("overview"),
                    "air_date": ep.get("air_date"),
                    "still_tmdb": still_path,
                    "still_local": local_still,
                    "links": build_tv_links(cfg, tmdb_id, season_number, ep_num),
                }
            )

        seasons_out.append(
            {
                "season_number": season_number,
                "name": season_details.get("name"),
                "overview": season_details.get("overview"),
                "air_date": season_details.get("air_date"),
                "poster_tmdb": season_poster_path,
                "poster_local": season_local_poster,
                "episodes": episodes_out,
            }
        )

    return {
        "tmdb_id": tmdb_id,
        "title": details.get("name") or title,
        "original_name": details.get("original_name"),
        "first_air_date": details.get("first_air_date"),
        "overview": details.get("overview"),
        "poster_tmdb": poster_path,
        "poster_local": local_poster,
        "backdrop_tmdb": backdrop_path,
        "backdrop_local": local_backdrop,
        "seasons": seasons_out,
    }


def build_movie_entry(cfg: Config, auth: TmdbAuth, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tmdb_id: Optional[int] = item.get("tmdb_id")
    title = item.get("title") or ""
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
        "title": details.get("title") or title,
        "original_title": details.get("original_title"),
        "release_date": details.get("release_date"),
        "overview": details.get("overview"),
        "poster_tmdb": poster_path,
        "poster_local": local_poster,
        "backdrop_tmdb": backdrop_path,
        "backdrop_local": local_backdrop,
        "links": build_movie_links(cfg, tmdb_id),
    }


# -------------------------
# Main
# -------------------------
def main() -> int:
    setup_logging()
    ensure_dirs()

    try:
        cfg = load_config()
        validate_link_bases(cfg)
        logging.info("[fetch_tmdb] config_hash=%s", cfg.raw_hash[:12])
    except Exception as e:
        logging.error("[fetch_tmdb] config load failed: %s", e)
        return 2

    try:
        auth = load_tmdb_auth()
        logging.info("[fetch_tmdb] tmdb_auth_mode=%s", auth.mode)
    except Exception as e:
        logging.error("[fetch_tmdb] %s", e)
        return 3

    # parse lists
    try:
        tv_rows = parse_tv_list(TV_LIST_PATH)
        movie_rows = parse_movies_list(MOVIES_LIST_PATH)
        livetv_raw = parse_livetv_list_optional(LIVETV_LIST_PATH)
    except Exception as e:
        logging.error("[fetch_tmdb] list parse failed: %s", e)
        return 4

    # preflight
    try:
        _ = tmdb_get(auth, "/configuration")
    except Exception as e:
        logging.error("[fetch_tmdb] TMDB preflight failed: %s", e)
        return 5

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
            "build_timestamp_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": {"script": "fetch_tmdb.py", "script_version": "v2.6.4", "build": "14.01.05"},
            "inputs": {
                "tv_list": str(TV_LIST_PATH.name),
                "movies_list": str(MOVIES_LIST_PATH.name),
                "livetv_list": str(LIVETV_LIST_PATH.name),
                "config_json": str(CONFIG_JSON_PATH.as_posix()),
            },
        },
    }

    # Guard stays, but the script is now much harder to end up at 0/0 unless TMDB is genuinely unreachable
    if len(shows_out) == 0 and len(movies_out) == 0:
        logging.error("[fetch_tmdb] Refusing to write data.json: shows=0 AND movies=0 (bad run)")
        return 6

    safe_write_json(DATA_JSON_PATH, data)
    LAST_REFRESH_PATH.write_text(_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")

    logging.info("[fetch_tmdb] Wrote: %s (shows=%s movies=%s live_tv=%s)", DATA_JSON_PATH, len(shows_out), len(movies_out), len(livetv_raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
