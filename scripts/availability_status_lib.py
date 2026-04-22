#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/availability_status_lib.py
# [PROJECT] my_TV_Movie
# [ROLE]    Shared availability-status helpers for source validation, provider-
#           aware URL checks, optional cached network validation, and runtime
#           enrichment.
# [VERSION] v2.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.02
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
from urllib import error as _urlerror
from urllib import request as _urlrequest
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
SOURCE_JSON = REPO_ROOT / "data" / "watch_source_availability.json"
CONFIG_JSON = REPO_ROOT / "web" / "config.json"
NETWORK_CACHE_JSON = REPO_ROOT / "logs" / "availability_status_network_cache.json"

ALLOWED_ENTITY_TYPES = ("movie", "show", "season", "episode")
ALLOWED_AVAILABILITY = ("not_yet_released", "available", "unavailable", "unknown")
ALLOWED_URL_TEST = ("pass", "fail", "skip", "unknown")
ALLOWED_SOURCES = (
    "videasy",
    "vidsrc",
    "vidsrc_net",
    "superembed",
    "multiembed",
    "smashystream",
    "flixhq",
    "sflix",
    "2embed_cc",
    "2embed_org",
    "local",
)
ALLOWED_VALIDATION_MODES = ("structural", "provider_structural", "provider_structural_cached_head")
DEFAULT_SOURCE_VERSION = "1.2.0"


def utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_jsonc(text: str) -> str:
    lines: List[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("//"):
            continue
        out: List[str] = []
        in_str = False
        esc = False
        idx = 0
        while idx < len(line):
            ch = line[idx]
            if in_str:
                out.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                idx += 1
                continue
            if ch == '"':
                in_str = True
                out.append(ch)
                idx += 1
                continue
            if ch == "/" and idx + 1 < len(line) and line[idx + 1] == "/":
                break
            out.append(ch)
            idx += 1
        lines.append("".join(out).rstrip())
    cleaned = "\n".join(lines).strip()
    if cleaned and not cleaned.startswith("{"):
        brace = cleaned.find("{")
        if brace >= 0:
            cleaned = cleaned[brace:]
    return cleaned


def load_json(path: Path, *, allow_jsonc: bool = False) -> Any:
    raw = read_text(path)
    if allow_jsonc:
        raw = strip_jsonc(raw)
    return json.loads(raw)


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def normalize_entity_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_ENTITY_TYPES else ""


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_AVAILABILITY else ""


def normalize_url_test(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_URL_TEST else ""


def normalize_source(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_SOURCES else ""


def normalize_validation_mode(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_VALIDATION_MODES else ""


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def to_date_key(value: Any) -> str:
    text = safe_text(value)[:10]
    if len(text) != 10:
        return ""
    try:
        _dt.date.fromisoformat(text)
    except ValueError:
        return ""
    return text


def today_key() -> str:
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


def is_future_date(value: Any) -> bool:
    key = to_date_key(value)
    return bool(key and key > today_key())


def canonical_defaults() -> Dict[str, Any]:
    return {
        "validation_mode": "provider_structural",
        "network": {
            "enabled": False,
            "timeout_seconds": 5,
            "retry_count": 1,
            "cache_ttl_hours": 24,
            "cache_file": str(NETWORK_CACHE_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
        },
        "entities": {
            "movie": {"requires_url": True, "preferred_sources": ["videasy", "vidsrc", "local"]},
            "show": {"requires_url": True, "preferred_sources": ["videasy", "vidsrc"]},
            "season": {"requires_url": True, "preferred_sources": ["videasy", "vidsrc"]},
            "episode": {"requires_url": True, "preferred_sources": ["videasy", "vidsrc", "local"]},
        },
    }


def canonical_source_document(existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    existing = existing if isinstance(existing, dict) else {}
    defaults = canonical_defaults()
    incoming_defaults = existing.get("defaults") if isinstance(existing.get("defaults"), dict) else {}
    incoming_network = incoming_defaults.get("network") if isinstance(incoming_defaults.get("network"), dict) else {}
    entity_defaults = incoming_defaults.get("entities") if isinstance(incoming_defaults.get("entities"), dict) else {}
    merged_entities: Dict[str, Any] = {}
    for entity_type, entity_default in defaults["entities"].items():
        incoming_entity = entity_defaults.get(entity_type) if isinstance(entity_defaults.get(entity_type), dict) else {}
        preferred_sources = incoming_entity.get("preferred_sources")
        merged_entities[entity_type] = {
            "requires_url": bool(incoming_entity.get("requires_url", entity_default["requires_url"])),
            "preferred_sources": list(preferred_sources) if isinstance(preferred_sources, list) and preferred_sources else list(entity_default["preferred_sources"]),
        }
    records = existing.get("records")
    return {
        "version": safe_text(existing.get("version")) or DEFAULT_SOURCE_VERSION,
        "generated_at": safe_text(existing.get("generated_at")) or utc_iso(),
        "defaults": {
            "validation_mode": normalize_validation_mode(incoming_defaults.get("validation_mode")) or defaults["validation_mode"],
            "network": {
                "enabled": bool(incoming_network.get("enabled", defaults["network"]["enabled"])),
                "timeout_seconds": max(1, safe_int(incoming_network.get("timeout_seconds"), defaults["network"]["timeout_seconds"])),
                "retry_count": max(0, safe_int(incoming_network.get("retry_count"), defaults["network"]["retry_count"])),
                "cache_ttl_hours": max(1, safe_int(incoming_network.get("cache_ttl_hours"), defaults["network"]["cache_ttl_hours"])),
                "cache_file": safe_text(incoming_network.get("cache_file")) or defaults["network"]["cache_file"],
            },
            "entities": merged_entities,
        },
        "records": list(records) if isinstance(records, list) else [],
    }


def movie_key(movie: Dict[str, Any]) -> str:
    tmdb_id = safe_text(movie.get("tmdb_id") or movie.get("id"))
    return f"movie:{tmdb_id}" if tmdb_id else ""


def show_key(show: Dict[str, Any]) -> str:
    tmdb_id = safe_text(show.get("tmdb_id") or show.get("id"))
    return f"show:{tmdb_id}" if tmdb_id else ""


def season_key(show_id: Any, season_number: Any) -> str:
    show_part = safe_text(show_id)
    season_part = safe_text(season_number)
    if not show_part or not season_part:
        return ""
    return f"show:{show_part}:season:{season_part}"


def episode_key(show_id: Any, season_number: Any, episode_number: Any) -> str:
    show_part = safe_text(show_id)
    season_part = safe_text(season_number)
    episode_part = safe_text(episode_number)
    if not show_part or not season_part or not episode_part:
        return ""
    return f"show:{show_part}:season:{season_part}:episode:{episode_part}"


def pick_release_date(entity_type: str, entity: Dict[str, Any]) -> str:
    if entity_type == "movie":
        return to_date_key(entity.get("release_date"))
    return to_date_key(entity.get("air_date") or entity.get("first_air_date") or entity.get("release_date"))


def build_url_from_base(base: str, *parts: Any) -> str:
    root = safe_text(base).rstrip("/")
    suffix = "/".join([safe_text(part).strip("/") for part in parts if safe_text(part)])
    if not root:
        return ""
    if "{" in root and "}" in root:
        values = {
            "tmdb_id": parts[0] if len(parts) > 0 else "",
            "season": parts[1] if len(parts) > 1 else "",
            "episode": parts[2] if len(parts) > 2 else "",
        }
        try:
            return root.format(**values)
        except Exception:
            return ""
    if not suffix:
        return root
    return f"{root}/{suffix}"


def load_streaming_config(config_path: Path = CONFIG_JSON) -> Dict[str, str]:
    cfg = load_json(config_path, allow_jsonc=True)
    streaming = cfg.get("streaming") or {}
    if not isinstance(streaming, dict):
        streaming = {}
    out = {
        "vidsrc_tv": safe_text(streaming.get("vidsrc_tv")),
        "vidsrc_movie": safe_text(streaming.get("vidsrc_movie")),
        "videasy_tv": safe_text(streaming.get("videasy_tv")),
        "videasy_movie": safe_text(streaming.get("videasy_movie")),
    }
    providers = streaming.get("embed_providers")
    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            key = safe_text(provider.get("key"))
            if not key:
                continue
            out[f"{key}_tv"] = safe_text(provider.get("tv_template"))
            out[f"{key}_movie"] = safe_text(provider.get("movie_template"))
    return out


def entity_candidates(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any], streaming: Dict[str, str]) -> Dict[str, str]:
    links = entity.get("links") if isinstance(entity.get("links"), dict) else {}
    show_id = safe_text(context.get("show_tmdb_id"))
    season_number = safe_text(context.get("season_number"))
    episode_number = safe_text(context.get("episode_number"))
    tmdb_id = safe_text(entity.get("tmdb_id") or entity.get("id") or show_id)
    candidates: Dict[str, str] = {}
    local = safe_text(links.get("local_media") or links.get("local") or links.get("localMedia"))
    if local:
        candidates["local"] = local
    configured_sources = []
    configured_sources.extend(entity.get("watch_sources") if isinstance(entity.get("watch_sources"), list) else [])
    configured_sources.extend(entity.get("source_options") if isinstance(entity.get("source_options"), list) else [])
    configured_sources.extend(links.get("watch_sources") if isinstance(links.get("watch_sources"), list) else [])
    configured_sources.extend(links.get("source_options") if isinstance(links.get("source_options"), list) else [])
    for entry in configured_sources:
        if not isinstance(entry, dict):
            continue
        key = normalize_source(entry.get("key") or entry.get("provider") or entry.get("source"))
        href = safe_text(entry.get("href") or entry.get("url") or entry.get("link"))
        if key and href:
            candidates[key] = href
    if entity_type == "movie":
        candidates["videasy"] = safe_text(links.get("videasy")) or build_url_from_base(streaming.get("videasy_movie", ""), tmdb_id)
        candidates["vidsrc"] = safe_text(links.get("vidsrc")) or build_url_from_base(streaming.get("vidsrc_movie", ""), tmdb_id)
    elif entity_type == "show":
        candidates["videasy"] = safe_text(links.get("videasy")) or build_url_from_base(streaming.get("videasy_tv", ""), tmdb_id)
        candidates["vidsrc"] = safe_text(links.get("vidsrc")) or build_url_from_base(streaming.get("vidsrc_tv", ""), tmdb_id)
    elif entity_type == "season":
        candidates["videasy"] = safe_text(links.get("videasy")) or build_url_from_base(streaming.get("videasy_tv", ""), show_id, season_number)
        candidates["vidsrc"] = safe_text(links.get("vidsrc")) or build_url_from_base(streaming.get("vidsrc_tv", ""), show_id, season_number)
    elif entity_type == "episode":
        candidates["videasy"] = safe_text(links.get("videasy")) or build_url_from_base(streaming.get("videasy_tv", ""), show_id, season_number, episode_number)
        candidates["vidsrc"] = safe_text(links.get("vidsrc")) or build_url_from_base(streaming.get("vidsrc_tv", ""), show_id, season_number, episode_number)
    return {key: value for key, value in candidates.items() if safe_text(value)}


def choose_primary_watch_url(
    entity_type: str,
    entity: Dict[str, Any],
    context: Dict[str, Any],
    defaults: Dict[str, Any],
    streaming: Dict[str, str],
    record: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    explicit = safe_text((record or {}).get("primary_watch_url"))
    explicit_source = normalize_source((record or {}).get("preferred_source"))
    if explicit:
        return explicit, explicit_source or detect_provider_kind(explicit, streaming)
    entities = defaults.get("entities") if isinstance(defaults.get("entities"), dict) else {}
    entity_defaults = entities.get(entity_type) if isinstance(entities.get(entity_type), dict) else {}
    preferred = entity_defaults.get("preferred_sources")
    candidates = entity_candidates(entity_type, entity, context, streaming)
    order = []
    if explicit_source:
        order.append(explicit_source)
    order.extend(list(preferred) if isinstance(preferred, list) and preferred else ["videasy", "vidsrc", "local"])
    seen: set[str] = set()
    for key in order:
        source_key = normalize_source(key)
        if not source_key or source_key in seen:
            continue
        seen.add(source_key)
        url = safe_text(candidates.get(source_key))
        if url:
            return url, source_key
    for source_key, value in candidates.items():
        if safe_text(value):
            return safe_text(value), normalize_source(source_key)
    return "", explicit_source


def is_valid_primary_url(url: str) -> bool:
    value = safe_text(url)
    if not value:
        return False
    if value.startswith("/") or os.path.isabs(value):
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def detect_provider_kind(url: str, streaming: Dict[str, str]) -> str:
    value = safe_text(url)
    if not value:
        return ""
    if value.startswith("/") or os.path.isabs(value):
        return "local"
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    for key, base in streaming.items():
        parsed_base = urlparse(safe_text(base))
        if parsed_base.netloc and parsed_base.netloc.lower() == host:
            source = key[:-6] if key.endswith("_movie") else key[:-3] if key.endswith("_tv") else key
            return normalize_source(source) or source
    return ""


def explicit_url_test_result(record: Optional[Dict[str, Any]]) -> str:
    if not isinstance(record, dict):
        return ""
    return normalize_url_test(record.get("url_test_result"))


def iter_catalog_entities(data: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    for movie in data.get("movies", []) or []:
        if not isinstance(movie, dict):
            continue
        yield {
            "entity_type": "movie",
            "entity": movie,
            "context": {"show_tmdb_id": None, "season_number": None, "episode_number": None},
            "entity_key": movie_key(movie),
        }
    for show in data.get("shows", []) or []:
        if not isinstance(show, dict):
            continue
        show_tmdb_id = safe_text(show.get("tmdb_id") or show.get("id"))
        yield {
            "entity_type": "show",
            "entity": show,
            "context": {"show_tmdb_id": show_tmdb_id, "season_number": None, "episode_number": None},
            "entity_key": show_key(show),
        }
        for season in show.get("seasons", []) or []:
            if not isinstance(season, dict):
                continue
            season_number = safe_text(season.get("season_number") or season.get("number"))
            yield {
                "entity_type": "season",
                "entity": season,
                "context": {"show_tmdb_id": show_tmdb_id, "season_number": season_number, "episode_number": None},
                "entity_key": season_key(show_tmdb_id, season_number),
            }
            for episode in season.get("episodes", []) or []:
                if not isinstance(episode, dict):
                    continue
                episode_number = safe_text(episode.get("episode_number") or episode.get("number"))
                yield {
                    "entity_type": "episode",
                    "entity": episode,
                    "context": {"show_tmdb_id": show_tmdb_id, "season_number": season_number, "episode_number": episode_number},
                    "entity_key": episode_key(show_tmdb_id, season_number, episode_number),
                }


def build_catalog_key_index(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in iter_catalog_entities(data):
        out[row["entity_key"]] = row
    return out


def network_cache_path(defaults: Dict[str, Any]) -> Path:
    network = defaults.get("network") if isinstance(defaults.get("network"), dict) else {}
    raw = safe_text(network.get("cache_file"))
    if not raw:
        return NETWORK_CACHE_JSON
    path = Path(raw)
    return path if path.is_absolute() else (REPO_ROOT / path)


def load_network_cache(defaults: Dict[str, Any]) -> Dict[str, Any]:
    path = network_cache_path(defaults)
    if not path.exists():
        return {"version": 1, "entries": {}}
    try:
        cache = load_json(path)
    except Exception:
        return {"version": 1, "entries": {}}
    if not isinstance(cache, dict):
        return {"version": 1, "entries": {}}
    entries = cache.get("entries")
    cache["entries"] = entries if isinstance(entries, dict) else {}
    cache["version"] = cache.get("version") or 1
    return cache


def write_network_cache(defaults: Dict[str, Any], cache: Dict[str, Any]) -> None:
    path = network_cache_path(defaults)
    write_json_atomic(path, cache)


def _url_cache_key(url: str) -> str:
    return hashlib.sha256(safe_text(url).encode("utf-8")).hexdigest()


def _cache_is_fresh(entry: Dict[str, Any], ttl_hours: int) -> bool:
    checked_at = safe_text(entry.get("checked_at"))
    if not checked_at:
        return False
    try:
        dt = _dt.datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    age = _dt.datetime.now(_dt.timezone.utc) - dt.astimezone(_dt.timezone.utc)
    return age.total_seconds() <= ttl_hours * 3600


def _expected_base_for_source(source_key: str, entity_type: str, streaming: Dict[str, str]) -> str:
    if source_key == "local":
        return ""
    suffix = "movie" if entity_type == "movie" else "tv"
    if source_key == "vidsrc":
        return safe_text(streaming.get(f"vidsrc_{suffix}") or streaming.get(f"vidsrc_net_{suffix}"))
    return safe_text(streaming.get(f"{source_key}_{suffix}"))


def _expected_suffix(entity_type: str, context: Dict[str, Any], entity: Dict[str, Any]) -> str:
    show_id = safe_text(context.get("show_tmdb_id"))
    season_number = safe_text(context.get("season_number"))
    episode_number = safe_text(context.get("episode_number"))
    tmdb_id = safe_text(entity.get("tmdb_id") or entity.get("id") or show_id)
    if entity_type == "movie":
        return tmdb_id
    if entity_type == "show":
        return tmdb_id
    if entity_type == "season":
        return "/".join(part for part in [show_id, season_number] if part)
    if entity_type == "episode":
        return "/".join(part for part in [show_id, season_number, episode_number] if part)
    return ""


def validate_url_provider_structure(
    url: str,
    entity_type: str,
    entity: Dict[str, Any],
    context: Dict[str, Any],
    streaming: Dict[str, str],
    source_key: str = "",
) -> Tuple[str, str, str]:
    value = safe_text(url)
    if not value:
        return "fail", "primary watch URL is missing", source_key
    if value.startswith("/") or os.path.isabs(value):
        return "pass", "local path passed structural validation", "local"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "fail", "primary watch URL failed structural validation", source_key
    active_source = normalize_source(source_key) or detect_provider_kind(value, streaming)
    if not active_source:
        return "pass", "primary watch URL passed structural validation with unrecognized provider", ""
    if active_source == "local":
        return "pass", "local path passed structural validation", active_source
    expected_base = _expected_base_for_source(active_source, entity_type, streaming).rstrip("/")
    if not expected_base:
        return "fail", f"{active_source} base URL is not configured", active_source
    normalized_value = value.rstrip("/")
    if not normalized_value.startswith(expected_base):
        return "fail", f"primary watch URL does not match configured {active_source} base", active_source
    expected_suffix = _expected_suffix(entity_type, context, entity)
    if expected_suffix:
        actual_suffix = normalized_value[len(expected_base):].strip("/")
        expected_parts = [part for part in expected_suffix.split("/") if part]
        actual_parts = [part for part in actual_suffix.split("/") if part]
        if actual_parts[: len(expected_parts)] != expected_parts:
            return "fail", f"primary watch URL path does not match expected {entity_type} identifier pattern", active_source
    return "pass", f"primary watch URL passed {active_source} provider validation", active_source


def _network_probe_once(url: str, timeout_seconds: int) -> Tuple[str, str, Optional[int]]:
    headers = {"User-Agent": "my_TV_Movie-availability-check/2.0"}
    methods = ("HEAD", "GET")
    for method in methods:
        request = _urlrequest.Request(url, headers=headers, method=method)
        if method == "GET":
            request.add_header("Range", "bytes=0-0")
        try:
            with _urlrequest.urlopen(request, timeout=timeout_seconds) as response:
                code = int(getattr(response, "status", response.getcode()))
                if 200 <= code < 400:
                    return "pass", f"network validation returned HTTP {code}", code
                return "fail", f"network validation returned HTTP {code}", code
        except _urlerror.HTTPError as exc:
            code = int(getattr(exc, "code", 0) or 0)
            if method == "HEAD" and code in {403, 405, 429}:
                continue
            return ("pass" if 200 <= code < 400 else "fail", f"network validation returned HTTP {code}", code)
        except Exception as exc:
            if method == "HEAD":
                continue
            return "unknown", f"network validation error: {exc.__class__.__name__}", None
    return "unknown", "network validation unavailable", None


def validate_primary_watch_url(
    url: str,
    entity_type: str,
    entity: Dict[str, Any],
    context: Dict[str, Any],
    streaming: Dict[str, str],
    defaults: Dict[str, Any],
    source_key: str = "",
    allow_network: bool = False,
    cache: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    validation_mode = normalize_validation_mode(defaults.get("validation_mode")) or "provider_structural"
    base_result = {
        "url_test_result": "fail",
        "validation_reason": "primary watch URL is missing",
        "provider_source": normalize_source(source_key),
        "validation_mode": validation_mode,
        "network_checked": False,
        "http_status": None,
        "cache_hit": False,
    }
    if validation_mode == "structural":
        if is_valid_primary_url(url):
            base_result.update({
                "url_test_result": "pass",
                "validation_reason": "primary watch URL passed structural validation",
                "provider_source": normalize_source(source_key) or detect_provider_kind(url, streaming),
            })
        return base_result

    url_test_result, validation_reason, provider_source = validate_url_provider_structure(url, entity_type, entity, context, streaming, source_key)
    base_result.update({
        "url_test_result": url_test_result,
        "validation_reason": validation_reason,
        "provider_source": provider_source,
    })
    if url_test_result != "pass":
        return base_result

    network_defaults = defaults.get("network") if isinstance(defaults.get("network"), dict) else {}
    network_enabled = allow_network or bool(network_defaults.get("enabled")) or validation_mode == "provider_structural_cached_head"
    if not network_enabled:
        return base_result
    if not safe_text(url) or safe_text(url).startswith("/") or os.path.isabs(safe_text(url)):
        return base_result

    timeout_seconds = max(1, safe_int(network_defaults.get("timeout_seconds"), 5))
    retry_count = max(0, safe_int(network_defaults.get("retry_count"), 1))
    ttl_hours = max(1, safe_int(network_defaults.get("cache_ttl_hours"), 24))
    cache_doc = cache if isinstance(cache, dict) else {"version": 1, "entries": {}}
    entries = cache_doc.setdefault("entries", {})
    cache_key = _url_cache_key(url)
    cached = entries.get(cache_key) if isinstance(entries, dict) else None
    if isinstance(cached, dict) and _cache_is_fresh(cached, ttl_hours):
        base_result.update({
            "url_test_result": normalize_url_test(cached.get("url_test_result")) or base_result["url_test_result"],
            "validation_reason": safe_text(cached.get("validation_reason")) or base_result["validation_reason"],
            "network_checked": bool(cached.get("network_checked")),
            "http_status": cached.get("http_status"),
            "cache_hit": True,
        })
        return base_result

    final_result = "unknown"
    final_reason = "network validation unavailable"
    final_code: Optional[int] = None
    for _ in range(retry_count + 1):
        final_result, final_reason, final_code = _network_probe_once(url, timeout_seconds)
        if final_result in {"pass", "fail"}:
            break

    entry = {
        "url": safe_text(url),
        "checked_at": utc_iso(),
        "url_test_result": final_result,
        "validation_reason": final_reason,
        "network_checked": True,
        "http_status": final_code,
    }
    entries[cache_key] = entry
    base_result["network_checked"] = True
    base_result["http_status"] = final_code
    if final_result in {"pass", "fail"}:
        base_result["url_test_result"] = final_result
        base_result["validation_reason"] = final_reason
    else:
        base_result["validation_reason"] = f"{base_result['validation_reason']}; {final_reason}; structural result retained"
    return base_result


def derive_status_from_children(child_statuses: Iterable[str]) -> Tuple[str, str]:
    normalized = [normalize_status(value) for value in child_statuses if normalize_status(value)]
    if not normalized:
        return "unknown", "child availability unavailable"
    if "available" in normalized:
        return "available", "derived from child availability"
    if "unavailable" in normalized:
        return "unavailable", "derived from child availability"
    if "not_yet_released" in normalized:
        return "not_yet_released", "derived from child availability"
    return "unknown", "child availability indeterminate"


def validate_source_document(source: Dict[str, Any], known_keys: Optional[Iterable[str]] = None) -> List[str]:
    errors: List[str] = []
    if not isinstance(source, dict):
        return ["source document must be an object"]
    if not isinstance(source.get("records"), list):
        errors.append("records must be a list")
    defaults = source.get("defaults")
    if not isinstance(defaults, dict):
        errors.append("defaults must be an object")
    else:
        if normalize_validation_mode(defaults.get("validation_mode")) != safe_text(defaults.get("validation_mode")):
            errors.append("defaults.validation_mode must be one of: " + ", ".join(ALLOWED_VALIDATION_MODES))
        network = defaults.get("network")
        if network is not None and not isinstance(network, dict):
            errors.append("defaults.network must be an object")
        elif isinstance(network, dict):
            if safe_text(network.get("cache_file")) and ".." in safe_text(network.get("cache_file")).replace("\\", "/").split("/"):
                errors.append("defaults.network.cache_file must stay inside the repo")
        entities = defaults.get("entities")
        if not isinstance(entities, dict):
            errors.append("defaults.entities must be an object")
        else:
            for entity_type, payload in entities.items():
                if normalize_entity_type(entity_type) != entity_type:
                    errors.append(f"defaults.entities contains invalid entity type: {entity_type}")
                    continue
                if not isinstance(payload, dict):
                    errors.append(f"defaults.entities.{entity_type} must be an object")
                    continue
                preferred = payload.get("preferred_sources")
                if not isinstance(preferred, list) or not preferred:
                    errors.append(f"defaults.entities.{entity_type}.preferred_sources must be a non-empty list")
                elif any(normalize_source(item) != safe_text(item) for item in preferred):
                    errors.append(f"defaults.entities.{entity_type}.preferred_sources contains unsupported source")
    seen: Dict[str, int] = {}
    key_set = set(known_keys or [])
    for idx, record in enumerate(source.get("records") or []):
        if not isinstance(record, dict):
            errors.append(f"records[{idx}] must be an object")
            continue
        entity_type = normalize_entity_type(record.get("entity_type"))
        entity_key = safe_text(record.get("entity_key"))
        if not entity_type:
            errors.append(f"records[{idx}] invalid entity_type")
        if not entity_key:
            errors.append(f"records[{idx}] missing entity_key")
        elif entity_key in seen:
            errors.append(f"duplicate entity_key: {entity_key}")
        else:
            seen[entity_key] = idx
        status_override = record.get("status_override")
        if status_override not in (None, "") and not normalize_status(status_override):
            errors.append(f"records[{idx}] invalid status_override: {status_override}")
        url_test_result = record.get("url_test_result")
        if url_test_result not in (None, "") and not normalize_url_test(url_test_result):
            errors.append(f"records[{idx}] invalid url_test_result: {url_test_result}")
        preferred_source = record.get("preferred_source")
        if preferred_source not in (None, "") and not normalize_source(preferred_source):
            errors.append(f"records[{idx}] invalid preferred_source: {preferred_source}")
        primary_watch_url = safe_text(record.get("primary_watch_url"))
        if primary_watch_url and not is_valid_primary_url(primary_watch_url):
            errors.append(f"records[{idx}] invalid primary_watch_url: {primary_watch_url}")
        release_date_override = record.get("release_date_override")
        if release_date_override not in (None, "") and not to_date_key(release_date_override):
            errors.append(f"records[{idx}] invalid release_date_override: {release_date_override}")
        if key_set and entity_key and entity_key not in key_set:
            errors.append(f"records[{idx}] entity_key not found in data.json: {entity_key}")
    return errors


def resolve_availability(
    entity_type: str,
    entity: Dict[str, Any],
    context: Dict[str, Any],
    defaults: Dict[str, Any],
    streaming: Dict[str, str],
    record: Optional[Dict[str, Any]] = None,
    *,
    child_statuses: Optional[Iterable[str]] = None,
    allow_network: bool = False,
    cache: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    release_date = to_date_key((record or {}).get("release_date_override")) or pick_release_date(entity_type, entity)
    primary_watch_url, selected_source = choose_primary_watch_url(entity_type, entity, context, defaults, streaming, record)
    entities = defaults.get("entities") if isinstance(defaults.get("entities"), dict) else {}
    entity_defaults = entities.get(entity_type) if isinstance(entities.get(entity_type), dict) else {}
    requires_url = bool((record or {}).get("requires_url", entity_defaults.get("requires_url", True)))
    override = normalize_status((record or {}).get("status_override"))
    explicit_test = explicit_url_test_result(record)
    validation = validate_primary_watch_url(
        primary_watch_url,
        entity_type,
        entity,
        context,
        streaming,
        defaults,
        source_key=normalize_source((record or {}).get("preferred_source")) or selected_source,
        allow_network=allow_network,
        cache=cache,
    )
    if explicit_test:
        url_test_result = explicit_test
        validation_reason = safe_text((record or {}).get("reason")) or "manual url_test_result override"
    elif not requires_url:
        url_test_result = "skip"
        validation_reason = "URL validation skipped for this entity"
    else:
        url_test_result = validation["url_test_result"]
        validation_reason = validation["validation_reason"]

    if override:
        status = override
        reason = safe_text((record or {}).get("reason")) or "manual override"
        source = "watch_source_availability.json:override"
    elif is_future_date(release_date):
        status = "not_yet_released"
        reason = safe_text((record or {}).get("reason")) or f"release date {release_date} is in the future"
        source = "watch_source_availability.json:release_date"
    elif not release_date and entity_type in {"show", "season"}:
        child_status, child_reason = derive_status_from_children(child_statuses or [])
        status = child_status
        reason = safe_text((record or {}).get("reason")) or child_reason
        source = "watch_source_availability.json:child_status"
    elif not release_date:
        status = "unknown"
        reason = safe_text((record or {}).get("reason")) or "release date missing"
        source = "watch_source_availability.json:unknown"
    elif requires_url and url_test_result == "pass":
        status = "available"
        reason = safe_text((record or {}).get("reason")) or validation_reason
        source = "watch_source_availability.json:derived"
    elif requires_url and not primary_watch_url:
        status = "unavailable"
        reason = safe_text((record or {}).get("reason")) or "released but primary watch URL is missing"
        source = "watch_source_availability.json:derived"
    elif requires_url:
        status = "unavailable"
        reason = safe_text((record or {}).get("reason")) or validation_reason or "released but primary watch URL failed validation"
        source = "watch_source_availability.json:derived"
    else:
        status = "unknown"
        reason = safe_text((record or {}).get("reason")) or "indeterminate availability"
        source = "watch_source_availability.json:unknown"

    return {
        "availability_status": status,
        "availability_checked_at": utc_iso(),
        "availability_source": source,
        "availability_reason": reason,
        "primary_watch_url_tested": primary_watch_url or None,
        "url_test_result": url_test_result,
        "url_validation_reason": validation_reason,
        "provider_source": validation.get("provider_source") or selected_source or None,
        "validation_mode": validation.get("validation_mode") or normalize_validation_mode(defaults.get("validation_mode")) or "provider_structural",
        "network_checked": bool(validation.get("network_checked")),
        "cache_hit": bool(validation.get("cache_hit")),
        "http_status": validation.get("http_status"),
        "release_date": release_date,
        "requires_url": requires_url,
    }
