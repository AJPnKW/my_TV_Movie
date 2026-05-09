# FILE: tools/media_renamer/media_catalog_builder.py
# VERSION: v0.4.0
# CHANGE NOTES:
# - Builds a compact media cleanup reference from the existing my_TV_Movie catalog.
# - Uses data/catalog_index.json and data/catalog_detail/*.json as the only authority.
# - Designed for the two-step cleanup pipeline: plan, then apply.

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MEDIA_REFERENCE_SCHEMA = "media_cleanup.reference.v1"


def utc_now_text() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def safe_int(value: object, fallback: int = 0) -> int:
    try:
        text = safe_text(value)
        if not text:
            return fallback
        return int(text)
    except (TypeError, ValueError):
        return fallback


def year_from_date(value: object) -> str:
    text = safe_text(value)
    match = re.search(r"(19\d{2}|20\d{2})", text)
    return match.group(1) if match else ""


def normalize_title(value: object) -> str:
    text = unicodedata.normalize("NFKD", safe_text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_tokens(value: object) -> list[str]:
    normalized = normalize_title(value)
    if not normalized:
        return []
    return [part for part in normalized.split(" ") if part]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


@dataclass(frozen=True)
class EpisodeReference:
    season_number: int
    episode_number: int
    name: str
    tmdb_id: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "season_number": self.season_number,
            "episode_number": self.episode_number,
            "name": self.name,
            "tmdb_id": self.tmdb_id,
            "tokens": title_tokens(self.name),
        }


@dataclass(frozen=True)
class SeasonReference:
    season_number: int
    name: str
    episodes: list[EpisodeReference] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "season_number": self.season_number,
            "name": self.name,
            "tokens": title_tokens(self.name),
            "episodes": [episode.as_dict() for episode in sorted(self.episodes, key=lambda item: item.episode_number)],
        }


@dataclass(frozen=True)
class ShowReference:
    tmdb_id: int
    title: str
    year: str
    seasons: list[SeasonReference] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "year": self.year,
            "tokens": title_tokens(self.title),
            "aliases": sorted(set([normalize_title(self.title), normalize_title(f"{self.title} {self.year}")])),
            "seasons": [season.as_dict() for season in sorted(self.seasons, key=lambda item: item.season_number)],
        }


@dataclass(frozen=True)
class MovieReference:
    tmdb_id: int
    title: str
    year: str

    def as_dict(self) -> dict[str, Any]:
        display_title = f"{self.title} ({self.year})" if self.year else self.title
        return {
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "year": self.year,
            "tokens": title_tokens(self.title),
            "aliases": sorted(set([normalize_title(self.title), normalize_title(display_title)])),
        }


def _detail_path_from_index(repo_root: Path, item: dict[str, Any]) -> Path | None:
    raw_path = safe_text(item.get("detail_path"))
    if raw_path:
        candidate = repo_root / raw_path.lstrip("/\\")
        if candidate.exists():
            return candidate
    tmdb_id = safe_int(item.get("tmdb_id") or item.get("id"))
    if tmdb_id:
        candidate = repo_root / "data" / "catalog_detail" / f"{tmdb_id}.json"
        if candidate.exists():
            return candidate
    return None


def _build_show(repo_root: Path, index_item: dict[str, Any]) -> ShowReference:
    detail_path = _detail_path_from_index(repo_root, index_item)
    detail = load_json(detail_path) if detail_path else index_item
    tmdb_id = safe_int(detail.get("tmdb_id") or detail.get("id") or index_item.get("tmdb_id") or index_item.get("id"))
    title = safe_text(detail.get("title") or detail.get("name") or index_item.get("title") or index_item.get("name"))
    year = year_from_date(detail.get("first_air_date") or detail.get("release_date") or index_item.get("first_air_date") or index_item.get("release_date"))
    seasons: list[SeasonReference] = []
    for season_data in detail.get("seasons", []):
        if not isinstance(season_data, dict):
            continue
        season_number = safe_int(season_data.get("season_number"))
        if season_number < 0:
            continue
        season_name = safe_text(season_data.get("name")) or f"Season {season_number}"
        episodes: list[EpisodeReference] = []
        for episode_data in season_data.get("episodes", []):
            if not isinstance(episode_data, dict):
                continue
            episode_number = safe_int(episode_data.get("episode_number"))
            if episode_number <= 0:
                continue
            episodes.append(
                EpisodeReference(
                    season_number=season_number,
                    episode_number=episode_number,
                    name=safe_text(episode_data.get("name") or episode_data.get("title")) or f"Episode {episode_number}",
                    tmdb_id=safe_int(episode_data.get("tmdb_id") or episode_data.get("id")),
                )
            )
        seasons.append(SeasonReference(season_number=season_number, name=season_name, episodes=episodes))
    return ShowReference(tmdb_id=tmdb_id, title=title, year=year, seasons=seasons)


def _build_movie(repo_root: Path, index_item: dict[str, Any]) -> MovieReference:
    detail_path = _detail_path_from_index(repo_root, index_item)
    detail = load_json(detail_path) if detail_path else index_item
    tmdb_id = safe_int(detail.get("tmdb_id") or detail.get("id") or index_item.get("tmdb_id") or index_item.get("id"))
    title = safe_text(detail.get("title") or detail.get("name") or index_item.get("title") or index_item.get("name"))
    year = year_from_date(detail.get("release_date") or index_item.get("release_date") or detail.get("first_air_date") or index_item.get("first_air_date"))
    return MovieReference(tmdb_id=tmdb_id, title=title, year=year)


def build_media_reference(repo_root: Path, output_path: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    index_path = repo_root / "data" / "catalog_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Required catalog index not found: {index_path}")
    catalog_index = load_json(index_path)
    shows = []
    movies = []
    for item in catalog_index.get("shows", []):
        if isinstance(item, dict):
            show = _build_show(repo_root, item)
            if show.tmdb_id and show.title:
                shows.append(show.as_dict())
    for item in catalog_index.get("movies", []):
        if isinstance(item, dict):
            movie = _build_movie(repo_root, item)
            if movie.tmdb_id and movie.title:
                movies.append(movie.as_dict())
    reference = {
        "meta": {
            "schema": MEDIA_REFERENCE_SCHEMA,
            "generated_utc": utc_now_text(),
            "source": "data/catalog_index.json + data/catalog_detail/*.json",
            "show_count": len(shows),
            "movie_count": len(movies),
        },
        "shows": sorted(shows, key=lambda item: normalize_title(item.get("title"))),
        "movies": sorted(movies, key=lambda item: normalize_title(item.get("title"))),
    }
    destination = output_path or repo_root / "tools" / "media_renamer" / "media_reference.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")
    return reference


def load_or_build_media_reference(repo_root: Path, force: bool = False) -> dict[str, Any]:
    reference_path = repo_root / "tools" / "media_renamer" / "media_reference.json"
    if force or not reference_path.exists():
        return build_media_reference(repo_root, reference_path)
    data = load_json(reference_path)
    if data.get("meta", {}).get("schema") != MEDIA_REFERENCE_SCHEMA:
        return build_media_reference(repo_root, reference_path)
    return data


__all__ = [
    "MEDIA_REFERENCE_SCHEMA",
    "build_media_reference",
    "load_or_build_media_reference",
    "normalize_title",
    "safe_int",
    "safe_text",
    "title_tokens",
]
