"""Build the compact media reference used by the home media renamer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATALOG_INDEX = Path("data/catalog_index.json")
DETAIL_DIR = Path("data/catalog_detail")
REFERENCE_PATH = Path("tools/media_renamer/media_reference.json")


def safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def year_from(value: Any) -> str:
    match = re.search(r"(19\d{2}|20\d{2})", safe_text(value))
    return match.group(1) if match else ""


def normalize_key(value: str) -> str:
    text = safe_text(value).lower().replace("&", " and ")
    text = re.sub(r"\[[0-9]+\]", " ", text)
    text = re.sub(r"\([12][0-9]{3}\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(the|a|an)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_tokens(*values: Any) -> list[str]:
    tokens: set[str] = set()
    for value in values:
        key = normalize_key(safe_text(value))
        if key:
            tokens.add(key)
            tokens.update(part for part in key.split() if part)
    return sorted(tokens)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class BuildStats:
    shows: int
    movies: int
    episodes: int
    detail_files_read: int
    detail_files_missing: int

    def as_dict(self) -> dict[str, int]:
        return {
            "shows": self.shows,
            "movies": self.movies,
            "episodes": self.episodes,
            "detail_files_read": self.detail_files_read,
            "detail_files_missing": self.detail_files_missing,
        }


def season_label(name: str, number: int) -> str:
    key = normalize_key(name)
    if not key or key in {"season", f"season {number}", f"season {number:02d}"}:
        return ""
    return safe_text(name)


def detail_path_for(repo_root: Path, item: dict[str, Any], tmdb_id: int) -> Path:
    detail_text = safe_text(item.get("detail_path")).lstrip("/\\")
    if detail_text:
        return repo_root / detail_text
    return repo_root / DETAIL_DIR / f"{tmdb_id}.json"


def show_from(index_item: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    source = detail or index_item
    tmdb_id = safe_int(source.get("tmdb_id") or source.get("id") or index_item.get("tmdb_id") or index_item.get("id"))
    title = safe_text(source.get("title") or source.get("name") or index_item.get("title") or index_item.get("name"))
    first_air_year = year_from(source.get("first_air_date") or source.get("release_date") or index_item.get("first_air_date"))
    alternate_values = [
        title,
        source.get("name"),
        source.get("original_name"),
        index_item.get("title"),
        index_item.get("name"),
        index_item.get("original_name"),
    ]
    seasons: list[dict[str, Any]] = []
    for season in source.get("seasons", []) if isinstance(source.get("seasons"), list) else []:
        if not isinstance(season, dict):
            continue
        season_number = safe_int(season.get("season_number"))
        episodes: list[dict[str, Any]] = []
        for episode in season.get("episodes", []) if isinstance(season.get("episodes"), list) else []:
            if not isinstance(episode, dict):
                continue
            episode_number = safe_int(episode.get("episode_number"))
            episodes.append(
                {
                    "episode_number": episode_number,
                    "episode_name": safe_text(episode.get("name") or episode.get("title")) or f"Episode {episode_number:02d}",
                }
            )
        seasons.append(
            {
                "season_number": season_number,
                "season_name": season_label(safe_text(season.get("name")), season_number),
                "episodes": sorted(episodes, key=lambda item: item["episode_number"]),
            }
        )
    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "first_air_year": first_air_year,
        "alternate_normalized_title_tokens": title_tokens(*alternate_values),
        "seasons": sorted(seasons, key=lambda item: item["season_number"]),
    }


def movie_from(index_item: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    source = detail or index_item
    tmdb_id = safe_int(source.get("tmdb_id") or source.get("id") or index_item.get("tmdb_id") or index_item.get("id"))
    title = safe_text(source.get("title") or source.get("name") or index_item.get("title") or index_item.get("name"))
    release_year = year_from(source.get("release_date") or index_item.get("release_date") or source.get("year") or index_item.get("year"))
    alternate_values = [
        title,
        source.get("original_title"),
        source.get("name"),
        index_item.get("title"),
        index_item.get("original_title"),
        index_item.get("name"),
    ]
    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "release_year": release_year,
        "alternate_normalized_title_tokens": title_tokens(*alternate_values),
    }


def build_media_reference(repo_root: Path) -> tuple[Path, BuildStats]:
    repo_root = repo_root.resolve()
    index_path = repo_root / CATALOG_INDEX
    detail_dir = repo_root / DETAIL_DIR
    reference_path = repo_root / REFERENCE_PATH
    if not index_path.exists():
        raise FileNotFoundError(f"Catalog index not found: {index_path}")
    if not detail_dir.exists():
        raise FileNotFoundError(f"Catalog detail folder not found: {detail_dir}")

    index = read_json(index_path)
    shows_raw = index.get("shows") if isinstance(index, dict) else []
    movies_raw = index.get("movies") if isinstance(index, dict) else []
    shows: list[dict[str, Any]] = []
    movies: list[dict[str, Any]] = []
    detail_files_read = 0
    detail_files_missing = 0

    for item in shows_raw if isinstance(shows_raw, list) else []:
        if not isinstance(item, dict):
            continue
        tmdb_id = safe_int(item.get("tmdb_id") or item.get("id"))
        if not tmdb_id:
            continue
        detail: dict[str, Any] | None = None
        detail_path = detail_path_for(repo_root, item, tmdb_id)
        if detail_path.exists():
            payload = read_json(detail_path)
            detail = payload if isinstance(payload, dict) else None
            detail_files_read += 1
        else:
            detail_files_missing += 1
        shows.append(show_from(item, detail))

    for item in movies_raw if isinstance(movies_raw, list) else []:
        if not isinstance(item, dict):
            continue
        tmdb_id = safe_int(item.get("tmdb_id") or item.get("id"))
        if not tmdb_id:
            continue
        detail: dict[str, Any] | None = None
        detail_path = detail_path_for(repo_root, item, tmdb_id)
        if detail_path.exists():
            payload = read_json(detail_path)
            detail = payload if isinstance(payload, dict) else None
        movies.append(movie_from(item, detail))

    episode_count = sum(len(season["episodes"]) for show in shows for season in show["seasons"])
    payload = {
        "schema": "media_renamer.reference.v3",
        "version": "0.3.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "catalog_index": str(index_path),
            "catalog_detail": str(detail_dir),
        },
        "stats": {
            "shows": len(shows),
            "movies": len(movies),
            "episodes": episode_count,
            "detail_files_read": detail_files_read,
            "detail_files_missing": detail_files_missing,
        },
        "movies": sorted(movies, key=lambda item: normalize_key(item["title"])),
        "shows": sorted(shows, key=lambda item: normalize_key(item["title"])),
    }
    write_json(reference_path, payload)
    return reference_path, BuildStats(len(shows), len(movies), episode_count, detail_files_read, detail_files_missing)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build the compact media renamer reference.")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args()
    path, stats = build_media_reference(Path(args.repo_root))
    print(f"reference_path={path}")
    print(json.dumps(stats.as_dict(), indent=2))


if __name__ == "__main__":
    main()
