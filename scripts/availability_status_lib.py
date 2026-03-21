#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/availability_status_lib.py
# [PROJECT] my_TV_Movie
# [ROLE]    Shared availability-status helpers for source validation and data
#           enrichment.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.01
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
SOURCE_JSON = REPO_ROOT / "data" / "watch_source_availability.json"
CONFIG_JSON = REPO_ROOT / "web" / "config.json"

ALLOWED_ENTITY_TYPES = ("movie", "show", "season", "episode")
ALLOWED_AVAILABILITY = ("not_yet_released", "available", "unavailable", "unknown")
ALLOWED_URL_TEST = ("pass", "fail", "skip", "unknown")
DEFAULT_SOURCE_VERSION = "1.1.0"


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


def safe_text(value: Any) -> str:
    return str(value or "").strip()


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
        "validation_mode": "structural",
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
            "validation_mode": safe_text(incoming_defaults.get("validation_mode")) or defaults["validation_mode"],
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
        values = {"tmdb_id": parts[0] if len(parts) > 0 else "", "season": parts[1] if len(parts) > 1 else "", "episode": parts[2] if len(parts) > 2 else ""}
        try:
            return root.format(**values)
        except Exception:
            return ""
    if not suffix:
        return root
    return f"{root}/{suffix}"


def load_streaming_config(config_path: Path = CONFIG_JSON) -> Dict[str, str]:
    cfg = load_json(config_path, allow_jsonc=True)
    streaming = cfg.get("streaming") or cfg.get("streaming_services") or {}
    if not isinstance(streaming, dict):
        streaming = {}
    return {
        "vidsrc_tv": safe_text(streaming.get("vidsrc_tv")),
        "vidsrc_movie": safe_text(streaming.get("vidsrc_movie")),
        "videasy_tv": safe_text(streaming.get("videasy_tv")),
        "videasy_movie": safe_text(streaming.get("videasy_movie")),
    }


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


def choose_primary_watch_url(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any], defaults: Dict[str, Any], streaming: Dict[str, str], record: Optional[Dict[str, Any]] = None) -> str:
    explicit = safe_text((record or {}).get("primary_watch_url"))
    if explicit:
        return explicit
    entities = defaults.get("entities") if isinstance(defaults.get("entities"), dict) else {}
    entity_defaults = entities.get(entity_type) if isinstance(entities.get(entity_type), dict) else {}
    preferred = entity_defaults.get("preferred_sources")
    candidates = entity_candidates(entity_type, entity, context, streaming)
    order = list(preferred) if isinstance(preferred, list) and preferred else ["videasy", "vidsrc", "local"]
    for key in order:
        url = safe_text(candidates.get(str(key)))
        if url:
            return url
    for value in candidates.values():
        if safe_text(value):
            return safe_text(value)
    return ""


def is_valid_primary_url(url: str) -> bool:
    value = safe_text(url)
    if not value:
        return False
    if value.startswith("/") or os.path.isabs(value):
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


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
                elif any(safe_text(item) not in {"videasy", "vidsrc", "local"} for item in preferred):
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
        primary_watch_url = safe_text(record.get("primary_watch_url"))
        if primary_watch_url and not is_valid_primary_url(primary_watch_url):
            errors.append(f"records[{idx}] invalid primary_watch_url: {primary_watch_url}")
        release_date_override = record.get("release_date_override")
        if release_date_override not in (None, "") and not to_date_key(release_date_override):
            errors.append(f"records[{idx}] invalid release_date_override: {release_date_override}")
        if key_set and entity_key and entity_key not in key_set:
            errors.append(f"records[{idx}] entity_key not found in data.json: {entity_key}")
    return errors


def resolve_availability(entity_type: str, entity: Dict[str, Any], context: Dict[str, Any], defaults: Dict[str, Any], streaming: Dict[str, str], record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    release_date = to_date_key((record or {}).get("release_date_override")) or pick_release_date(entity_type, entity)
    primary_watch_url = choose_primary_watch_url(entity_type, entity, context, defaults, streaming, record)
    entities = defaults.get("entities") if isinstance(defaults.get("entities"), dict) else {}
    entity_defaults = entities.get(entity_type) if isinstance(entities.get(entity_type), dict) else {}
    requires_url = bool((record or {}).get("requires_url", entity_defaults.get("requires_url", True)))
    override = normalize_status((record or {}).get("status_override"))
    explicit_test = explicit_url_test_result(record)
    if explicit_test:
        url_test_result = explicit_test
    elif not requires_url:
        url_test_result = "skip"
    elif is_valid_primary_url(primary_watch_url):
        url_test_result = "pass"
    else:
        url_test_result = "fail"

    if override:
        status = override
        reason = safe_text((record or {}).get("reason")) or "manual override"
        source = "watch_source_availability.json:override"
    elif is_future_date(release_date):
        status = "not_yet_released"
        reason = safe_text((record or {}).get("reason")) or f"release date {release_date} is in the future"
        source = "watch_source_availability.json:release_date"
    elif not release_date:
        status = "unknown"
        reason = safe_text((record or {}).get("reason")) or "release date missing"
        source = "watch_source_availability.json:unknown"
    elif requires_url and url_test_result == "pass":
        status = "available"
        reason = safe_text((record or {}).get("reason")) or "released and primary watch URL passed structural validation"
        source = "watch_source_availability.json:derived"
    elif requires_url and not primary_watch_url:
        status = "unavailable"
        reason = safe_text((record or {}).get("reason")) or "released but primary watch URL is missing"
        source = "watch_source_availability.json:derived"
    elif requires_url:
        status = "unavailable"
        reason = safe_text((record or {}).get("reason")) or "released but primary watch URL failed validation"
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
        "release_date": release_date,
        "requires_url": requires_url,
    }
