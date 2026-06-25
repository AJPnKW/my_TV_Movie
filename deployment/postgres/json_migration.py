"""JSON import/export tooling for the server-mode PostgreSQL migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1] / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from postgres_client import PostgresClient, PostgresUnavailable
from server_mode_config import ServerModeConfig


def load_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except Exception:
        return default


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def as_date(value: Any) -> str | None:
    text = as_text(value)
    if not text or len(text) < 10:
        return None
    return text[:10]


def media_title(row: dict[str, Any], fallback: str = "") -> str:
    for key in ("title", "name", "canonical_title", "original_title", "original_name"):
        value = as_text(row.get(key))
        if value:
            return value
    return fallback


def first_network_name(show: dict[str, Any]) -> str | None:
    networks = show.get("networks")
    if isinstance(networks, list) and networks:
        first = networks[0]
        if isinstance(first, dict):
            return as_text(first.get("name"))
    return None


def origin_country(show: dict[str, Any]) -> str | None:
    countries = show.get("origin_country")
    if isinstance(countries, list):
        return ",".join(str(country).strip() for country in countries if str(country).strip()) or None
    return as_text(countries)


def runtime_minutes(row: dict[str, Any]) -> int | None:
    value = row.get("runtime")
    if value is None and isinstance(row.get("episode_run_time"), list) and row["episode_run_time"]:
        value = row["episode_run_time"][0]
    return as_int(value)


def image_path(row: dict[str, Any], local_key: str, remote_key: str) -> str | None:
    return as_text(row.get(local_key)) or as_text(row.get(remote_key))


def catalog_shape(config: ServerModeConfig) -> dict[str, Any]:
    payload = load_json(config.data_path("data.json"), {}) or {}
    shows = payload.get("shows") if isinstance(payload, dict) else []
    movies = payload.get("movies") if isinstance(payload, dict) else []
    seasons = 0
    episodes = 0
    for show in shows if isinstance(shows, list) else []:
        show_seasons = show.get("seasons") if isinstance(show, dict) else []
        seasons += len(show_seasons) if isinstance(show_seasons, list) else 0
        for season in show_seasons if isinstance(show_seasons, list) else []:
            season_episodes = season.get("episodes") if isinstance(season, dict) else []
            episodes += len(season_episodes) if isinstance(season_episodes, list) else 0
    return {
        "shows": len(shows) if isinstance(shows, list) else 0,
        "seasons": seasons,
        "episodes": episodes,
        "movies": len(movies) if isinstance(movies, list) else 0,
    }


def migration_summary(config: ServerModeConfig) -> dict[str, Any]:
    shape = catalog_shape(config)
    queue_payload = load_json(config.data_path("watch_state_queue.json"), {}) or {}
    queue_items = queue_payload.get("items") if isinstance(queue_payload, dict) else []
    inputs_payload = load_json(config.data_path("inputs.json"), {}) or {}
    watchlist = inputs_payload.get("watchlist") if isinstance(inputs_payload, dict) else []
    return {
        "mode": "dry_run",
        "candidate_count": sum(shape.values()),
        "by_type": shape,
        "state_candidates": {
            "inputs_watchlist": len(watchlist) if isinstance(watchlist, list) else 0,
            "watch_state_queue": len(queue_items) if isinstance(queue_items, list) else 0,
        },
        "sources": {
            "inputs_json": config.data_path("inputs.json").exists(),
            "data_json": config.data_path("data.json").exists(),
            "watch_state_queue_json": config.data_path("watch_state_queue.json").exists(),
            "catalog_detail_dir": config.data_path("catalog_detail").exists(),
        },
        "postgres_primary": True,
        "json_fallback": True,
        "stores_binary_assets": False,
    }


def fetch_returning(cur: Any, sql: str, params: tuple[Any, ...]) -> dict[str, Any]:
    cur.execute(sql, params)
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("expected RETURNING row from PostgreSQL upsert")
    return row


def upsert_media_item(
    cur: Any,
    *,
    media_type: str,
    title: str,
    tmdb_id: int | None,
    parent_media_item_id: int | None = None,
    row: dict[str, Any],
    source_key: str,
    release_date: str | None = None,
    runtime: int | None = None,
    poster_path: str | None = None,
    backdrop_path: str | None = None,
    still_path: str | None = None,
) -> int:
    if tmdb_id is None:
        existing = None
    else:
        cur.execute(
            "SELECT media_item_id FROM media_items WHERE media_type = %s AND tmdb_id = %s",
            (media_type, tmdb_id),
        )
        existing = cur.fetchone()
    if existing:
        media_item_id = existing["media_item_id"]
        cur.execute(
            """
            UPDATE media_items
            SET canonical_title = %s,
                parent_media_item_id = %s,
                imdb_id = %s,
                tvdb_id = %s,
                trakt_id = %s,
                release_date = %s,
                runtime_minutes = %s,
                overview = %s,
                poster_path = %s,
                backdrop_path = %s,
                still_path = %s,
                source_json_path = 'data/data.json',
                source_json_key = %s,
                source_hash = %s,
                raw_json = %s::jsonb
            WHERE media_item_id = %s
            """,
            (
                title,
                parent_media_item_id,
                as_text(row.get("imdb_id")),
                as_int(row.get("tvdb_id")),
                as_int(row.get("trakt_id")),
                release_date,
                runtime,
                as_text(row.get("overview")),
                poster_path,
                backdrop_path,
                still_path,
                source_key,
                stable_hash(row),
                PostgresClient.json_param(row),
                media_item_id,
            ),
        )
        return int(media_item_id)
    inserted = fetch_returning(
        cur,
        """
        INSERT INTO media_items (
            media_type, canonical_title, parent_media_item_id, tmdb_id, imdb_id, tvdb_id, trakt_id,
            release_date, runtime_minutes, overview, poster_path, backdrop_path, still_path,
            source_json_path, source_json_key, source_hash, raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'data/data.json', %s, %s, %s::jsonb)
        RETURNING media_item_id
        """,
        (
            media_type,
            title,
            parent_media_item_id,
            tmdb_id,
            as_text(row.get("imdb_id")),
            as_int(row.get("tvdb_id")),
            as_int(row.get("trakt_id")),
            release_date,
            runtime,
            as_text(row.get("overview")),
            poster_path,
            backdrop_path,
            still_path,
            source_key,
            stable_hash(row),
            PostgresClient.json_param(row),
        ),
    )
    return int(inserted["media_item_id"])


def upsert_show(cur: Any, show: dict[str, Any], media_item_id: int) -> int:
    row = fetch_returning(
        cur,
        """
        INSERT INTO shows (
            media_item_id, tmdb_show_id, first_air_date, last_air_date, status,
            network_name, origin_country, season_count, episode_count
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (media_item_id) DO UPDATE SET
            tmdb_show_id = EXCLUDED.tmdb_show_id,
            first_air_date = EXCLUDED.first_air_date,
            last_air_date = EXCLUDED.last_air_date,
            status = EXCLUDED.status,
            network_name = EXCLUDED.network_name,
            origin_country = EXCLUDED.origin_country,
            season_count = EXCLUDED.season_count,
            episode_count = EXCLUDED.episode_count
        RETURNING show_id
        """,
        (
            media_item_id,
            as_int(show.get("tmdb_id") or show.get("id")),
            as_date(show.get("first_air_date")),
            as_date(show.get("last_air_date")),
            as_text(show.get("status")),
            first_network_name(show),
            origin_country(show),
            as_int(show.get("number_of_seasons")),
            as_int(show.get("number_of_episodes")),
        ),
    )
    return int(row["show_id"])


def upsert_season(cur: Any, season: dict[str, Any], show_id: int, media_item_id: int) -> int:
    row = fetch_returning(
        cur,
        """
        INSERT INTO seasons (media_item_id, show_id, season_number, tmdb_season_id, title, air_date, episode_count, poster_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (show_id, season_number) DO UPDATE SET
            media_item_id = EXCLUDED.media_item_id,
            tmdb_season_id = EXCLUDED.tmdb_season_id,
            title = EXCLUDED.title,
            air_date = EXCLUDED.air_date,
            episode_count = EXCLUDED.episode_count,
            poster_path = EXCLUDED.poster_path
        RETURNING season_id
        """,
        (
            media_item_id,
            show_id,
            as_int(season.get("season_number")) or 0,
            as_int(season.get("id") or season.get("_id")),
            media_title(season, f"Season {as_int(season.get('season_number')) or 0}"),
            as_date(season.get("air_date")),
            as_int(season.get("episode_count")) or len(season.get("episodes") or []),
            image_path(season, "poster_local", "poster_path"),
        ),
    )
    return int(row["season_id"])


def upsert_episode(cur: Any, episode: dict[str, Any], show_id: int, season_id: int, media_item_id: int) -> None:
    cur.execute(
        """
        INSERT INTO episodes (
            media_item_id, show_id, season_id, season_number, episode_number,
            tmdb_episode_id, title, air_date, runtime_minutes, still_path
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (show_id, season_number, episode_number) DO UPDATE SET
            media_item_id = EXCLUDED.media_item_id,
            season_id = EXCLUDED.season_id,
            tmdb_episode_id = EXCLUDED.tmdb_episode_id,
            title = EXCLUDED.title,
            air_date = EXCLUDED.air_date,
            runtime_minutes = EXCLUDED.runtime_minutes,
            still_path = EXCLUDED.still_path
        """,
        (
            media_item_id,
            show_id,
            season_id,
            as_int(episode.get("season_number")) or 0,
            as_int(episode.get("episode_number")) or 0,
            as_int(episode.get("id")),
            media_title(episode, "Episode"),
            as_date(episode.get("air_date")),
            runtime_minutes(episode),
            image_path(episode, "still_local", "still_path"),
        ),
    )


def upsert_movie(cur: Any, movie: dict[str, Any], media_item_id: int) -> None:
    cur.execute(
        """
        INSERT INTO movies (media_item_id, tmdb_movie_id, title, release_date, runtime_minutes)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (media_item_id) DO UPDATE SET
            tmdb_movie_id = EXCLUDED.tmdb_movie_id,
            title = EXCLUDED.title,
            release_date = EXCLUDED.release_date,
            runtime_minutes = EXCLUDED.runtime_minutes
        """,
        (
            media_item_id,
            as_int(movie.get("tmdb_id") or movie.get("id")),
            media_title(movie, "Movie"),
            as_date(movie.get("release_date")),
            runtime_minutes(movie),
        ),
    )


def resolve_media_item(cur: Any, item: dict[str, Any]) -> int | None:
    state_ids = item.get("ids") if isinstance(item.get("ids"), dict) else {}
    media_type = as_text(item.get("media_type") or item.get("item_type") or item.get("kind"))
    tmdb_id = as_int(item.get("tmdb_id") or state_ids.get("tmdb"))
    if media_type in {"tv", "series"}:
        media_type = "show"
    if media_type in {"movie", "show"} and tmdb_id is not None:
        cur.execute(
            "SELECT media_item_id FROM media_items WHERE media_type = %s AND tmdb_id = %s",
            (media_type, tmdb_id),
        )
        row = cur.fetchone()
        return int(row["media_item_id"]) if row else None
    if media_type == "episode":
        show_id = as_int(item.get("show_id") or state_ids.get("tmdb"))
        season_number = as_int(item.get("season_number"))
        episode_number = as_int(item.get("episode_number"))
        if show_id is not None and season_number is not None and episode_number is not None:
            cur.execute(
                """
                SELECT e.media_item_id
                FROM episodes e
                JOIN shows s ON s.show_id = e.show_id
                WHERE s.tmdb_show_id = %s AND e.season_number = %s AND e.episode_number = %s
                """,
                (show_id, season_number, episode_number),
            )
            row = cur.fetchone()
            return int(row["media_item_id"]) if row else None
    if media_type == "season":
        show_id = as_int(item.get("show_id") or state_ids.get("tmdb"))
        season_number = as_int(item.get("season_number"))
        if show_id is not None and season_number is not None:
            cur.execute(
                """
                SELECT se.media_item_id
                FROM seasons se
                JOIN shows s ON s.show_id = se.show_id
                WHERE s.tmdb_show_id = %s AND se.season_number = %s
                """,
                (show_id, season_number),
            )
            row = cur.fetchone()
            return int(row["media_item_id"]) if row else None
    return None


def operation_for_state(state_type: str, value: str) -> tuple[str, str]:
    if state_type == "watched_status":
        return "trakt", "watch_state_set"
    if state_type == "watch_list":
        return "trakt", "watchlist_add" if value == "on" else "watchlist_remove"
    if state_type == "favourite":
        return "local", "favourite_set"
    return "local", "watch_state_set"


def import_state_sources(cur: Any, config: ServerModeConfig) -> dict[str, int]:
    counts = {"inputs_watchlist": 0, "watch_state": 0, "watchlist": 0, "favourites": 0, "sync_queue": 0, "unresolved": 0}
    inputs_payload = load_json(config.data_path("inputs.json"), {}) or {}
    watchlist = inputs_payload.get("watchlist") if isinstance(inputs_payload, dict) else []
    for entry in watchlist if isinstance(watchlist, list) else []:
        if not isinstance(entry, dict):
            continue
        media_item_id = resolve_media_item(cur, entry)
        if media_item_id is None:
            counts["unresolved"] += 1
            continue
        cur.execute(
            """
            INSERT INTO watchlist (media_item_id, is_active, list_source, pending_sync)
            VALUES (%s, true, 'json_import', false)
            ON CONFLICT (media_item_id) DO UPDATE SET is_active = true, list_source = 'json_import', pending_sync = false
            """,
            (media_item_id,),
        )
        counts["inputs_watchlist"] += 1

    queue_payload = load_json(config.data_path("watch_state_queue.json"), {}) or {}
    queue_items = queue_payload.get("items") if isinstance(queue_payload, dict) else []
    for entry in queue_items if isinstance(queue_items, list) else []:
        if not isinstance(entry, dict):
            continue
        media_item_id = resolve_media_item(cur, entry)
        state_type = as_text(entry.get("state_type")) or ""
        value = as_text(entry.get("new_value")) or ""
        provider, operation = operation_for_state(state_type, value)
        if media_item_id is None:
            counts["unresolved"] += 1
        elif state_type == "watched_status" and value in {"unwatched", "partial", "watched"}:
            cur.execute(
                """
                INSERT INTO watch_state (media_item_id, watched_status, state_source, pending_sync)
                VALUES (%s, %s, 'json_import', true)
                ON CONFLICT (media_item_id) DO UPDATE SET
                    watched_status = EXCLUDED.watched_status,
                    state_source = 'json_import',
                    pending_sync = true
                """,
                (media_item_id, value),
            )
            counts["watch_state"] += 1
        elif state_type == "watch_list":
            cur.execute(
                """
                INSERT INTO watchlist (media_item_id, is_active, list_source, pending_sync)
                VALUES (%s, %s, 'json_import', true)
                ON CONFLICT (media_item_id) DO UPDATE SET
                    is_active = EXCLUDED.is_active,
                    list_source = 'json_import',
                    pending_sync = true
                """,
                (media_item_id, value == "on"),
            )
            counts["watchlist"] += 1
        elif state_type == "favourite":
            cur.execute(
                """
                INSERT INTO favourites (media_item_id, is_active, favourite_source, pending_sync)
                VALUES (%s, %s, 'json_import', true)
                ON CONFLICT (media_item_id) DO UPDATE SET
                    is_active = EXCLUDED.is_active,
                    favourite_source = 'json_import',
                    pending_sync = true
                """,
                (media_item_id, value == "on"),
            )
            counts["favourites"] += 1
        cur.execute(
            """
            INSERT INTO sync_queue (media_item_id, provider_key, operation_type, operation_key, payload_json, status)
            VALUES (%s, %s, %s, %s, %s::jsonb, 'queued')
            """,
            (media_item_id, provider, operation, as_text(entry.get("id") or entry.get("item_key")), PostgresClient.json_param(entry)),
        )
        counts["sync_queue"] += 1
    return counts


def import_to_postgres(config: ServerModeConfig, dry_run: bool = True) -> dict[str, Any]:
    summary = migration_summary(config)
    if dry_run:
        return summary
    client = PostgresClient(config.postgres_dsn)
    if not client.ready:
        raise PostgresUnavailable(f"PostgreSQL unavailable: {client.status()}")

    payload = load_json(config.data_path("data.json"), {}) or {}
    shows = payload.get("shows") if isinstance(payload, dict) else []
    movies = payload.get("movies") if isinstance(payload, dict) else []
    counts = {"shows": 0, "seasons": 0, "episodes": 0, "movies": 0}

    with client.connection() as conn:
        with conn.cursor() as cur:
            for show in shows if isinstance(shows, list) else []:
                if not isinstance(show, dict):
                    continue
                show_tmdb_id = as_int(show.get("tmdb_id") or show.get("id"))
                show_title = media_title(show, "Show")
                show_media_item_id = upsert_media_item(
                    cur,
                    media_type="show",
                    title=show_title,
                    tmdb_id=show_tmdb_id,
                    row=show,
                    source_key=f"shows:{show_tmdb_id or show_title}",
                    release_date=as_date(show.get("first_air_date")),
                    runtime=runtime_minutes(show),
                    poster_path=image_path(show, "poster_local", "poster_path"),
                    backdrop_path=image_path(show, "backdrop_local", "backdrop_path"),
                )
                show_id = upsert_show(cur, show, show_media_item_id)
                counts["shows"] += 1
                seasons = show.get("seasons") if isinstance(show.get("seasons"), list) else []
                for season in seasons:
                    if not isinstance(season, dict):
                        continue
                    season_number = as_int(season.get("season_number")) or 0
                    season_tmdb_id = as_int(season.get("id") or season.get("_id"))
                    season_title = f"{show_title} - {media_title(season, f'Season {season_number}')}"
                    season_media_item_id = upsert_media_item(
                        cur,
                        media_type="season",
                        title=season_title,
                        tmdb_id=season_tmdb_id,
                        parent_media_item_id=show_media_item_id,
                        row=season,
                        source_key=f"shows:{show_tmdb_id}:seasons:{season_number}",
                        release_date=as_date(season.get("air_date")),
                        poster_path=image_path(season, "poster_local", "poster_path"),
                    )
                    season_id = upsert_season(cur, season, show_id, season_media_item_id)
                    counts["seasons"] += 1
                    episodes = season.get("episodes") if isinstance(season.get("episodes"), list) else []
                    for episode in episodes:
                        if not isinstance(episode, dict):
                            continue
                        episode_number = as_int(episode.get("episode_number")) or 0
                        episode_tmdb_id = as_int(episode.get("id"))
                        episode_title = f"{show_title} - S{season_number:02d}E{episode_number:02d} - {media_title(episode, 'Episode')}"
                        episode_media_item_id = upsert_media_item(
                            cur,
                            media_type="episode",
                            title=episode_title,
                            tmdb_id=episode_tmdb_id,
                            parent_media_item_id=season_media_item_id,
                            row=episode,
                            source_key=f"shows:{show_tmdb_id}:seasons:{season_number}:episodes:{episode_number}",
                            release_date=as_date(episode.get("air_date")),
                            runtime=runtime_minutes(episode),
                            still_path=image_path(episode, "still_local", "still_path"),
                        )
                        upsert_episode(cur, episode, show_id, season_id, episode_media_item_id)
                        counts["episodes"] += 1

            for movie in movies if isinstance(movies, list) else []:
                if not isinstance(movie, dict):
                    continue
                movie_tmdb_id = as_int(movie.get("tmdb_id") or movie.get("id"))
                movie_title = media_title(movie, "Movie")
                movie_media_item_id = upsert_media_item(
                    cur,
                    media_type="movie",
                    title=movie_title,
                    tmdb_id=movie_tmdb_id,
                    row=movie,
                    source_key=f"movies:{movie_tmdb_id or movie_title}",
                    release_date=as_date(movie.get("release_date")),
                    runtime=runtime_minutes(movie),
                    poster_path=image_path(movie, "poster_local", "poster_path"),
                    backdrop_path=image_path(movie, "backdrop_local", "backdrop_path"),
                )
                upsert_movie(cur, movie, movie_media_item_id)
                counts["movies"] += 1
            state_counts = import_state_sources(cur, config)

    summary["mode"] = "applied"
    summary["upserted"] = counts
    summary["state_imported"] = state_counts
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import current JSON artifacts into PostgreSQL.")
    parser.add_argument("--apply", action="store_true", help="Apply upserts; default is dry run.")
    args = parser.parse_args(argv)
    result = import_to_postgres(ServerModeConfig.from_env(), dry_run=not args.apply)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
