#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_tmdb.py
# [PROJECT] my_TV_Movie
# [ROLE]    Build static dataset (data/data.json) from TMDB + web/config.json
# [VERSION] v2.9.0
# [UPDATED] 2026-01-24
# [BUILD]   24.01.01
#
# [PATCH GOALS]
# - Fix broken streaming links caused by config key mismatch (streaming vs streaming_services)
# - Compute robust streaming URLs (supports {tmdb_id}/{season}/{episode} placeholders or simple base+suffix)
# - Add core rich TMDB fields (NO translations) to support UI cards:
#   * movie: imdb_id, poster_path, backdrop_path, overview, status, popularity, vote_average, vote_count, genres, runtime, homepage
#   * tv: tvdb_id, poster_path, backdrop_path, overview, status, popularity, vote_average, vote_count, genres, networks, created_by,
#         origin_country, in_production, number_of_seasons, number_of_episodes, episode_run_time, last_air_date,
#         next_episode_to_air, last_episode_to_air, type, homepage
# - Compute poster_local/backdrop_local using config image_cache folders + TMDB path basename
# - Preserve existing minimal fields and placeholders (seasons:[], links:{} for TV)
#
# [NOTE]
# Deep-build of seasons/episodes is NOT implemented here (still a separate stage if you add it later).
# ==============================================================================

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
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]

WEB_DIR = REPO_ROOT / "web"
DATA_DIR = REPO_ROOT / "data"

# Inputs (support both legacy and inputs/)
TV_LIST_CANDIDATES = [REPO_ROOT / "inputs" / "tv_list.txt", REPO_ROOT / "tv_list.txt"]
MOVIES_LIST_CANDIDATES = [REPO_ROOT / "inputs" / "movies_list.txt", REPO_ROOT / "movies_list.txt"]
WATCHLIST_CANDIDATES = [REPO_ROOT / "inputs" / "watchlist.txt", REPO_ROOT / "watchlist.txt"]

# Optional intermediate JSON from parse_txt_to_json.py
PARSED_INPUTS_JSON = DATA_DIR / "inputs_parsed.json"
INPUTS_JSON_DEFAULT = DATA_DIR / "inputs.json"

OUT_DATA_JSON = DATA_DIR / "data.json"
LOG_DIR = REPO_ROOT / "logs"

CONFIG_JSON = WEB_DIR / "config.json"

# -------------------------
# Regex helpers
# -------------------------
RE_COMMENT = re.compile(r"^\s*#")
RE_PIPE = re.compile(r"\s*\|\s*")
RE_WS = re.compile(r"\s+")

# -------------------------
# Logging
# -------------------------
def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now(_dt.UTC).strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"fetch_tmdb.{ts}.log.txt"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    logging.info("[init] repo_root=%s", REPO_ROOT)
    logging.info("[init] log=%s", log_path)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_json_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if orjson:
        b = orjson.dumps(obj, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)  # type: ignore
        tmp.write_bytes(b)
    else:
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


# -------------------------
# Config
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


def _coalesce_streaming(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical keys: cfg['streaming'].*
    Backward-compat: cfg['streaming_services'].*
    Precedence: streaming.* overrides streaming_services.*
    """
    s1 = cfg.get("streaming", {}) or {}
    s2 = cfg.get("streaming_services", {}) or {}
    out: Dict[str, Any] = {}
    for k in ("vidsrc_tv", "vidsrc_movie", "videasy_tv", "videasy_movie"):
        v = s1.get(k)
        if v in (None, ""):
            v = s2.get(k)
        out[k] = "" if v is None else str(v)
    return out


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    cfg = json.loads(read_text_file(path))

    streaming = _coalesce_streaming(cfg)

    image_cache = cfg.get("image_cache", {}) or {}
    folders = (image_cache.get("folders", {}) or {})
    base_dir = str(image_cache.get("base_dir", ""))

    return Config(
        streaming=StreamingConfig(
            vidsrc_tv=str(streaming.get("vidsrc_tv", "")),
            vidsrc_movie=str(streaming.get("vidsrc_movie", "")),
            videasy_tv=str(streaming.get("videasy_tv", "")),
            videasy_movie=str(streaming.get("videasy_movie", "")),
        ),
        image_cache=ImageCacheConfig(
            base_dir=base_dir,
            folders={str(k): str(v) for k, v in folders.items()},
        ),
    )


# -------------------------
# URL builders (robust)
# -------------------------
def _norm_base(base: str) -> str:
    base = (base or "").strip()
    return base


def _join_url(base: str, suffix: str) -> str:
    base = _norm_base(base)
    suffix = (suffix or "").lstrip("/")
    if not base:
        return suffix  # will at least be deterministic, but should not happen once config is correct
    if base.endswith("/"):
        return base + suffix
    return base + "/" + suffix


def _format_or_join(base: str, **kw: Any) -> str:
    """
    Supports:
    - base containing placeholders: {tmdb_id}, {season}, {episode}
    - otherwise, caller supplies suffix and we join
    """
    base = _norm_base(base)
    if not base:
        return ""
    if "{" in base and "}" in base:
        try:
            return base.format(**kw)
        except Exception:
            # fall back to joining the tmdb_id if formatting fails
            pass
    # default join with tmdb_id
    tmdb_id = str(kw.get("tmdb_id", "")).strip()
    return _join_url(base, tmdb_id)


def build_tv_links(cfg: Config, tmdb_id: int, season: int, episode: int) -> Dict[str, str]:
    # canonical suffix for these providers is typically /{tmdb_id}/{season}/{episode}
    suffix = f"{tmdb_id}/{season}/{episode}"
    return {
        "tmdb": f"https://www.themoviedb.org/tv/{tmdb_id}/season/{season}/episode/{episode}",
        "vidsrc": _format_or_join(cfg.streaming.vidsrc_tv, tmdb_id=tmdb_id, season=season, episode=episode) if "{" in cfg.streaming.vidsrc_tv else _join_url(cfg.streaming.vidsrc_tv, suffix),
        "videasy": _format_or_join(cfg.streaming.videasy_tv, tmdb_id=tmdb_id, season=season, episode=episode) if "{" in cfg.streaming.videasy_tv else _join_url(cfg.streaming.videasy_tv, suffix),
    }


def build_movie_links(cfg: Config, tmdb_id: int) -> Dict[str, str]:
    return {
        "tmdb": f"https://www.themoviedb.org/movie/{tmdb_id}",
        "vidsrc": _format_or_join(cfg.streaming.vidsrc_movie, tmdb_id=tmdb_id),
        "videasy": _format_or_join(cfg.streaming.videasy_movie, tmdb_id=tmdb_id),
    }


# -------------------------
# Local asset path helpers
# -------------------------
def _folder(cfg: Config, key: str) -> str:
    v = (cfg.image_cache.folders.get(key) or "").strip()
    if not v:
        return ""
    if not v.startswith("/"):
        v = "/" + v
    return v.rstrip("/")


def _basename_from_tmdb_path(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    p = str(p).strip()
    if not p:
        return None
    return Path(p).name


def compute_local_image_paths(cfg: Config, media: str, poster_path: Optional[str], backdrop_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (poster_local, backdrop_local) using configured public folders + tmdb basename.
    Does not download; only computes deterministic paths for UI.
    """
    poster_name = _basename_from_tmdb_path(poster_path)
    backdrop_name = _basename_from_tmdb_path(backdrop_path)

    if media == "show":
        poster_dir = _folder(cfg, "shows_poster")
        backdrop_dir = _folder(cfg, "shows_backdrop")
    else:
        poster_dir = _folder(cfg, "movies_poster")
        backdrop_dir = _folder(cfg, "movies_backdrop")

    poster_local = f"{poster_dir}/{poster_name}" if (poster_dir and poster_name) else None
    backdrop_local = f"{backdrop_dir}/{backdrop_name}" if (backdrop_dir and backdrop_name) else None
    return poster_local, backdrop_local


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
        if not self.bearer_token and "." in self.api_key_or_token and len(self.api_key_or_token) > 40:
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
        raise RuntimeError(f"TMDB get_json failed after retries: {url}") from last_ex

    def precheck(self) -> None:
        js = self.get_json("/configuration")
        if not isinstance(js, dict):
            raise RuntimeError("TMDB precheck failed (non-dict)")
        logging.info("[tmdb] precheck ok")


# -------------------------
# Inputs parsing
# -------------------------
def _first_existing(candidates: List[Path]) -> Optional[Path]:
    for p in candidates:
        if p.exists():
            return p
    return None



def compute_local_season_poster(cfg: Config, poster_path: Optional[str]) -> Optional[str]:
    name = _basename_from_tmdb_path(poster_path)
    if not name:
        return None
    d = _folder(cfg, "seasons_poster")
    return f"{d}/{name}" if d else None


def compute_local_episode_still(cfg: Config, still_path: Optional[str]) -> Optional[str]:
    name = _basename_from_tmdb_path(still_path)
    if not name:
        return None
    d = _folder(cfg, "episodes_stills")
    return f"{d}/{name}" if d else None


def build_tv_seasons_episodes(
    client: "TMDBClient",
    cfg: Config,
    show_tmdb_id: int,
    season_mode: str,
    season_filter: Optional[List[int]],
    season_min: Optional[int],
) -> List[Dict[str, Any]]:
    """Build full Season -> Episode hierarchy via /tv/{id}/season/{season_number}."""
    try:
        show = client.get_json(f"/tv/{int(show_tmdb_id)}", params={"language": "en-US"})
    except Exception:
        show = None

    available: List[int] = []
    for ss in (show or {}).get("seasons") or []:
        try:
            available.append(int(ss.get("season_number")))
        except Exception:
            continue

    # Decide which seasons to fetch WITHOUT ever calling non-existent seasons
    available_set = sorted({int(x) for x in available if isinstance(x, int)})

    wanted: List[int] = []
    if (season_mode or "all") == "min" and season_min is not None:
        wanted = [sn for sn in available_set if sn >= int(season_min)]
    elif (season_mode or "all") == "filter" and season_filter:
        wanted = [sn for sn in season_filter if int(sn) in set(available_set)]
    else:
        wanted = available_set

    seasons_out: List[Dict[str, Any]] = []
    for sn in wanted:
        try:
            season = client.get_json(f"/tv/{int(show_tmdb_id)}/season/{int(sn)}", params={"language": "en-US"})
        except Exception as ex:
            logging.warning("[season] fetch failed show=%s season=%s err=%s", show_tmdb_id, sn, ex)
            continue

        poster_path = season.get("poster_path")
        season_obj: Dict[str, Any] = {
            "id": season.get("id"),
            "_id": season.get("_id"),
            "name": season.get("name"),
            "overview": season.get("overview"),
            "air_date": season.get("air_date"),
            "season_number": season.get("season_number", sn),
            "vote_average": season.get("vote_average"),
            "vote_count": season.get("vote_count"),
            "poster_path": poster_path,
            "poster_local": compute_local_season_poster(cfg, poster_path),
            "links": {"tmdb": f"https://www.themoviedb.org/tv/{int(show_tmdb_id)}/season/{int(sn)}"},
            "episodes": [],
        }

        for ep in (season.get("episodes") or []):
            try:
                ep_num = int(ep.get("episode_number"))
            except Exception:
                continue
            still_path = ep.get("still_path")
            season_number = int(ep.get("season_number") or sn)
            ep_obj: Dict[str, Any] = {
                "id": ep.get("id"),
                "show_id": ep.get("show_id", show_tmdb_id),
                "season_number": season_number,
                "episode_number": ep_num,
                "episode_type": ep.get("episode_type"),
                "name": ep.get("name"),
                "overview": ep.get("overview"),
                "air_date": ep.get("air_date"),
                "runtime": ep.get("runtime"),
                "production_code": ep.get("production_code"),
                "still_path": still_path,
                "still_local": compute_local_episode_still(cfg, still_path),
                "vote_average": ep.get("vote_average"),
                "vote_count": ep.get("vote_count"),
                "links": build_tv_links(cfg, int(show_tmdb_id), int(season_number), int(ep_num)),
            }
            season_obj["episodes"].append(ep_obj)

        seasons_out.append(season_obj)

    return seasons_out



def parse_pipe_lines(path: Path, media: str) -> List[Dict[str, Any]]:
    """
    TV:    name|tmdb_id|season_spec|tvmaze_id
    Movie: name|tmdb_id
    Season spec rules:
      - blank => all
      - "S1,S2,S3" or "1,2,3"
      - "S1-3" or "1-3"
    """
    out: List[Dict[str, Any]] = []
    for raw in read_text_file(path).splitlines():
        if not raw.strip():
            continue
        if RE_COMMENT.match(raw):
            continue

        parts = RE_PIPE.split(raw.strip())
        parts = [RE_WS.sub(" ", p.strip()) for p in parts]

        if media == "show":
            name = parts[0] if len(parts) > 0 else ""
            tmdb_id = parts[1] if len(parts) > 1 else ""
            season_spec = parts[2] if len(parts) > 2 else ""
            tvmaze_id = parts[3] if len(parts) > 3 else ""
            out.append(
                {
                    "title": name,
                    "tmdb_id": tmdb_id,
                    "season_spec": season_spec,
                    "tvmaze_id": tvmaze_id,
                }
            )
        else:
            name = parts[0] if len(parts) > 0 else ""
            tmdb_id = parts[1] if len(parts) > 1 else ""
            out.append({"title": name, "tmdb_id": tmdb_id})

    return out


def parse_season_rule(spec: str) -> Tuple[str, Optional[List[int]], Optional[int]]:
    """
    Season spec rules:
      - "" or "*"      => ("all", None, None)
      - "1,2,3"        => ("filter", [1,2,3], None)
      - "1-3"          => ("filter", [1,2,3], None)
      - "7+"           => ("min", None, 7)

    Returns:
      (season_mode, season_filter, season_min)
    """
    s = (spec or "").strip()
    if not s or s == "*":
        return "all", None, None

    s = s.upper().replace("SEASON", "S").replace(" ", "")

    if s.endswith("+") and s[:-1].lstrip("S").isdigit():
        n = int(s[:-1].lstrip("S"))
        return ("min", None, n if n > 0 else None)

    s = s.lstrip("S")
    parts = [p for p in s.split(",") if p]
    seasons: List[int] = []
    for p in parts:
        p = p.lstrip("S")
        if "-" in p:
            a, b = p.split("-", 1)
            try:
                start = int(a)
                end = int(b)
                if start <= end:
                    seasons.extend(list(range(start, end + 1)))
                else:
                    seasons.extend(list(range(end, start + 1)))
            except Exception:
                continue
        else:
            try:
                seasons.append(int(p))
            except Exception:
                continue
    seasons = sorted({x for x in seasons if x > 0})
    return ("filter", seasons or None, None)


def parse_season_spec(spec: str) -> Optional[List[int]]:
    """Legacy helper: returns explicit season list or None for all/min."""
    mode, flt, _mn = parse_season_rule(spec)
    return flt if mode == "filter" else None

def load_inputs() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load upstream seeds from data/inputs.json (canonical)."""
    inputs_path = INPUTS_JSON_DEFAULT
    if not inputs_path.exists():
        raise FileNotFoundError(f"Missing required file: {inputs_path}")

    js = json.loads(read_text_file(inputs_path))
    tv = js.get("tv") or js.get("shows") or js.get("series") or []
    mv = js.get("movies") or js.get("films") or []
    if not isinstance(tv, list) or not isinstance(mv, list):
        raise ValueError("inputs.json must contain arrays: { tv: [...], movies: [...] }")

    logging.info("[inputs] inputs_json=%s", inputs_path)
    logging.info("[inputs] tv=%s movies=%s", len(tv), len(mv))
    return tv, mv
# -------------------------
# External IDs helpers
# -------------------------
def safe_external_ids(client: TMDBClient, media: str, tmdb_id: int) -> Dict[str, Any]:
    try:
        if media == "movie":
            js = client.get_json(f"/movie/{tmdb_id}/external_ids")
        else:
            js = client.get_json(f"/tv/{tmdb_id}/external_ids")
        return js if isinstance(js, dict) else {}
    except Exception as ex:
        logging.warning("[external_ids] media=%s tmdb_id=%s err=%s", media, tmdb_id, ex)
        return {}


def safe_watch_providers(client: TMDBClient, media: str, tmdb_id: int) -> Dict[str, Any]:
    try:
        if media == "movie":
            js = client.get_json(f"/movie/{tmdb_id}/watch/providers")
        else:
            js = client.get_json(f"/tv/{tmdb_id}/watch/providers")
        return js if isinstance(js, dict) else {}
    except Exception as ex:
        logging.warning("[watch_providers] media=%s tmdb_id=%s err=%s", media, tmdb_id, ex)
        return {}


# -------------------------
# Core build
# -------------------------
def main() -> int:
    setup_logging()

    if load_dotenv:
        load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)

    tmdb_key = (os.getenv("API_TMDB_KEY") or "").strip()
    tmdb_token = (os.getenv("API_TMDB_TOKEN") or "").strip()
    if not tmdb_key and not tmdb_token:
        logging.error("Missing TMDB creds. Set API_TMDB_KEY or API_TMDB_TOKEN.")
        return 2

    cfg = load_config(CONFIG_JSON)

    client = TMDBClient(api_key_or_token=(tmdb_key or tmdb_token), bearer_token=(tmdb_token or None))
    client.precheck()

    tv_list, movies_list = load_inputs()

    data: Dict[str, Any] = {
        "meta": {
            "generated_utc": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "builder": {
                "script": "scripts/fetch_tmdb.py",
                "version": "v2.9.0",
                "config_sha1": sha1_text(read_text_file(CONFIG_JSON)),
            },
        },
        "shows": [],
        "movies": [],
        "errors": [],
    }

    # progress helper
    def _iter(items: List[Dict[str, Any]], desc: str):
        if tqdm:
            return tqdm(items, desc=desc)
        return items

    shows_ok = 0
    movies_ok = 0

    # -------------------------
    # TV shows (minimal + rich fields; seasons/episodes deep build not included)
    # -------------------------
    for item in _iter(tv_list, "TMDB TV"):
        title = (item.get("title") or item.get("name") or "").strip()
        tmdb_id_raw = str(item.get("tmdb_id") or "").strip()
        season_spec = str(item.get("season_spec") or item.get("seasons") or "").strip()

        # Prefer parsed rule fields if present (from parse_txt_to_json.py)
        season_mode = str(item.get("season_mode") or "").strip().lower() or ""
        season_min = item.get("season_min")
        parsed_filter = item.get("season_filter")

        # Backward-compat: compute rule from season_spec if not provided
        if season_mode not in ("all", "filter", "min"):
            season_mode2, season_filter2, season_min2 = parse_season_rule(season_spec)
            season_mode = season_mode2
            seasons = season_filter2
            season_min = season_min2
        else:
            seasons = parsed_filter if isinstance(parsed_filter, list) else parse_season_spec(season_spec)

        # UI flags (preserve)
        if season_mode == "filter":
            season_mode = "filter" if seasons else "all"
        if season_mode == "min":
            try:
                season_min = int(season_min) if season_min is not None else None
            except Exception:
                season_min = None

        try:
            tmdb_id: Optional[int] = int(tmdb_id_raw) if tmdb_id_raw else None
        except Exception:
            tmdb_id = None

        year = item.get("year")
        try:
            if tmdb_id:
                show = client.get_json(f"/tv/{int(tmdb_id)}", params={"language": "en-US"})
            else:
                params: Dict[str, Any] = {"query": title, "language": "en-US"}
                if year:
                    try:
                        params["first_air_date_year"] = int(year)
                    except Exception:
                        pass
                sr = client.get_json("/search/tv", params=params)
                results = (sr or {}).get("results") or []
                if not results:
                    logging.warning("[show] not found: %s|%s (%s)", title, tmdb_id_raw, year)
                    data["errors"].append({"type": "tmdb_not_found", "media": "show", "title": title, "tmdb_id": tmdb_id_raw, "year": year})
                    continue
                show = results[0]
                tmdb_id = int(show.get("id"))
                show = client.get_json(f"/tv/{int(tmdb_id)}", params={"language": "en-US"})

            tmdb_id = int(show.get("id") or tmdb_id or 0)
            ext = safe_external_ids(client, "show", tmdb_id)
            watch_providers = safe_watch_providers(client, "show", tmdb_id)

            poster_path = show.get("poster_path")
            backdrop_path = show.get("backdrop_path")
            poster_local, backdrop_local = compute_local_image_paths(cfg, "show", poster_path, backdrop_path)

            show_obj = {
                # --- core / legacy ---
                "tmdb_id": int(tmdb_id),
                "trakt_id": None,
                "title": show.get("name") or title,
                "first_air_date": show.get("first_air_date"),
                "poster_local": poster_local,
                "backdrop_local": backdrop_local,
                "seasons": [],  # built below
                "links": {"tmdb": f"https://www.themoviedb.org/tv/{int(tmdb_id)}"},
                "season_mode": season_mode,
                "season_filter": seasons,  # None => all

                # --- rich TMDB fields (NO translations) ---
                "id": int(tmdb_id),
                "tvdb_id": ext.get("tvdb_id"),
                "imdb_id": ext.get("imdb_id"),
                "name": show.get("name"),
                "original_name": show.get("original_name"),
                "type": show.get("type"),
                "overview": show.get("overview"),
                "homepage": show.get("homepage"),
                "status": show.get("status"),
                "popularity": show.get("popularity"),
                "vote_average": show.get("vote_average"),
                "vote_count": show.get("vote_count"),
                "poster_path": poster_path,
                "backdrop_path": backdrop_path,
                "genres": show.get("genres") or [],
                "origin_country": show.get("origin_country") or [],
                "in_production": show.get("in_production"),
                "number_of_seasons": show.get("number_of_seasons"),
                "number_of_episodes": show.get("number_of_episodes"),
                "episode_run_time": show.get("episode_run_time") or [],
                "last_air_date": show.get("last_air_date"),
                "next_episode_to_air": show.get("next_episode_to_air"),
                "last_episode_to_air": show.get("last_episode_to_air"),
                "created_by": show.get("created_by") or [],
                "networks": show.get("networks") or [],
                "watch_providers": watch_providers,
            }

            # Deep build seasons + episodes (required for UI + Trakt mapping)
            try:
                show_obj["seasons"] = build_tv_seasons_episodes(
                    client=client,
                    cfg=cfg,
                    show_tmdb_id=int(tmdb_id),
                    season_mode=season_mode,
                    season_filter=seasons,
                    season_min=season_min,
                )
            except Exception as _ex_deep:
                logging.warning("[show] deep build failed tmdb_id=%s err=%s", tmdb_id, _ex_deep)

            data["shows"].append(show_obj)
            shows_ok += 1
        except Exception as ex:
            logging.error("[show] error title=%s tmdb_id=%s err=%s", title, tmdb_id_raw, ex)
            data["errors"].append({"type": "tmdb_error", "media": "show", "title": title, "tmdb_id": tmdb_id_raw, "message": str(ex)})

    # -------------------------
    # Movies (minimal + rich fields)
    # -------------------------
    for item in _iter(movies_list, "TMDB Movies"):
        title = (item.get("title") or "").strip()
        tmdb_id_raw = str(item.get("tmdb_id") or "").strip()
        year = item.get("year")

        try:
            tmdb_id: Optional[int] = int(tmdb_id_raw) if tmdb_id_raw else None
        except Exception:
            tmdb_id = None

        try:
            if tmdb_id:
                mv = client.get_json(f"/movie/{int(tmdb_id)}", params={"language": "en-US"})
            else:
                params = {"query": title, "language": "en-US"}
                if year:
                    try:
                        params["year"] = int(year)
                    except Exception:
                        pass
                sr = client.get_json("/search/movie", params=params)
                results = (sr or {}).get("results") or []
                if not results:
                    logging.warning("[movie] not found: %s|%s (%s)", title, tmdb_id_raw, year)
                    data["errors"].append({"type": "tmdb_not_found", "media": "movie", "title": title, "tmdb_id": tmdb_id_raw, "year": year})
                    continue
                mv = results[0]
                tmdb_id = int(mv.get("id"))
                mv = client.get_json(f"/movie/{int(tmdb_id)}", params={"language": "en-US"})

            tmdb_id = int(mv.get("id") or tmdb_id or 0)
            ext = safe_external_ids(client, "movie", tmdb_id)
            watch_providers = safe_watch_providers(client, "movie", tmdb_id)

            poster_path = mv.get("poster_path")
            backdrop_path = mv.get("backdrop_path")
            poster_local, backdrop_local = compute_local_image_paths(cfg, "movie", poster_path, backdrop_path)

            mv_obj = {
                # --- core / legacy ---
                "tmdb_id": int(tmdb_id),
                "trakt_id": None,
                "title": mv.get("title") or title,
                "release_date": mv.get("release_date"),
                "poster_local": poster_local,
                "backdrop_local": backdrop_local,
                "links": build_movie_links(cfg, int(tmdb_id)),

                # --- rich TMDB fields (NO translations) ---
                "id": int(tmdb_id),
                "imdb_id": ext.get("imdb_id"),
                "original_title": mv.get("original_title"),
                "tagline": mv.get("tagline"),
                "overview": mv.get("overview"),
                "homepage": mv.get("homepage"),
                "status": mv.get("status"),
                "popularity": mv.get("popularity"),
                "vote_average": mv.get("vote_average"),
                "vote_count": mv.get("vote_count"),
                "poster_path": poster_path,
                "backdrop_path": backdrop_path,
                "genres": mv.get("genres") or [],
                "collection": mv.get("belongs_to_collection"),
                "production_companies": mv.get("production_companies") or [],
                "production_countries": mv.get("production_countries") or [],
                "runtime": mv.get("runtime"),
                "watch_providers": watch_providers,
            }

            data["movies"].append(mv_obj)
            movies_ok += 1
        except Exception as ex:
            logging.error("[movie] error title=%s tmdb_id=%s err=%s", title, tmdb_id_raw, ex)
            data["errors"].append({"type": "tmdb_error", "media": "movie", "title": title, "tmdb_id": tmdb_id_raw, "message": str(ex)})

    # hard refusal guard (preserve your existing safety)
    if shows_ok == 0 and movies_ok == 0:
        logging.error("No shows or movies built. Refusing to overwrite output.")
        return 3

    data["meta"]["counts"] = {"shows": shows_ok, "movies": movies_ok, "errors": len(data["errors"])}


    # -------------------------
    # Preserve Trakt enrichment across TMDB rebuilds
    #   - TMDB fetch rebuilds the file; Trakt later enriches it.
    #   - Without this step, running fetch_tmdb.py after fetch_trakt.py would wipe trakt_id.
    # -------------------------
    try:
        if OUT_DATA_JSON.exists():
            prev = json.loads(OUT_DATA_JSON.read_text(encoding="utf-8", errors="replace") or "{}")
            prev_movies = {
                str(m.get("tmdb_id")): m.get("trakt_id")
                for m in (prev.get("movies") or [])
                if m.get("tmdb_id") is not None and m.get("trakt_id") not in (None, "", 0)
            }
            prev_shows = {
                str(s.get("tmdb_id")): s.get("trakt_id")
                for s in (prev.get("shows") or [])
                if s.get("tmdb_id") is not None and s.get("trakt_id") not in (None, "", 0)
            }

            for m in data.get("movies", []):
                k = str(m.get("tmdb_id"))
                if not m.get("trakt_id") and k in prev_movies:
                    m["trakt_id"] = prev_movies[k]

            for s in data.get("shows", []):
                k = str(s.get("tmdb_id"))
                if not s.get("trakt_id") and k in prev_shows:
                    s["trakt_id"] = prev_shows[k]
    except Exception as ex:
        logging.warning("[merge] preserve trakt_id skipped: %s", ex)
    write_json_atomic(OUT_DATA_JSON, data)
    logging.info("[done] wrote=%s shows=%s movies=%s errors=%s", OUT_DATA_JSON, shows_ok, movies_ok, len(data["errors"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
