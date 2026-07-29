#!/usr/bin/env python3
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
ASSETS_DIR = REPO_ROOT / "assets"
SOURCE_JSON = DATA_DIR / "data.json"
INDEX_JSON = DATA_DIR / "catalog_index.json"
CALENDAR_JSON = DATA_DIR / "calendar.json"
DETAIL_DIR = DATA_DIR / "catalog_detail"
REGIONS = ("CA", "US", "GB", "AU")
PROVIDER_BUCKETS = ("flatrate", "free", "ads", "rent", "buy")


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def _provider_logo_local(path: Any) -> str:
    raw = _safe_text(path)
    if not raw.startswith("/"):
        return ""
    filename = raw.split("/")[-1]
    if not filename:
        return ""
    asset_path = ASSETS_DIR / "logos" / "services" / filename
    return f"/assets/logos/services/{filename}" if asset_path.exists() else ""


def _normalize_provider_rows(region_block: Dict[str, Any], deep_link: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    for bucket in PROVIDER_BUCKETS:
        providers = region_block.get(bucket)
        if not isinstance(providers, list):
            continue
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            provider_id = _safe_int(provider.get("provider_id"))
            provider_name = _safe_text(provider.get("provider_name") or provider.get("name"))
            dedupe_key = (str(provider_id or provider_name), bucket)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            rows.append(
                {
                    "provider_id": provider_id or None,
                    "provider_name": provider_name,
                    "logo_path": _safe_text(provider.get("logo_path")),
                    "logo_local": _provider_logo_local(provider.get("logo_path")),
                    "availability_type": bucket,
                    "display_priority": _safe_int(provider.get("display_priority"), 999),
                    "deep_link": deep_link,
                }
            )
    rows.sort(key=lambda row: (row.get("display_priority") or 999, _safe_text(row.get("provider_name"))))
    return rows


def _normalize_watch_providers(watch_providers: Any, provider_page: str = "") -> Dict[str, List[Dict[str, Any]]]:
    source = watch_providers if isinstance(watch_providers, dict) else {}
    results = source.get("results") if isinstance(source.get("results"), dict) else source
    out: Dict[str, List[Dict[str, Any]]] = {}
    for region in REGIONS:
        region_block = results.get(region) if isinstance(results, dict) else None
        if not isinstance(region_block, dict):
            out[region] = []
            continue
        deep_link = _safe_text(region_block.get("link") or provider_page)
        out[region] = _normalize_provider_rows(region_block, deep_link)
    return out


def _normalize_embed_sources(entity: Dict[str, Any]) -> List[Dict[str, Any]]:
    links = entity.get("links") if isinstance(entity.get("links"), dict) else {}
    out: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    local_href = _safe_text(links.get("local_media") or links.get("local") or links.get("localMedia"))
    if local_href:
        out.append(
            {
                "key": "local",
                "label": "Local Server / Owned",
                "href": local_href,
                "type": "local",
                "status": "ok",
                "style": "direct",
                "priority": -1,
            }
        )
        seen.add(("local", local_href))

    out.sort(key=lambda row: (_safe_int(row.get("priority"), 999), _safe_text(row.get("label"))))
    return out


def _normalize_watch(entity: Dict[str, Any], fallback_providers: Dict[str, List[Dict[str, Any]]] | None = None) -> Dict[str, Any]:
    links = entity.get("links") if isinstance(entity.get("links"), dict) else {}
    providers = _normalize_watch_providers(entity.get("watch_providers"), _safe_text(links.get("provider_page")))
    if fallback_providers:
        for region in REGIONS:
            if not providers.get(region):
                providers[region] = list(fallback_providers.get(region) or [])
    return {"embed": _normalize_embed_sources(entity), "providers": providers}


def _provider_summary(providers: Dict[str, List[Dict[str, Any]]]) -> str:
    for region in REGIONS:
        names = [_safe_text(row.get("provider_name")) for row in providers.get(region) or [] if _safe_text(row.get("provider_name"))]
        if names:
            return " • ".join(names[:4])
    return ""


def _base_index_fields(entity: Dict[str, Any], media_type: str) -> Dict[str, Any]:
    entity_id = _safe_int(entity.get("tmdb_id") or entity.get("id"))
    release_date = _safe_text(entity.get("release_date") or entity.get("first_air_date") or entity.get("air_date"))
    watch = _normalize_watch(entity)
    return {
        "id": entity_id,
        "tmdb_id": entity_id,
        "type": media_type,
        "title": _safe_text(entity.get("title") or entity.get("name")),
        "year": _safe_text(release_date[:4]),
        "release_date": release_date,
        "status": _safe_text(entity.get("status")),
        "overview": _safe_text(entity.get("overview")),
        "poster_path": _safe_text(entity.get("poster_path")),
        "poster_local": _safe_text(entity.get("poster_local")),
        "backdrop_path": _safe_text(entity.get("backdrop_path")),
        "backdrop_local": _safe_text(entity.get("backdrop_local")),
        "genres": entity.get("genres") if isinstance(entity.get("genres"), list) else [],
        "popularity": entity.get("popularity"),
        "vote_average": entity.get("vote_average"),
        "vote_count": entity.get("vote_count"),
        "availability_status": _safe_text(entity.get("availability_status")),
        "availability_checked_at": _safe_text(entity.get("availability_checked_at")),
        "availability_source": _safe_text(entity.get("availability_source")),
        "availability_reason": _safe_text(entity.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(entity.get("primary_watch_url_tested")),
        "watch_summary": _provider_summary(watch["providers"]),
        "watch_embed_count": len(watch["embed"]),
        "provider_regions": [region for region in REGIONS if watch["providers"].get(region)],
        "detail_path": f"/data/catalog_detail/{entity_id}.json",
    }


def _detail_movie(movie: Dict[str, Any]) -> Dict[str, Any]:
    entity_id = _safe_int(movie.get("tmdb_id") or movie.get("id"))
    links = movie.get("links") if isinstance(movie.get("links"), dict) else {}
    return {
        "id": entity_id,
        "tmdb_id": entity_id,
        "type": "movie",
        "title": _safe_text(movie.get("title")),
        "original_title": _safe_text(movie.get("original_title")),
        "release_date": _safe_text(movie.get("release_date")),
        "poster_path": _safe_text(movie.get("poster_path")),
        "poster_local": _safe_text(movie.get("poster_local")),
        "backdrop_path": _safe_text(movie.get("backdrop_path")),
        "backdrop_local": _safe_text(movie.get("backdrop_local")),
        "status": _safe_text(movie.get("status")),
        "overview": _safe_text(movie.get("overview")),
        "tagline": _safe_text(movie.get("tagline")),
        "homepage": _safe_text(movie.get("homepage")),
        "provider_page": _safe_text(links.get("provider_page")),
        "tmdb_url": _safe_text(links.get("tmdb")),
        "runtime": movie.get("runtime"),
        "genres": movie.get("genres") if isinstance(movie.get("genres"), list) else [],
        "collection": movie.get("collection"),
        "production_companies": movie.get("production_companies") if isinstance(movie.get("production_companies"), list) else [],
        "production_countries": movie.get("production_countries") if isinstance(movie.get("production_countries"), list) else [],
        "popularity": movie.get("popularity"),
        "vote_average": movie.get("vote_average"),
        "vote_count": movie.get("vote_count"),
        "availability_status": _safe_text(movie.get("availability_status")),
        "availability_checked_at": _safe_text(movie.get("availability_checked_at")),
        "availability_source": _safe_text(movie.get("availability_source")),
        "availability_reason": _safe_text(movie.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(movie.get("primary_watch_url_tested")),
        "watch": _normalize_watch(movie),
    }


def _detail_episode(episode: Dict[str, Any], show_watch: Dict[str, Any]) -> Dict[str, Any]:
    links = episode.get("links") if isinstance(episode.get("links"), dict) else {}
    return {
        "id": _safe_int(episode.get("id")),
        "type": "episode",
        "show_id": _safe_int(episode.get("show_id")),
        "season_number": _safe_int(episode.get("season_number")),
        "episode_number": _safe_int(episode.get("episode_number") or episode.get("number")),
        "name": _safe_text(episode.get("name") or episode.get("title")),
        "air_date": _safe_text(episode.get("air_date")),
        "runtime": episode.get("runtime"),
        "still_path": _safe_text(episode.get("still_path")),
        "still_local": _safe_text(episode.get("still_local")),
        "overview": _safe_text(episode.get("overview")),
        "vote_average": episode.get("vote_average"),
        "vote_count": episode.get("vote_count"),
        "provider_page": _safe_text(links.get("provider_page")),
        "tmdb_url": _safe_text(links.get("tmdb")),
        "availability_status": _safe_text(episode.get("availability_status")),
        "availability_checked_at": _safe_text(episode.get("availability_checked_at")),
        "availability_source": _safe_text(episode.get("availability_source")),
        "availability_reason": _safe_text(episode.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(episode.get("primary_watch_url_tested")),
        "watch": _normalize_watch(episode, show_watch["providers"]),
    }


def _detail_season(season: Dict[str, Any], show_watch: Dict[str, Any]) -> Dict[str, Any]:
    links = season.get("links") if isinstance(season.get("links"), dict) else {}
    return {
        "id": _safe_int(season.get("tmdb_season_id") or season.get("id")),
        "type": "season",
        "season_number": _safe_int(season.get("season_number") or season.get("number")),
        "name": _safe_text(season.get("name")),
        "premiere_date": _safe_text(season.get("air_date")),
        "poster_path": _safe_text(season.get("poster_path")),
        "poster_local": _safe_text(season.get("poster_local")),
        "backdrop_path": _safe_text(season.get("backdrop_path")),
        "backdrop_local": _safe_text(season.get("backdrop_local")),
        "overview": _safe_text(season.get("overview")),
        "status": _safe_text(season.get("status") or season.get("availability_status")),
        "episode_count": _safe_int(season.get("episode_count") or len(season.get("episodes") or [])),
        "provider_page": _safe_text(links.get("provider_page")),
        "tmdb_url": _safe_text(links.get("tmdb")),
        "availability_status": _safe_text(season.get("availability_status")),
        "availability_checked_at": _safe_text(season.get("availability_checked_at")),
        "availability_source": _safe_text(season.get("availability_source")),
        "availability_reason": _safe_text(season.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(season.get("primary_watch_url_tested")),
        "watch": _normalize_watch(season, show_watch["providers"]),
        "episodes": [_detail_episode(episode, show_watch) for episode in (season.get("episodes") or []) if isinstance(episode, dict)],
    }


def _detail_show(show: Dict[str, Any]) -> Dict[str, Any]:
    entity_id = _safe_int(show.get("tmdb_id") or show.get("id"))
    links = show.get("links") if isinstance(show.get("links"), dict) else {}
    show_watch = _normalize_watch(show)
    return {
        "id": entity_id,
        "tmdb_id": entity_id,
        "type": "tv",
        "title": _safe_text(show.get("title") or show.get("name")),
        "name": _safe_text(show.get("name") or show.get("title")),
        "original_name": _safe_text(show.get("original_name")),
        "first_air_date": _safe_text(show.get("first_air_date")),
        "poster_path": _safe_text(show.get("poster_path")),
        "poster_local": _safe_text(show.get("poster_local")),
        "backdrop_path": _safe_text(show.get("backdrop_path")),
        "backdrop_local": _safe_text(show.get("backdrop_local")),
        "status": _safe_text(show.get("status")),
        "overview": _safe_text(show.get("overview")),
        "homepage": _safe_text(show.get("homepage")),
        "provider_page": _safe_text(links.get("provider_page")),
        "tmdb_url": _safe_text(links.get("tmdb")),
        "genres": show.get("genres") if isinstance(show.get("genres"), list) else [],
        "networks": show.get("networks") if isinstance(show.get("networks"), list) else [],
        "created_by": show.get("created_by") if isinstance(show.get("created_by"), list) else [],
        "origin_country": show.get("origin_country") if isinstance(show.get("origin_country"), list) else [],
        "in_production": bool(show.get("in_production")),
        "number_of_seasons": _safe_int(show.get("number_of_seasons")),
        "number_of_episodes": _safe_int(show.get("number_of_episodes")),
        "episode_run_time": show.get("episode_run_time") if isinstance(show.get("episode_run_time"), list) else [],
        "last_air_date": _safe_text(show.get("last_air_date")),
        "next_episode_to_air": show.get("next_episode_to_air") if isinstance(show.get("next_episode_to_air"), dict) else show.get("next_episode_to_air"),
        "last_episode_to_air": show.get("last_episode_to_air") if isinstance(show.get("last_episode_to_air"), dict) else show.get("last_episode_to_air"),
        "popularity": show.get("popularity"),
        "vote_average": show.get("vote_average"),
        "vote_count": show.get("vote_count"),
        "availability_status": _safe_text(show.get("availability_status")),
        "availability_checked_at": _safe_text(show.get("availability_checked_at")),
        "availability_source": _safe_text(show.get("availability_source")),
        "availability_reason": _safe_text(show.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(show.get("primary_watch_url_tested")),
        "watch": show_watch,
        "seasons": [_detail_season(season, show_watch) for season in (show.get("seasons") or []) if isinstance(season, dict)],
    }


def _calendar_episode_entry(show: Dict[str, Any], season: Dict[str, Any], episode: Dict[str, Any], show_index: Dict[str, Any]) -> Dict[str, Any]:
    networks = show.get("networks") if isinstance(show.get("networks"), list) else []
    network = networks[0] if networks and isinstance(networks[0], dict) else {}
    date_key = _safe_text(episode.get("air_date"))[:10]
    return {
        "kind": "episode",
        "date": date_key,
        "show_id": _safe_int(show.get("tmdb_id") or show.get("id")),
        "show_tmdb_id": _safe_int(show.get("tmdb_id") or show.get("id")),
        "show_title": _safe_text(show.get("title") or show.get("name")),
        "show_poster_local": _safe_text(show_index.get("poster_local")),
        "show_backdrop_local": _safe_text(show_index.get("backdrop_local")),
        "season_number": _safe_int(episode.get("season_number") or season.get("season_number")),
        "episode_number": _safe_int(episode.get("episode_number") or episode.get("number")),
        "episode_name": _safe_text(episode.get("name") or episode.get("title")),
        "runtime": episode.get("runtime"),
        "thumb": _safe_text(episode.get("still_local") or season.get("poster_local") or show_index.get("poster_local") or show_index.get("backdrop_local")),
        "still_local": _safe_text(episode.get("still_local")),
        "still_path": _safe_text(episode.get("still_path")),
        "network_name": _safe_text(network.get("name")),
        "network_logo_tmdb": _safe_text(network.get("logo_path")),
        "progress": round(float(episode.get("vote_average") or 0) * 10) if episode.get("vote_average") is not None else None,
        "availability_status": _safe_text(episode.get("availability_status")),
        "availability_checked_at": _safe_text(episode.get("availability_checked_at")),
        "availability_source": _safe_text(episode.get("availability_source")),
        "availability_reason": _safe_text(episode.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(episode.get("primary_watch_url_tested")),
        "has_watch_sources": bool(_normalize_embed_sources(episode)),
    }


def _calendar_movie_entry(movie: Dict[str, Any], movie_index: Dict[str, Any]) -> Dict[str, Any]:
    date_key = _safe_text(movie.get("release_date"))[:10]
    return {
        "kind": "movie",
        "date": date_key,
        "id": _safe_int(movie.get("tmdb_id") or movie.get("id")),
        "tmdb_id": _safe_int(movie.get("tmdb_id") or movie.get("id")),
        "title": _safe_text(movie.get("title")),
        "thumb": _safe_text(movie_index.get("poster_local") or movie_index.get("backdrop_local")),
        "poster_local": _safe_text(movie_index.get("poster_local")),
        "backdrop_local": _safe_text(movie_index.get("backdrop_local")),
        "runtime": movie.get("runtime"),
        "progress": round(float(movie.get("vote_average") or 0) * 10) if movie.get("vote_average") is not None else None,
        "availability_status": _safe_text(movie.get("availability_status")),
        "availability_checked_at": _safe_text(movie.get("availability_checked_at")),
        "availability_source": _safe_text(movie.get("availability_source")),
        "availability_reason": _safe_text(movie.get("availability_reason")),
        "primary_watch_url_tested": _safe_text(movie.get("primary_watch_url_tested")),
        "has_watch_sources": bool(_normalize_embed_sources(movie)),
    }


def _clear_detail_dir(active_ids: Iterable[int]) -> None:
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)
    keep = {f"{entity_id}.json" for entity_id in active_ids if entity_id}
    for existing in DETAIL_DIR.glob("*.json"):
        if existing.name not in keep:
            existing.unlink()


def main() -> int:
    data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    shows = [show for show in (data.get("shows") or []) if isinstance(show, dict)]
    movies = [movie for movie in (data.get("movies") or []) if isinstance(movie, dict)]

    index = {
        "meta": {
            "generated_utc": _utc_iso(),
            "schema": "catalog_index.v1",
            "source": "data/data.json",
            "detail_dir": "/data/catalog_detail",
            "calendar": "/data/calendar.json",
        },
        "shows": [],
        "movies": [],
        "errors": data.get("errors") if isinstance(data.get("errors"), list) else [],
    }
    calendar_days: Dict[str, List[Dict[str, Any]]] = {}
    detail_ids: List[int] = []

    for show in shows:
        show_index = _base_index_fields(show, "tv")
        show_index.update(
            {
                "first_air_date": _safe_text(show.get("first_air_date")),
                "number_of_seasons": _safe_int(show.get("number_of_seasons")),
                "number_of_episodes": _safe_int(show.get("number_of_episodes")),
                "in_production": bool(show.get("in_production")),
                "last_air_date": _safe_text(show.get("last_air_date")),
                "episode_run_time": show.get("episode_run_time") if isinstance(show.get("episode_run_time"), list) else [],
                "networks": show.get("networks") if isinstance(show.get("networks"), list) else [],
                "season_episode_counts": [
                    {
                        "season_number": _safe_int(season.get("season_number") or season.get("number")),
                        "episode_count": len(season.get("episodes") or []),
                    }
                    for season in (show.get("seasons") or [])
                    if isinstance(season, dict)
                ],
            }
        )
        index["shows"].append(show_index)
        detail = _detail_show(show)
        entity_id = _safe_int(detail.get("id"))
        detail_ids.append(entity_id)
        _write_json(DETAIL_DIR / f"{entity_id}.json", detail)
        for season in show.get("seasons") or []:
            if not isinstance(season, dict):
                continue
            for episode in season.get("episodes") or []:
                if not isinstance(episode, dict):
                    continue
                date_key = _safe_text(episode.get("air_date"))[:10]
                if len(date_key) != 10:
                    continue
                calendar_days.setdefault(date_key, []).append(_calendar_episode_entry(show, season, episode, show_index))

    for movie in movies:
        movie_index = _base_index_fields(movie, "movie")
        movie_index.update({"runtime": movie.get("runtime"), "collection": movie.get("collection")})
        index["movies"].append(movie_index)
        detail = _detail_movie(movie)
        entity_id = _safe_int(detail.get("id"))
        detail_ids.append(entity_id)
        _write_json(DETAIL_DIR / f"{entity_id}.json", detail)
        date_key = _safe_text(movie.get("release_date"))[:10]
        if len(date_key) == 10:
            calendar_days.setdefault(date_key, []).append(_calendar_movie_entry(movie, movie_index))

    index["shows"].sort(key=lambda row: _safe_text(row.get("title")).lower())
    index["movies"].sort(key=lambda row: _safe_text(row.get("title")).lower())

    for entries in calendar_days.values():
        entries.sort(key=lambda row: (0 if row.get("kind") == "episode" else 1, _safe_text(row.get("show_title") or row.get("title")).lower()))

    calendar = {
        "meta": {
            "generated_utc": _utc_iso(),
            "schema": "calendar.v1",
            "source": "data/data.json",
            "detail_dir": "/data/catalog_detail",
        },
        "days": dict(sorted(calendar_days.items())),
    }

    _clear_detail_dir(detail_ids)
    _write_json(INDEX_JSON, index)
    _write_json(CALENDAR_JSON, calendar)
    print(json.dumps({"result": "OK", "catalog_index": str(INDEX_JSON), "calendar": str(CALENDAR_JSON), "detail_count": len(detail_ids)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
