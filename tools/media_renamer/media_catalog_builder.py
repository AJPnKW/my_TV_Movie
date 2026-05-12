from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

def normalize_key(value: str) -> str:
    text = value.casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def clean_title(value: str) -> str:
    text = re.sub(r"[_]+", " ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text

@dataclass(slots=True)
class EpisodeRef:
    season_number: int
    episode_number: int
    name: str
    normalized_name: str

@dataclass(slots=True)
class SeasonRef:
    season_number: int
    name: str
    episodes: dict[int, EpisodeRef] = field(default_factory=dict)

@dataclass(slots=True)
class ShowRef:
    tmdb_id: int
    title: str
    year: str
    tokens: set[str] = field(default_factory=set)
    seasons: dict[int, SeasonRef] = field(default_factory=dict)

@dataclass(slots=True)
class MovieRef:
    tmdb_id: int
    title: str
    year: str
    tokens: set[str] = field(default_factory=set)

@dataclass(slots=True)
class MediaReference:
    shows: dict[int, ShowRef]
    movies: dict[int, MovieRef]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "shows": [
                {
                    "tmdb_id": show.tmdb_id,
                    "title": show.title,
                    "year": show.year,
                    "tokens": sorted(show.tokens),
                    "seasons": [
                        {
                            "season_number": season.season_number,
                            "name": season.name,
                            "episodes": [
                                {
                                    "season_number": ep.season_number,
                                    "episode_number": ep.episode_number,
                                    "name": ep.name,
                                    "normalized_name": ep.normalized_name,
                                }
                                for ep in sorted(season.episodes.values(), key=lambda item: item.episode_number)
                            ],
                        }
                        for season in sorted(show.seasons.values(), key=lambda item: item.season_number)
                    ],
                }
                for show in sorted(self.shows.values(), key=lambda item: item.title.casefold())
            ],
            "movies": [
                {
                    "tmdb_id": movie.tmdb_id,
                    "title": movie.title,
                    "year": movie.year,
                    "tokens": sorted(movie.tokens),
                }
                for movie in sorted(self.movies.values(), key=lambda item: item.title.casefold())
            ],
        }

def _year_from_item(item: dict[str, Any]) -> str:
    for key in ("release_date", "first_air_date"):
        value = str(item.get(key) or "")
        if len(value) >= 4 and value[:4].isdigit():
            return value[:4]
    value = str(item.get("year") or "")
    return value if value.isdigit() else ""

def _add_title_tokens(tokens: set[str], *values: str) -> None:
    for value in values:
        if not value:
            continue
        clean = clean_title(value)
        norm = normalize_key(clean)
        if norm:
            tokens.add(norm)
            tokens.add(normalize_key(re.sub(r"\bthe\b", "", clean, flags=re.IGNORECASE)))

def _load_detail(repo: Path, detail_path: str, tmdb_id: int) -> dict[str, Any]:
    candidates = []
    if detail_path:
        candidates.append(repo / detail_path.strip("/"))
    candidates.append(repo / "data" / "catalog_detail" / f"{tmdb_id}.json")
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {}

def build_reference(repo: Path) -> MediaReference:
    index_path = repo / "data" / "catalog_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Missing catalog index: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    shows: dict[int, ShowRef] = {}
    movies: dict[int, MovieRef] = {}

    for item in index.get("shows", []):
        tmdb_id = int(item.get("tmdb_id") or item.get("id") or 0)
        if tmdb_id <= 0:
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        detail = _load_detail(repo, str(item.get("detail_path") or ""), tmdb_id)
        show = ShowRef(tmdb_id=tmdb_id, title=clean_title(str(detail.get("title") or detail.get("name") or title)), year=_year_from_item(item))
        _add_title_tokens(show.tokens, title, str(item.get("name") or ""), str(item.get("original_name") or ""), show.title)
        for season_data in detail.get("seasons", []):
            season_number = int(season_data.get("season_number") or 0)
            season_name = clean_title(str(season_data.get("name") or f"Season {season_number:02d}"))
            season = SeasonRef(season_number=season_number, name=season_name)
            for ep_data in season_data.get("episodes", []):
                ep_number = int(ep_data.get("episode_number") or 0)
                if ep_number <= 0:
                    continue
                ep_name = clean_title(str(ep_data.get("name") or f"Episode {ep_number:02d}"))
                season.episodes[ep_number] = EpisodeRef(
                    season_number=season_number,
                    episode_number=ep_number,
                    name=ep_name,
                    normalized_name=normalize_key(ep_name),
                )
            show.seasons[season_number] = season
        shows[tmdb_id] = show

    for item in index.get("movies", []):
        tmdb_id = int(item.get("tmdb_id") or item.get("id") or 0)
        if tmdb_id <= 0:
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        movie = MovieRef(tmdb_id=tmdb_id, title=clean_title(title), year=_year_from_item(item))
        _add_title_tokens(movie.tokens, title, str(item.get("original_title") or ""), movie.title)
        movies[tmdb_id] = movie
    return MediaReference(shows=shows, movies=movies)

def save_reference(repo: Path, output_path: Path | None = None) -> Path:
    ref = build_reference(repo)
    target = output_path or repo / "tools" / "media_renamer" / "media_reference.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ref.to_jsonable(), indent=2, ensure_ascii=False), encoding="utf-8")
    return target

def load_reference(repo: Path) -> MediaReference:
    return build_reference(repo)
