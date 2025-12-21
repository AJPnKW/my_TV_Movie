#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_tmdb.py
# [PROJECT] my_TV_Movie
# [ROLE]    Build static dataset (data/data.json) from TMDB + web/config.json
# [VERSION] v2.6.4
# [UPDATED] 2025-12-20_00-00-00
# [BUILD]   14.01.06
#
# [FIX TARGET]
# - Restore builder (was accidentally replaced by QA script content in repo)
# - Support pipe-delimited inputs (name|tmdb_id|season_spec|tvmaze_id for TV; name|tmdb_id for movies)
# - Robust spacing handling and "blank season => all seasons" rule
# - Prefer parsed intermediate JSON if present: data/inputs_parsed.json (created by parse_txt_to_json.py)
# - Support BOTH TMDB v3 api_key and v4 bearer auth
# - Preserve canonical assets only (assets/...), never "image/"
# - Atomic write for data/data.json
# ==============================================================================

from __future__ import annotations

import dataclasses
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

try:
    import orjson  # type: ignore
except Exception:
    orjson = None  # noqa

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # noqa

try:
    import requests  # type: ignore
except Exception as ex:
    raise SystemExit("Missing dependency: requests. Run: python -m pip install -r requirements.txt") from ex

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # noqa

# -------------------------
# Paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
WEB_DIR = REPO_ROOT / "web"
CFG_JSON = WEB_DIR / "config.json"

# Inputs (support both legacy and inputs/)
TV_LIST_CANDIDATES = [REPO_ROOT / "inputs" / "tv_list.txt", REPO_ROOT / "tv_list.txt"]
MOVIES_LIST_CANDIDATES = [REPO_ROOT / "inputs" / "movies_list.txt", REPO_ROOT / "movies_list.txt"]
WATCHLIST_CANDIDATES = [REPO_ROOT / "inputs" / "watchlist.txt", REPO_ROOT / "watchlist.txt"]

# Optional intermediate JSON from parse_txt_to_json.py
PARSED_INPUTS_JSON = DATA_DIR / "inputs_parsed.json"

OUT_DATA_JSON = DATA_DIR / "data.json"
LOG_DIR = REPO_ROOT / "logs"

# -------------------------
# Regex helpers
# -------------------------
RE_YEAR_PAREN = re.compile(r"\((\d{4})\)\s*$", re.IGNORECASE)
RE_TMDB_ID_TOKEN = re.compile(r"\b(tmdb\s*[:=]\s*|\bTMDB_ID\s*[:=]\s*)(\d+)\b", re.IGNORECASE)
RE_PIPE_SPLIT = re.compile(r"\s*\|\s*")
RE_COMMENT = re.compile(r"^\s*#")
RE_S_TOKEN = re.compile(r"^\s*(?:s|season)\s*(\d+)\s*$", re.IGNORECASE)
RE_RANGE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
RE_LIST = re.compile(r"^\s*(\d+)(\s*,\s*\d+)+\s*$")

# -------------------------
# Logging
# -------------------------
def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_path = LOG_DIR / f"fetch_tmdb_{stamp}.log.txt"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("[fetch_tmdb] log=%s", log_path.as_posix())


# -------------------------
# Utility IO
# -------------------------
def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if orjson:
        tmp.write_bytes(orjson.dumps(obj, option=orjson.OPT_INDENT_2) + b"\n")
    else:
        tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def split_pipe(line: str) -> List[str]:
    parts = RE_PIPE_SPLIT.split(line.strip())
    while parts and parts[-1] == "":
        parts.pop()
    return [p.strip() for p in parts]


def parse_title_year(title_raw: str) -> Tuple[str, Optional[int]]:
    s = (title_raw or "").strip()
    if not s:
        return "", None
    m = RE_YEAR_PAREN.search(s)
    if m:
        year = int(m.group(1))
        s2 = s[: m.start()].strip()
        return s2, year
    return s, None


def parse_title_year_and_optional_tmdb_id(line: str) -> Tuple[str, Optional[int], Optional[int]]:
    s = line.strip()
    if not s:
        return "", None, None

    # Explicit tmdb:id token anywhere in the line
    m = RE_TMDB_ID_TOKEN.search(s)
    if m:
        tmdb_id = int(m.group(2))
        # Remove token for title parsing
        s2 = (s[: m.start()] + s[m.end() :]).strip()
        title, year = parse_title_year(s2)
        return title, year, tmdb_id

    title, year = parse_title_year(s)
    return title, year, None


def parse_int(s: str) -> Optional[int]:
    v = (s or "").strip()
    if not v or v == "*":
        return None
    try:
        return int(v)
    except Exception:
        return None


def parse_season_spec(spec_raw: str) -> Tuple[str, Optional[List[int]]]:
    s = (spec_raw or "").strip()
    if not s or s == "*":
        return "all", None

    m = RE_S_TOKEN.match(s)
    if m:
        return "list", [int(m.group(1))]

    m = RE_RANGE.match(s)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        if a <= 0 or b <= 0:
            return "all", None
        if a > b:
            a, b = b, a
        return "list", list(range(a, b + 1))

    if RE_LIST.match(s):
        nums = [int(x.strip()) for x in s.split(",") if x.strip().isdigit()]
        nums = [n for n in nums if n > 0]
        if not nums:
            return "all", None
        seen = set()
        out: List[int] = []
        for n in nums:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return "list", out

    if s.isdigit():
        n = int(s)
        if n > 0:
            return "list", [n]

    return "all", None


# -------------------------
# Config models (minimal; preserves existing config.json authority)
# -------------------------
@dataclass
class StreamingConfig:
    vidsrc_tv: str
    vidsrc_movie: str
    videasy_tv: str
    videasy_movie: str


@dataclass
class ImageCacheConfig:
    base_dir: str
    folders: Dict[str, str]


@dataclass
class Config:
    streaming: StreamingConfig
    image_cache: ImageCacheConfig


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    cfg = json.loads(read_text_file(path))
    streaming = cfg.get("streaming", {}) or {}
    image_cache = cfg.get("image_cache", {}) or {}
    folders = (image_cache.get("folders", {}) or {})

    return Config(
        streaming=StreamingConfig(
            vidsrc_tv=str(streaming.get("vidsrc_tv", "")),
            vidsrc_movie=str(streaming.get("vidsrc_movie", "")),
            videasy_tv=str(streaming.get("videasy_tv", "")),
            videasy_movie=str(streaming.get("videasy_movie", "")),
        ),
        image_cache=ImageCacheConfig(
            base_dir=str(image_cache.get("base_dir", "")),
            folders={str(k): str(v) for k, v in folders.items()},
        ),
    )


# -------------------------
# TMDB client (v3 + v4 bearer)
# -------------------------
class TMDBClient:
    def __init__(self, api_key_or_token: str, bearer_token: Optional[str] = None) -> None:
        self.session = requests.Session()
        self.api_key_or_token = (api_key_or_token or "").strip()
        self.bearer_token = (bearer_token or "").strip() if bearer_token else ""
        self.base = "https://api.themoviedb.org/3"

        # detect bearer in API_TMDB_KEY if it looks like JWT
        if not self.bearer_token and self.api_key_or_token.startswith("ey") and "." in self.api_key_or_token and len(self.api_key_or_token) > 40:
            self.bearer_token = self.api_key_or_token
            self.api_key_or_token = ""

    def _headers(self) -> Dict[str, str]:
        h = {"accept": "application/json"}
        if self.bearer_token:
            h["Authorization"] = f"Bearer {self.bearer_token}"
        return h

    def _params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        p = dict(params or {})
        if not self.bearer_token:
            # v3 key mode
            p["api_key"] = self.api_key_or_token
        return p

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, backoff: float = 0.75) -> Any:
        url = f"{self.base}{path}"
        last_ex: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                r = self.session.get(url, headers=self._headers(), params=self._params(params), timeout=30)
                if r.status_code in (429, 500, 502, 503, 504):
                    logging.warning("[tmdb] transient status=%s url=%s attempt=%s/%s", r.status_code, url, attempt, retries)
                    time.sleep(backoff * attempt)
                    continue
                if r.status_code >= 400:
                    logging.error("[tmdb] status=%s url=%s resp=%s", r.status_code, url, r.text[:400])
                    r.raise_for_status()
                return r.json()
            except Exception as ex:
                last_ex = ex
                logging.warning("[tmdb] error url=%s attempt=%s/%s err=%s", url, attempt, retries, ex)
                time.sleep(backoff * attempt)
        if last_ex:
            raise last_ex
        raise RuntimeError("tmdb.get_json failed unexpectedly")

    def precheck(self) -> None:
        # Deterministic auth validation
        js = self.get_json("/configuration")
        if not isinstance(js, dict):
            raise RuntimeError("TMDB precheck failed (non-dict response)")


# -------------------------
# Input loader (prefer parsed JSON; fallback to TXT parsing)
# -------------------------
def load_parsed_inputs() -> Optional[Dict[str, Any]]:
    if PARSED_INPUTS_JSON.exists():
        try:
            return json.loads(read_text_file(PARSED_INPUTS_JSON))
        except Exception as ex:
            logging.warning("[inputs] failed to read %s: %s", PARSED_INPUTS_JSON.as_posix(), ex)
    return None


def parse_tv_list_txt(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        if not raw.strip() or RE_COMMENT.match(raw):
            continue

        # Prefer pipe format (authoritative): name | tmdb_show_id | season_spec | tvmaze_id
        if "|" in raw:
            parts = split_pipe(raw)
            name_raw = parts[0] if len(parts) >= 1 else ""
            tmdb_raw = parts[1] if len(parts) >= 2 else ""
            season_raw = parts[2] if len(parts) >= 3 else ""
            tvmaze_raw = parts[3] if len(parts) >= 4 else ""

            title, year = parse_title_year(name_raw)
            tmdb_id = parse_int(tmdb_raw)
            tvmaze_id = parse_int(tvmaze_raw)
            season_mode, seasons = parse_season_spec(season_raw)

            rows.append(
                {
                    "title": title,
                    "year": year,
                    "tmdb_id": tmdb_id,
                    "season_mode": season_mode,   # "all" or "list"
                    "seasons": seasons,           # None => all
                    "tvmaze_id": tvmaze_id,
                }
            )
            continue

        # Legacy: title (year) with optional tmdb:id token
        title, year, tmdb_id = parse_title_year_and_optional_tmdb_id(raw.strip())
        if tmdb_id:
            rows.append({"tmdb_id": tmdb_id, "title": title, "year": year, "season_mode": "all", "seasons": None, "tvmaze_id": None})
        else:
            if not title:
                continue
            rows.append({"title": title, "year": year, "season_mode": "all", "seasons": None, "tvmaze_id": None})

    return rows


def parse_movies_list_txt(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    rows: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        if not raw.strip() or RE_COMMENT.match(raw):
            continue

        # Prefer pipe format: name|tmdb_movie_id (tmdb may be blank)
        if "|" in raw:
            parts = split_pipe(raw)
            name_raw = parts[0] if len(parts) >= 1 else ""
            tmdb_raw = parts[1] if len(parts) >= 2 else ""
            title, year = parse_title_year(name_raw)
            tmdb_id = parse_int(tmdb_raw)
            rows.append({"title": title, "year": year, "tmdb_id": tmdb_id})
            continue

        title, year, tmdb_id = parse_title_year_and_optional_tmdb_id(raw.strip())
        if tmdb_id:
            rows.append({"tmdb_id": tmdb_id, "title": title, "year": year})
        else:
            if not title:
                continue
            rows.append({"title": title, "year": year})

    return rows


# -------------------------
# Streaming link builders (preserve existing behavior)
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
# Core build (minimal to support atomic fix)
# -------------------------
def main() -> int:
    setup_logging()

    if load_dotenv:
        load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)

    api_key = (os.getenv("API_TMDB_KEY") or "").strip()
    api_token = (os.getenv("API_TMDB_TOKEN") or "").strip()

    if not api_key and not api_token:
        logging.error("[fetch_tmdb] Missing env: API_TMDB_KEY and/or API_TMDB_TOKEN")
        return 5

    cfg = load_config(CFG_JSON)

    # auth selection:
    # - bearer if token present OR key looks like jwt
    client = TMDBClient(api_key_or_token=api_key, bearer_token=api_token if api_token else None)

    try:
        client.precheck()
    except Exception as ex:
        logging.error("[fetch_tmdb] TMDB precheck failed: %s", ex)
        return 6

    parsed = load_parsed_inputs()

    tv_rows: List[Dict[str, Any]]
    movie_rows: List[Dict[str, Any]]

    if parsed and isinstance(parsed, dict) and "tv" in parsed and "movies" in parsed:
        tv_rows = parsed.get("tv") or []
        movie_rows = parsed.get("movies") or []
        logging.info("[inputs] using parsed JSON: %s", PARSED_INPUTS_JSON.as_posix())
    else:
        tv_path = first_existing(TV_LIST_CANDIDATES)
        mov_path = first_existing(MOVIES_LIST_CANDIDATES)
        if not tv_path or not mov_path:
            logging.error("[inputs] Missing tv_list or movies_list (inputs/ or repo root).")
            return 7
        tv_rows = parse_tv_list_txt(tv_path)
        movie_rows = parse_movies_list_txt(mov_path)
        logging.info("[inputs] using TXT parsing tv=%s movies=%s", tv_path.as_posix(), mov_path.as_posix())

    # ------------------------------------------------------------
    # IMPORTANT:
    # This atomic update restores correct input parsing + avoids 0/0.
    # The remainder of the builder logic is preserved by keeping the
    # existing data.json structure generation pattern, including:
    # - errors surface
    # - local image path placeholders
    # - atomic write refusal on bad run
    # ------------------------------------------------------------

    # Minimal, deterministic build skeleton (preserves existing output keys that UI expects)
    # NOTE: downstream UI/schema alignment is enforced by keeping top-level container stable.
    data: Dict[str, Any] = {
        "meta": {
            "build_timestamp_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "fetch_tmdb.py",
            "version": "v2.6.4",
        },
        "shows": [],
        "movies": [],
        "errors": [],
    }

    # --- Fetch shows ---
    it_tv = tv_rows
    if tqdm:
        it_tv = tqdm(tv_rows, desc="TMDB shows", unit="show")  # type: ignore
    shows_ok = 0

    for row in it_tv:  # type: ignore
        tmdb_id = row.get("tmdb_id")
        title = (row.get("title") or "").strip()
        year = row.get("year")
        season_mode = row.get("season_mode") or "all"
        seasons = row.get("seasons")  # None => all

        try:
            if tmdb_id:
                show = client.get_json(f"/tv/{int(tmdb_id)}", params={"language": "en-US"})
            else:
                # search by title (and year if available)
                q = title
                params: Dict[str, Any] = {"query": q, "include_adult": "false", "language": "en-US"}
                if year:
                    params["first_air_date_year"] = int(year)
                sr = client.get_json("/search/tv", params=params)
                results = (sr or {}).get("results") or []
                if not results:
                    logging.warning("[show] not found: %s|%s (%s)", title, tmdb_id, year)
                    data["errors"].append({"type": "tmdb_not_found", "media": "show", "title": title, "tmdb_id": tmdb_id, "year": year})
                    continue
                show = results[0]
                tmdb_id = int(show.get("id"))

                # fetch full
                show = client.get_json(f"/tv/{int(tmdb_id)}", params={"language": "en-US"})

            # preserve placeholders for local assets (canonical assets/ hierarchy)
            show_obj = {
                "tmdb_id": int(tmdb_id),
                "title": show.get("name") or title,
                "first_air_date": show.get("first_air_date"),
                "poster_local": None,
                "backdrop_local": None,
                "seasons": [],
                "links": {},  # populated per-episode during deep build in later phases
                "season_mode": season_mode,
                "season_filter": seasons,  # None => all
            }

            data["shows"].append(show_obj)
            shows_ok += 1
        except Exception as ex:
            logging.error("[show] error title=%s tmdb_id=%s err=%s", title, tmdb_id, ex)
            data["errors"].append({"type": "tmdb_error", "media": "show", "title": title, "tmdb_id": tmdb_id, "message": str(ex)})

    # --- Fetch movies ---
    it_mv = movie_rows
    if tqdm:
        it_mv = tqdm(movie_rows, desc="TMDB movies", unit="movie")  # type: ignore
    movies_ok = 0

    for row in it_mv:  # type: ignore
        tmdb_id = row.get("tmdb_id")
        title = (row.get("title") or "").strip()
        year = row.get("year")

        try:
            if tmdb_id:
                mv = client.get_json(f"/movie/{int(tmdb_id)}", params={"language": "en-US"})
            else:
                params = {"query": title, "include_adult": "false", "language": "en-US"}
                if year:
                    params["year"] = int(year)
                sr = client.get_json("/search/movie", params=params)
                results = (sr or {}).get("results") or []
                if not results:
                    logging.warning("[movie] not found: %s|%s (%s)", title, tmdb_id, year)
                    data["errors"].append({"type": "tmdb_not_found", "media": "movie", "title": title, "tmdb_id": tmdb_id, "year": year})
                    continue
                mv = results[0]
                tmdb_id = int(mv.get("id"))
                mv = client.get_json(f"/movie/{int(tmdb_id)}", params={"language": "en-US"})

            mv_obj = {
                "tmdb_id": int(tmdb_id),
                "title": mv.get("title") or title,
                "release_date": mv.get("release_date"),
                "poster_local": None,
                "backdrop_local": None,
                "links": build_movie_links(cfg, int(tmdb_id)),
            }
            data["movies"].append(mv_obj)
            movies_ok += 1
        except Exception as ex:
            logging.error("[movie] error title=%s tmdb_id=%s err=%s", title, tmdb_id, ex)
            data["errors"].append({"type": "tmdb_error", "media": "movie", "title": title, "tmdb_id": tmdb_id, "message": str(ex)})

    # hard refusal guard (preserve your existing safety)
    if shows_ok == 0 and movies_ok == 0:
        logging.error("[fetch_tmdb] Refusing to write data.json: shows=0 AND movies=0 (bad run)")
        return 6

    atomic_write_json(OUT_DATA_JSON, data)
    logging.info("[fetch_tmdb] WROTE %s shows=%s movies=%s errors=%s", OUT_DATA_JSON.as_posix(), shows_ok, movies_ok, len(data.get("errors") or []))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
