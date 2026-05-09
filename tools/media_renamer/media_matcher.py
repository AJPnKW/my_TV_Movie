# FILE: tools/media_renamer/media_matcher.py
# VERSION: v0.4.0
# CHANGE NOTES:
# - Centralized messy filename parsing and catalog matching.
# - Supports SxxEyy, S2_E1, 5x04, S2026E01, malformed parentheses, and embedded TMDb patterns.
# - Outputs TV and Movies destinations only; never uses a Shows destination.

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path, PureWindowsPath
from typing import Any


WINDOWS_RESERVED_CHARS = '<>:"/\\|?*'


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


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", safe_text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_set(value: object) -> set[str]:
    return {part for part in normalize_text(value).split(" ") if part}


def sanitize_path_part(value: object) -> str:
    text = safe_text(value)
    for char in WINDOWS_RESERVED_CHARS:
        text = text.replace(char, " ")
    text = re.sub(r"\s+", " ", text).strip().strip(".")
    return text or "Unknown"


def _display_season_folder(season_number: int, season_name: str) -> str:
    base = f"Season {season_number:02d}" if season_number < 100 else f"Season {season_number}"
    clean_name = sanitize_path_part(season_name)
    generic_names = {
        "",
        normalize_text(base),
        normalize_text(f"Season {season_number}"),
        normalize_text(f"Season {season_number:02d}"),
    }
    if normalize_text(clean_name) in generic_names:
        return base
    return f"{base} - {clean_name}"


def _episode_code(season_number: int, episode_number: int) -> str:
    season_text = f"{season_number:02d}" if season_number < 100 else str(season_number)
    return f"S{season_text}E{episode_number:02d}"


@dataclass(frozen=True)
class ParsedName:
    source_path: Path
    stem: str
    extension: str
    normalized_name: str
    parent_names: list[str]
    tmdb_id: int = 0
    season_number: int = 0
    episode_number: int = 0
    episode_pattern: str = ""
    likely_movie_year: str = ""
    embedded_tv: bool = False
    has_episode_identity: bool = False


@dataclass(frozen=True)
class MatchResult:
    status: str
    media_type: str
    action: str
    confidence: int
    reason: str
    tmdb_id: int = 0
    title: str = ""
    season_number: int = 0
    episode_number: int = 0
    episode_name: str = ""
    season_name: str = ""
    destination_path: str = ""
    identity_key: str = ""


def parse_name(path: Path) -> ParsedName:
    stem = path.stem
    extension = path.suffix.lower()
    combined = " ".join([path.name, *[part.name for part in path.parents[:5]]])
    parent_names = [part.name for part in path.parents[:6]]
    tmdb_id = 0
    season_number = 0
    episode_number = 0
    episode_pattern = ""
    embedded_tv = False

    embedded = re.search(r"embed[_\-. ]*tv[_\-. ]*(\d+)[_\-. ]+(\d{1,4})[_\-. ]+(\d{1,3})", path.name, re.IGNORECASE)
    if embedded:
        tmdb_id = safe_int(embedded.group(1))
        season_number = safe_int(embedded.group(2))
        episode_number = safe_int(embedded.group(3))
        episode_pattern = "embedded_tv"
        embedded_tv = True

    bracket_ids = re.findall(r"\[(\d{2,})\]", combined)
    if bracket_ids and not tmdb_id:
        tmdb_id = safe_int(bracket_ids[-1])

    if not episode_number:
        for pattern_name, pattern in [
            ("sxxeyy", r"s\s*(\d{1,4})\s*e\s*(\d{1,3})"),
            ("sxx_eyy", r"s\s*(\d{1,4})\s*[_\-. ]+e\s*(\d{1,3})"),
            ("x", r"(?<!\d)(\d{1,4})\s*x\s*(\d{1,3})(?!\d)"),
            ("season_episode_words", r"season\s*(\d{1,4}).{0,12}episode\s*(\d{1,3})"),
        ]:
            found = re.search(pattern, combined, re.IGNORECASE)
            if found:
                season_number = safe_int(found.group(1))
                episode_number = safe_int(found.group(2))
                episode_pattern = pattern_name
                break

    year_match = re.search(r"\((19\d{2}|20\d{2})\)", combined)
    likely_movie_year = year_match.group(1) if year_match else ""

    return ParsedName(
        source_path=path,
        stem=stem,
        extension=extension,
        normalized_name=normalize_text(" ".join([path.stem, *parent_names[:4]])),
        parent_names=parent_names,
        tmdb_id=tmdb_id,
        season_number=season_number,
        episode_number=episode_number,
        episode_pattern=episode_pattern,
        likely_movie_year=likely_movie_year,
        embedded_tv=embedded_tv,
        has_episode_identity=season_number > 0 and episode_number > 0,
    )


def _score_tokens(query_tokens: set[str], title_tokens: set[str]) -> int:
    if not query_tokens or not title_tokens:
        return 0
    overlap = len(query_tokens & title_tokens)
    title_ratio = overlap / max(len(title_tokens), 1)
    query_ratio = overlap / max(len(query_tokens), 1)
    return int(round((title_ratio * 70) + (query_ratio * 30)))


def _sequence_score(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(round(SequenceMatcher(None, a, b).ratio() * 100))


def _find_show_by_id(reference: dict[str, Any], tmdb_id: int) -> dict[str, Any] | None:
    if not tmdb_id:
        return None
    for show in reference.get("shows", []):
        if safe_int(show.get("tmdb_id")) == tmdb_id:
            return show
    return None


def _find_movie_by_id(reference: dict[str, Any], tmdb_id: int) -> dict[str, Any] | None:
    if not tmdb_id:
        return None
    for movie in reference.get("movies", []):
        if safe_int(movie.get("tmdb_id")) == tmdb_id:
            return movie
    return None


def _best_show(reference: dict[str, Any], parsed: ParsedName) -> tuple[dict[str, Any] | None, int, str]:
    by_id = _find_show_by_id(reference, parsed.tmdb_id)
    if by_id:
        return by_id, 100, "tmdb id in file or folder"
    query_tokens = token_set(parsed.normalized_name)
    best: dict[str, Any] | None = None
    best_score = 0
    best_reason = ""
    for show in reference.get("shows", []):
        title = safe_text(show.get("title"))
        title_tokens = set(show.get("tokens", [])) or token_set(title)
        token_score = _score_tokens(query_tokens, title_tokens)
        sequence_score = _sequence_score(normalize_text(title), parsed.normalized_name)
        folder_boost = 0
        for parent in parsed.parent_names[:4]:
            parent_norm = normalize_text(parent)
            if normalize_text(title) and normalize_text(title) in parent_norm:
                folder_boost = max(folder_boost, 12)
            elif _score_tokens(token_set(parent), title_tokens) >= 85:
                folder_boost = max(folder_boost, 10)
        score = min(99, max(token_score, sequence_score) + folder_boost)
        if score > best_score:
            best = show
            best_score = score
            best_reason = "title and folder match"
    return best, best_score, best_reason


def _best_movie(reference: dict[str, Any], parsed: ParsedName) -> tuple[dict[str, Any] | None, int, str]:
    by_id = _find_movie_by_id(reference, parsed.tmdb_id)
    if by_id:
        return by_id, 100, "tmdb id in file or folder"
    query_tokens = token_set(parsed.stem)
    parent_context = " ".join(parsed.parent_names[:3])
    if normalize_text(parent_context) in {"movies", "movie"}:
        query_tokens |= token_set(parent_context)
    best: dict[str, Any] | None = None
    best_score = 0
    best_reason = ""
    for movie in reference.get("movies", []):
        title = safe_text(movie.get("title"))
        title_tokens = set(movie.get("tokens", [])) or token_set(title)
        token_score = _score_tokens(query_tokens, title_tokens)
        sequence_score = _sequence_score(normalize_text(title), normalize_text(parsed.stem))
        year_boost = 8 if parsed.likely_movie_year and parsed.likely_movie_year == safe_text(movie.get("year")) else 0
        score = min(99, max(token_score, sequence_score) + year_boost)
        if score > best_score:
            best = movie
            best_score = score
            best_reason = "movie title match"
    return best, best_score, best_reason


def _find_season(show: dict[str, Any], season_number: int) -> dict[str, Any] | None:
    for season in show.get("seasons", []):
        if safe_int(season.get("season_number")) == season_number:
            return season
    return None


def _find_episode(season: dict[str, Any] | None, episode_number: int) -> dict[str, Any] | None:
    if not season:
        return None
    for episode in season.get("episodes", []):
        if safe_int(episode.get("episode_number")) == episode_number:
            return episode
    return None


def destination_for_tv(media_root: Path, show: dict[str, Any], season: dict[str, Any] | None, episode: dict[str, Any] | None, season_number: int, episode_number: int, extension: str) -> Path:
    title = sanitize_path_part(show.get("title"))
    tmdb_id = safe_int(show.get("tmdb_id"))
    season_name = safe_text(season.get("name")) if season else ""
    episode_name = safe_text(episode.get("name")) if episode else f"Episode {episode_number}"
    show_folder = f"{title} [{tmdb_id}]"
    season_folder = _display_season_folder(season_number, season_name)
    filename = f"{title} - {_episode_code(season_number, episode_number)} - {sanitize_path_part(episode_name)}{extension}"
    return media_root / "TV" / show_folder / season_folder / filename


def destination_for_movie(media_root: Path, movie: dict[str, Any], extension: str) -> Path:
    title = sanitize_path_part(movie.get("title"))
    year = safe_text(movie.get("year"))
    tmdb_id = safe_int(movie.get("tmdb_id"))
    display = f"{title} ({year})" if year else title
    folder = f"{display} [{tmdb_id}]"
    return media_root / "Movies" / folder / f"{display}{extension}"


def match_media(path: Path, media_root: Path, reference: dict[str, Any], min_confidence: int) -> MatchResult:
    parsed = parse_name(path)
    extension = parsed.extension or ".mp4"
    if parsed.has_episode_identity:
        show, score, reason = _best_show(reference, parsed)
        if not show:
            return MatchResult(status="problem", media_type="tv", action="review", confidence=0, reason="no show match")
        season = _find_season(show, parsed.season_number)
        episode = _find_episode(season, parsed.episode_number)
        if not episode:
            # Still match known show+S/E when the catalog has incomplete season detail, but keep below safe threshold.
            confidence = min(score, 80)
            dest = destination_for_tv(media_root, show, season, None, parsed.season_number, parsed.episode_number, extension)
            return MatchResult(
                status="problem",
                media_type="tv",
                action="review",
                confidence=confidence,
                reason=f"{reason}; episode not found in catalog reference",
                tmdb_id=safe_int(show.get("tmdb_id")),
                title=safe_text(show.get("title")),
                season_number=parsed.season_number,
                episode_number=parsed.episode_number,
                episode_name=f"Episode {parsed.episode_number}",
                season_name=safe_text(season.get("name")) if season else "",
                destination_path=str(dest),
                identity_key=f"tv:{safe_int(show.get('tmdb_id'))}:s{parsed.season_number}:e{parsed.episode_number}",
            )
        confidence = 100 if parsed.tmdb_id and safe_int(show.get("tmdb_id")) == parsed.tmdb_id else max(score, 85 if score >= 80 else score)
        dest = destination_for_tv(media_root, show, season, episode, parsed.season_number, parsed.episode_number, extension)
        action = "already_ok" if path.resolve() == dest.resolve() else "move_tv"
        status = "safe" if confidence >= min_confidence else "problem"
        return MatchResult(
            status=status,
            media_type="tv",
            action=action if status == "safe" else "review",
            confidence=confidence,
            reason=reason or "episode pattern match",
            tmdb_id=safe_int(show.get("tmdb_id")),
            title=safe_text(show.get("title")),
            season_number=parsed.season_number,
            episode_number=parsed.episode_number,
            episode_name=safe_text(episode.get("name")),
            season_name=safe_text(season.get("name")) if season else "",
            destination_path=str(dest),
            identity_key=f"tv:{safe_int(show.get('tmdb_id'))}:s{parsed.season_number}:e{parsed.episode_number}",
        )

    movie, score, reason = _best_movie(reference, parsed)
    if not movie:
        return MatchResult(status="problem", media_type="unknown", action="review", confidence=0, reason="no movie or episode match")
    dest = destination_for_movie(media_root, movie, extension)
    action = "already_ok" if path.resolve() == dest.resolve() else "move_movie"
    status = "safe" if score >= min_confidence else "problem"
    return MatchResult(
        status=status,
        media_type="movie",
        action=action if status == "safe" else "review",
        confidence=score,
        reason=reason,
        tmdb_id=safe_int(movie.get("tmdb_id")),
        title=safe_text(movie.get("title")),
        destination_path=str(dest),
        identity_key=f"movie:{safe_int(movie.get('tmdb_id'))}",
    )


def representative_parse_results() -> list[dict[str, Any]]:
    samples = [
        "Abbott_Elementary_Safety_Day_S05E15.mp4",
        "CIA_(2026)_(2026)_S01E010.mp4",
        "Hacks__5x04.mp4",
        "Come_Dine_with_Me_(S2026E01).mp4",
        "The_Devil_Wears_Prada_2.mp4",
        "vsembed.ru_embed_tv_126027_5_16.mp4",
        "The_Hunting_Party_(S02E10.mp4",
        "Watson_(S02E20).a.mp4",
    ]
    rows = []
    for sample in samples:
        parsed = parse_name(PureWindowsPath(sample))  # type: ignore[arg-type]
        rows.append(
            {
                "sample": sample,
                "season_number": parsed.season_number,
                "episode_number": parsed.episode_number,
                "tmdb_id": parsed.tmdb_id,
                "episode_pattern": parsed.episode_pattern,
                "likely_movie_year": parsed.likely_movie_year,
            }
        )
    return rows


__all__ = [
    "MatchResult",
    "ParsedName",
    "match_media",
    "normalize_text",
    "parse_name",
    "representative_parse_results",
    "safe_int",
    "safe_text",
    "sanitize_path_part",
]
