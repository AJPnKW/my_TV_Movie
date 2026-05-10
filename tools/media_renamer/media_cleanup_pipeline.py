# FILE: tools/media_renamer/media_cleanup_pipeline.py
# VERSION: v0.4.4
# UPDATED: 2026-05-09
# CHANGE NOTES:
# - Replaces over-complex UI-dependent flow with a deterministic two-step pipeline.
# - Fixes root quarantine/duplicate destination handling.
# - Forces final media folders to TV and Movies only; never Shows.
# - Adds aggressive safe cleanup for root/ShowB/_Unsorted files when title + season + episode are clear.
# - Uses catalog data as authority and falls back to Episode NN only after show/season/episode identity is proven.
# - Treats destination-exists conflicts during apply as duplicate moves instead of errors.
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

VERSION = "0.4.4"
DEFAULT_MEDIA_ROOT = Path(r"C:\X1_Share\Recordings")
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv"}
SIDECAR_EXTENSIONS = {".srt", ".ass", ".vtt", ".nfo"}
SKIP_DIR_NAMES = {
    ".git", "__pycache__", "reports", "assets", "archived", "_metadata",
    "_mediarenamer_quarantine", "_mediarenamer_duplicates",
}
DO_NOT_SKIP_DIR_NAMES = {"showa", "showb", "_unsorted", "tv", "movies", "movie", "shows"}
JUNK_TRAILING_RE = re.compile(r"(?i)(?:[._\- ]+(?:copy|tmp|final|720|1080|f|a|b|alt\d*|\d+))+$")
EPISODE_PATTERNS = [
    re.compile(r"(?i)s(?P<s>\d{1,4})\s*e(?P<e>\d{1,3})"),
    re.compile(r"(?i)s(?P<s>\d{1,4})\s*[_ .-]\s*e(?P<e>\d{1,3})"),
    re.compile(r"(?i)(?P<s>\d{1,2})\s*x\s*(?P<e>\d{1,3})"),
]
EMBED_RE = re.compile(r"(?i)embed[_\-. ]tv[_\-. ](?P<id>\d+)[_\-. ](?P<s>\d+)[_\-. ](?P<e>\d+)")
TMDB_ID_RE = re.compile(r"\[(?P<id>\d{2,})\]")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_text(value: str) -> str:
    text = value.lower().replace("&", " and ")
    text = re.sub(r"[_+.]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_name(value: str) -> str:
    text = str(value or "").strip()
    replacements = {
        ":": " -", "?": "", "*": "", "\"": "", "<": "", ">": "", "|": "-", "/": "-", "\\": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "Unknown"


def media_root_from_arg(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else DEFAULT_MEDIA_ROOT


@dataclass
class ReferenceMovie:
    tmdb_id: int
    title: str
    year: str
    tokens: str


@dataclass
class ReferenceEpisode:
    season_number: int
    episode_number: int
    name: str


@dataclass
class ReferenceSeason:
    season_number: int
    name: str
    episodes: dict[str, ReferenceEpisode]


@dataclass
class ReferenceShow:
    tmdb_id: int
    title: str
    year: str
    tokens: str
    seasons: dict[str, ReferenceSeason]


@dataclass
class PlanRow:
    action: str
    status: str
    source: str
    original_filename: str
    destination: str
    media_type: str
    matched_title: str
    tmdb_id: int | None
    season_number: int | None
    episode_number: int | None
    confidence: int
    reason: str
    size: int
    extension: str


@dataclass
class ExecutionRow:
    timestamp: str
    action: str
    source: str
    destination: str
    result: str
    error: str


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def build_reference(repo_root: Path) -> tuple[dict[int, ReferenceShow], dict[int, ReferenceMovie]]:
    catalog_index = repo_root / "data" / "catalog_index.json"
    detail_dir = repo_root / "data" / "catalog_detail"
    if not catalog_index.exists():
        raise FileNotFoundError(f"Missing catalog index: {catalog_index}")
    index = load_json(catalog_index)
    shows: dict[int, ReferenceShow] = {}
    movies: dict[int, ReferenceMovie] = {}

    for raw in index.get("shows", []):
        tmdb_id = int(raw.get("tmdb_id") or raw.get("id") or 0)
        if not tmdb_id:
            continue
        title = str(raw.get("title") or raw.get("name") or "").strip()
        year = str(raw.get("year") or str(raw.get("first_air_date") or "")[:4] or "").strip()
        seasons: dict[str, ReferenceSeason] = {}
        detail_path = detail_dir / f"{tmdb_id}.json"
        if detail_path.exists():
            detail = load_json(detail_path)
            for season in detail.get("seasons", []) or []:
                try:
                    sn = int(season.get("season_number") or 0)
                except (TypeError, ValueError):
                    continue
                season_name = str(season.get("name") or f"Season {sn:02d}").strip()
                episodes: dict[str, ReferenceEpisode] = {}
                for ep in season.get("episodes", []) or []:
                    try:
                        en = int(ep.get("episode_number") or 0)
                    except (TypeError, ValueError):
                        continue
                    ep_name = str(ep.get("name") or f"Episode {en:02d}").strip()
                    episodes[str(en)] = ReferenceEpisode(sn, en, ep_name)
                seasons[str(sn)] = ReferenceSeason(sn, season_name, episodes)
        for item in raw.get("season_episode_counts", []) or []:
            try:
                sn = int(item.get("season_number") or 0)
            except (TypeError, ValueError):
                continue
            seasons.setdefault(str(sn), ReferenceSeason(sn, f"Season {sn:02d}", {}))
        shows[tmdb_id] = ReferenceShow(tmdb_id, title, year, normalize_text(f"{title} {year}"), seasons)

    for raw in index.get("movies", []):
        tmdb_id = int(raw.get("tmdb_id") or raw.get("id") or 0)
        if not tmdb_id:
            continue
        title = str(raw.get("title") or raw.get("name") or "").strip()
        year = str(raw.get("year") or str(raw.get("release_date") or "")[:4] or "").strip()
        movies[tmdb_id] = ReferenceMovie(tmdb_id, title, year, normalize_text(f"{title} {year}"))

    reference_payload = {
        "meta": {"generated_at": datetime.now().isoformat(timespec="seconds"), "version": VERSION},
        "shows": [
            {
                "tmdb_id": s.tmdb_id,
                "title": s.title,
                "year": s.year,
                "seasons": [
                    {
                        "season_number": season.season_number,
                        "name": season.name,
                        "episodes": [asdict(ep) for ep in season.episodes.values()],
                    }
                    for season in s.seasons.values()
                ],
            }
            for s in shows.values()
        ],
        "movies": [asdict(m) for m in movies.values()],
    }
    write_json(repo_root / "tools" / "media_renamer" / "media_reference.json", reference_payload)
    return shows, movies


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def actual_child_dir(parent: Path, expected_name: str) -> Path | None:
    if not parent.exists():
        return None
    expected = expected_name.lower()
    for child in parent.iterdir():
        if child.is_dir() and child.name.lower() == expected:
            return child
    return None


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def should_skip_dir(path: Path, media_root: Path) -> bool:
    name = path.name.lower()
    if name in DO_NOT_SKIP_DIR_NAMES:
        return False
    if name.startswith(".venv"):
        return True
    if name in SKIP_DIR_NAMES:
        return True
    if name == "shows":
        return False
    return False


def iter_candidate_files(media_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in media_root.rglob("*"):
        if path.is_dir():
            continue
        parts = [p.lower() for p in path.relative_to(media_root).parts[:-1]]
        if any(part in SKIP_DIR_NAMES or part.startswith(".venv") for part in parts):
            # Do not rescan previous quarantine/duplicate/support content.
            continue
        ext = path.suffix.lower()
        if ext in MEDIA_EXTENSIONS or ext in SIDECAR_EXTENSIONS:
            candidates.append(path)
        elif ext == "" and path.stat().st_size > 20_000_000:
            candidates.append(path)
    return sorted(candidates, key=lambda p: str(p).lower())


def parse_episode_identity(path: Path) -> tuple[int | None, int | None, int | None]:
    text = f"{path.parent} {path.stem}"
    embed = EMBED_RE.search(text)
    if embed:
        return int(embed.group("id")), int(embed.group("s")), int(embed.group("e"))
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(text)
        if match:
            season = int(match.group("s"))
            episode = int(match.group("e"))
            return None, season, episode
    return None, None, None


def existing_tmdb_id(path: Path) -> int | None:
    for part in reversed(path.parts):
        match = TMDB_ID_RE.search(part)
        if match:
            try:
                return int(match.group("id"))
            except ValueError:
                return None
    return None


def cleaned_title_source(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"(?i)embed[_\-. ]tv[_\-. ]\d+[_\-. ]\d+[_\-. ]\d+", " ", stem)
    stem = re.sub(r"(?i)s\d{1,4}\s*[_ .-]?\s*e\d{1,3}.*$", " ", stem)
    stem = re.sub(r"(?i)\d{1,2}\s*x\s*\d{1,3}.*$", " ", stem)
    stem = re.sub(r"\[[0-9]+\]", " ", stem)
    stem = re.sub(r"\((?:19|20)\d{2}\)", " ", stem)
    stem = JUNK_TRAILING_RE.sub("", stem)
    return normalize_text(stem)


def context_text(path: Path, media_root: Path) -> str:
    rel_parts = list(path.relative_to(media_root).parts)
    useful = []
    for part in rel_parts[:-1]:
        low = part.lower()
        if low in {"tv", "movies", "movie", "shows", "_unsorted", "season 01", "season_01"}:
            continue
        if low.startswith("season"):
            continue
        useful.append(part)
    useful.append(path.stem)
    return normalize_text(" ".join(useful))


def score_match(needle: str, haystack: str) -> int:
    if not needle or not haystack:
        return 0
    if needle in haystack or haystack in needle:
        return 96
    needle_tokens = set(needle.split())
    hay_tokens = set(haystack.split())
    if not needle_tokens or not hay_tokens:
        return 0
    overlap = len(needle_tokens & hay_tokens) / max(1, len(needle_tokens))
    seq = SequenceMatcher(None, needle, haystack).ratio()
    return int(max(overlap, seq) * 100)


def find_show(path: Path, media_root: Path, shows: dict[int, ReferenceShow]) -> tuple[ReferenceShow | None, int, str]:
    direct_id = existing_tmdb_id(path)
    embed_id, _season, _episode = parse_episode_identity(path)
    if embed_id and embed_id in shows:
        return shows[embed_id], 100, "embedded tmdb id"
    if direct_id and direct_id in shows:
        return shows[direct_id], 100, "folder/file tmdb id"
    text = context_text(path, media_root)
    file_title = cleaned_title_source(path)
    best: tuple[ReferenceShow | None, int, str] = (None, 0, "no show match")
    for show in shows.values():
        show_tokens = normalize_text(show.title)
        score = max(score_match(show_tokens, text), score_match(show_tokens, file_title))
        if show.year and show.year in path.name:
            score = min(100, score + 5)
        if score > best[1]:
            best = (show, score, "title/folder token match")
    return best


def find_movie(path: Path, media_root: Path, movies: dict[int, ReferenceMovie]) -> tuple[ReferenceMovie | None, int, str]:
    direct_id = existing_tmdb_id(path)
    if direct_id and direct_id in movies:
        return movies[direct_id], 100, "folder/file tmdb id"
    text = context_text(path, media_root)
    best: tuple[ReferenceMovie | None, int, str] = (None, 0, "no movie match")
    for movie in movies.values():
        movie_tokens = normalize_text(movie.title)
        score = max(score_match(movie_tokens, text), score_match(movie.tokens, text))
        if movie.year and movie.year in path.name:
            score = min(100, score + 5)
        if score > best[1]:
            best = (movie, score, "movie title token match")
    return best


def season_folder_name(show: ReferenceShow, season_number: int) -> str:
    season = show.seasons.get(str(season_number))
    base = f"Season {season_number:02d}" if season_number < 100 else f"Season {season_number}"
    if not season or not season.name:
        return base
    name = safe_name(season.name)
    if normalize_text(name) in {normalize_text(base), f"season {season_number}", f"series {season_number}"}:
        return base
    return f"{base} - {name}"


def episode_name(show: ReferenceShow, season_number: int, episode_number: int) -> str:
    season = show.seasons.get(str(season_number))
    if season:
        ep = season.episodes.get(str(episode_number))
        if ep and ep.name:
            return safe_name(ep.name)
    return f"Episode {episode_number:02d}"


def build_tv_destination(media_root: Path, show: ReferenceShow, season_number: int, episode_number: int, ext: str) -> Path:
    show_folder = safe_name(f"{show.title} [{show.tmdb_id}]")
    season_folder = season_folder_name(show, season_number)
    ep_title = episode_name(show, season_number, episode_number)
    filename = safe_name(f"{show.title} - S{season_number:02d}E{episode_number:02d} - {ep_title}{ext.lower()}")
    return media_root / "TV" / show_folder / season_folder / filename


def build_sidecar_destination(media_root: Path, show: ReferenceShow, season_number: int, episode_number: int, ext: str) -> Path:
    show_folder = safe_name(f"{show.title} [{show.tmdb_id}]")
    season_folder = season_folder_name(show, season_number)
    ep_title = episode_name(show, season_number, episode_number)
    filename = safe_name(f"{show.title} - S{season_number:02d}E{episode_number:02d} - {ep_title}{ext.lower()}")
    return media_root / "TV" / show_folder / season_folder / filename


def build_movie_destination(media_root: Path, movie: ReferenceMovie, ext: str) -> Path:
    year_part = f" ({movie.year})" if movie.year else ""
    folder = safe_name(f"{movie.title}{year_part} [{movie.tmdb_id}]")
    filename = safe_name(f"{movie.title}{year_part}{ext.lower() if ext else '.mp4'}")
    return media_root / "Movies" / folder / filename


def is_already_ok(path: Path, destination: Path) -> bool:
    try:
        return path.resolve() == destination.resolve()
    except FileNotFoundError:
        return False


def file_identity(row: PlanRow) -> str:
    if row.media_type == "tv":
        return f"tv:{row.tmdb_id}:{row.season_number}:{row.episode_number}"
    if row.media_type == "movie":
        return f"movie:{row.tmdb_id}"
    return f"other:{row.source}"


def generate_plan(repo_root: Path, media_root: Path) -> tuple[Path, list[PlanRow], dict[str, int]]:
    shows, movies = build_reference(repo_root)
    stamp = now_stamp()
    report_dir = repo_root / "reports" / "media_renamer" / stamp
    report_dir.mkdir(parents=True, exist_ok=True)
    rows: list[PlanRow] = []

    # Ensure Movies casing repair is planned using actual directory enumeration.
    actual_movies = actual_child_dir(media_root, "Movies")
    if actual_movies is not None and actual_movies.name != "Movies":
        rows.append(PlanRow("repair_movies_folder_case", "ready", str(actual_movies), actual_movies.name, str(media_root / "Movies"), "folder", "Movies", None, None, None, 100, "normalize movies folder casing to Movies", 0, ""))

    for path in iter_candidate_files(media_root):
        try:
            size = path.stat().st_size
        except OSError as exc:
            rows.append(PlanRow("review", "problem", str(path), path.name, "", "unknown", "", None, None, None, 0, f"cannot stat file: {exc}", 0, path.suffix.lower()))
            continue
        ext = path.suffix.lower()
        if size == 0 and ext in MEDIA_EXTENSIONS:
            destination = media_root / "_MediaRenamer_Quarantine" / stamp / path.relative_to(media_root)
            rows.append(PlanRow("quarantine", "ready", str(path), path.name, str(destination), "broken", "", None, None, None, 100, "zero-byte media file", size, ext))
            continue
        if ext in SIDECAR_EXTENSIONS:
            _id, season_number, episode_number = parse_episode_identity(path)
            if season_number is not None and episode_number is not None:
                show, confidence, reason = find_show(path, media_root, shows)
                if show and confidence >= 85:
                    destination = build_sidecar_destination(media_root, show, season_number, episode_number, ext)
                    status = "already_ok" if is_already_ok(path, destination) else "ready"
                    rows.append(PlanRow("already_ok" if status == "already_ok" else "move_sidecar", status, str(path), path.name, str(destination), "tv_sidecar", show.title, show.tmdb_id, season_number, episode_number, confidence, reason, size, ext))
                    continue
            rows.append(PlanRow("review", "problem", str(path), path.name, "", "sidecar", "", None, None, None, 0, "sidecar not clearly linked to a catalog episode", size, ext))
            continue

        embedded_id, season_number, episode_number = parse_episode_identity(path)
        if season_number is not None and episode_number is not None:
            show, confidence, reason = find_show(path, media_root, shows)
            if embedded_id and embedded_id in shows:
                show = shows[embedded_id]
                confidence = 100
                reason = "embedded tmdb id"
            if show and confidence >= 85:
                destination = build_tv_destination(media_root, show, season_number, episode_number, ext if ext else ".mp4")
                action = "already_ok" if is_already_ok(path, destination) else "move_to_tv"
                status = "already_ok" if action == "already_ok" else "ready"
                rows.append(PlanRow(action, status, str(path), path.name, str(destination), "tv", show.title, show.tmdb_id, season_number, episode_number, confidence, reason, size, ext))
            else:
                rows.append(PlanRow("review", "problem", str(path), path.name, "", "tv", show.title if show else "", show.tmdb_id if show else None, season_number, episode_number, confidence, "episode pattern found but show confidence below 85", size, ext))
            continue

        # Treat files under Movies/movies or obvious large extensionless files as movie candidates.
        rel_parts = [p.lower() for p in path.relative_to(media_root).parts]
        movie_context = "movies" in rel_parts or "movie" in rel_parts or path.parent.name.lower() in {"movies", "movie"}
        if movie_context or ext == "":
            movie, confidence, reason = find_movie(path, media_root, movies)
            if movie and confidence >= 85:
                destination = build_movie_destination(media_root, movie, ext if ext else ".mp4")
                action = "already_ok" if is_already_ok(path, destination) else "move_to_movies"
                status = "already_ok" if action == "already_ok" else "ready"
                rows.append(PlanRow(action, status, str(path), path.name, str(destination), "movie", movie.title, movie.tmdb_id, None, None, confidence, reason, size, ext))
            else:
                rows.append(PlanRow("review", "problem", str(path), path.name, "", "movie", movie.title if movie else "", movie.tmdb_id if movie else None, None, None, confidence, "movie confidence below 85", size, ext))
            continue

        rows.append(PlanRow("review", "problem", str(path), path.name, "", "unknown", "", None, None, None, 0, "no safe TV/movie identity found", size, ext))

    rows = resolve_duplicates(rows, media_root, stamp)
    rows.extend(plan_empty_folder_cleanup(media_root))
    summary = summarize(rows)
    write_reports(report_dir, rows, summary, plan_only=True)
    return report_dir, rows, summary


def resolve_duplicates(rows: list[PlanRow], media_root: Path, stamp: str) -> list[PlanRow]:
    result: list[PlanRow] = []
    ready_by_dest: dict[str, list[PlanRow]] = {}
    for row in rows:
        if row.status == "ready" and row.destination and row.action in {"move_to_tv", "move_to_movies", "move_sidecar"}:
            ready_by_dest.setdefault(str(Path(row.destination).resolve()).lower(), []).append(row)
        else:
            result.append(row)
    for _dest, group in ready_by_dest.items():
        if len(group) == 1:
            row = group[0]
            dest = Path(row.destination)
            if dest.exists() and not Path(row.source).resolve() == dest.resolve():
                existing_size = dest.stat().st_size if dest.is_file() else 0
                if row.size > existing_size:
                    duplicate_dest = media_root / "_MediaRenamer_Duplicates" / stamp / dest.relative_to(media_root)
                    result.append(PlanRow("move_existing_duplicate", "ready", str(dest), dest.name, str(duplicate_dest), row.media_type, row.matched_title, row.tmdb_id, row.season_number, row.episode_number, row.confidence, "incoming file is larger than existing destination", existing_size, dest.suffix.lower()))
                    result.append(row)
                else:
                    duplicate_dest = media_root / "_MediaRenamer_Duplicates" / stamp / Path(row.source).relative_to(media_root)
                    result.append(PlanRow("move_duplicate", "ready", row.source, row.original_filename, str(duplicate_dest), row.media_type, row.matched_title, row.tmdb_id, row.season_number, row.episode_number, row.confidence, "destination already exists and existing file is same/larger", row.size, row.extension))
            else:
                result.append(row)
            continue
        winner = sorted(group, key=lambda r: (r.size, r.confidence), reverse=True)[0]
        result.append(winner)
        for loser in group:
            if loser is winner:
                continue
            duplicate_dest = media_root / "_MediaRenamer_Duplicates" / stamp / Path(loser.source).relative_to(media_root)
            result.append(PlanRow("move_duplicate", "ready", loser.source, loser.original_filename, str(duplicate_dest), loser.media_type, loser.matched_title, loser.tmdb_id, loser.season_number, loser.episode_number, loser.confidence, f"duplicate loser; kept {Path(winner.source).name}", loser.size, loser.extension))
    return result


def plan_empty_folder_cleanup(media_root: Path) -> list[PlanRow]:
    rows: list[PlanRow] = []
    for name in ["ShowA", "ShowB", "Shows"]:
        folder = media_root / "TV" / name if name.lower().startswith("show") and name != "Shows" else media_root / name
        if folder.exists() and folder.is_dir():
            rows.append(PlanRow("remove_empty_folder", "ready", str(folder), folder.name, "", "folder", folder.name, None, None, None, 100, "remove only if empty after safe moves", 0, ""))
    return rows


def summarize(rows: list[PlanRow]) -> dict[str, int]:
    summary = {
        "ready_to_fix": 0,
        "already_ok": 0,
        "move_to_tv": 0,
        "move_to_movies": 0,
        "duplicates_to_move": 0,
        "broken_to_quarantine": 0,
        "problem_files_left_alone": 0,
        "skipped_support_files": 0,
        "remove_empty_folders": 0,
    }
    for row in rows:
        if row.status == "ready":
            summary["ready_to_fix"] += 1
        if row.status == "already_ok":
            summary["already_ok"] += 1
        if row.action == "move_to_tv":
            summary["move_to_tv"] += 1
        elif row.action == "move_to_movies":
            summary["move_to_movies"] += 1
        elif "duplicate" in row.action:
            summary["duplicates_to_move"] += 1
        elif row.action == "quarantine":
            summary["broken_to_quarantine"] += 1
        elif row.status == "problem":
            summary["problem_files_left_alone"] += 1
        elif row.action == "remove_empty_folder":
            summary["remove_empty_folders"] += 1
    return summary


def write_reports(report_dir: Path, rows: list[PlanRow], summary: dict[str, int], plan_only: bool) -> None:
    payload = {"meta": {"version": VERSION, "generated_at": datetime.now().isoformat(timespec="seconds")}, "summary": summary, "rows": [asdict(r) for r in rows]}
    write_json(report_dir / "scan_plan.json", payload)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(PlanRow("", "", "", "", "", "", "", None, None, None, 0, "", 0, "").__dict__.keys())
    with (report_dir / "scan_plan.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    problems = [r for r in rows if r.status == "problem"]
    with (report_dir / "problem_files.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in problems:
            writer.writerow(asdict(row))
    with (report_dir / "execution_preview.log.txt").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            if row.status == "ready":
                handle.write(f"{row.action}: {row.source} -> {row.destination}\n")
    html_path = report_dir / "summary.html"
    html_rows = "".join(
        f"<tr><td>{html.escape(r.status)}</td><td>{html.escape(r.action)}</td><td>{html.escape(r.original_filename)}</td><td>{html.escape(r.matched_title)}</td><td>{r.confidence}</td><td>{html.escape(r.reason)}</td></tr>"
        for r in rows[:1000]
    )
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Media Cleanup Summary</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#111;color:#eee}table{border-collapse:collapse;width:100%}td,th{border:1px solid #444;padding:6px}th{background:#222}.ok{color:#8f8}.warn{color:#ffd166}</style></head><body>"
        f"<h1>Media Cleanup Summary</h1><p>Version {VERSION}</p><h2>Counts</h2><pre>{html.escape(json.dumps(summary, indent=2))}</pre>"
        "<h2>Rows</h2><table><tr><th>Status</th><th>Action</th><th>Original File</th><th>Matched Title</th><th>Confidence</th><th>Reason</th></tr>"
        f"{html_rows}</table></body></html>",
        encoding="utf-8",
    )
    zip_path = report_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in report_dir.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(report_dir.parent))


def latest_plan_dir(repo_root: Path) -> Path:
    base = repo_root / "reports" / "media_renamer"
    candidates = [p for p in base.iterdir() if p.is_dir() and (p / "scan_plan.json").exists()] if base.exists() else []
    if not candidates:
        raise FileNotFoundError("No cleanup plan found. Run Build Cleanup Plan first.")
    return sorted(candidates)[-1]


def move_path(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        return
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    shutil.move(str(source), str(destination))


def duplicate_destination_for_conflict(media_root: Path, plan_dir: Path, source: Path) -> Path:
    stamp = plan_dir.name
    try:
        rel = source.relative_to(media_root)
    except ValueError:
        rel = Path(source.name)
    return unique_destination(media_root / "_MediaRenamer_Duplicates" / stamp / rel)


def repair_movies_case(media_root: Path, logs: list[ExecutionRow]) -> None:
    actual = actual_child_dir(media_root, "Movies")
    proper = media_root / "Movies"
    if actual is None or actual.name == "Movies":
        return
    temp = media_root / f"__Movies_case_fix_tmp_{now_stamp()}__"
    actual.rename(temp)
    temp.rename(proper)
    logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), "repair_movies_folder_case", str(actual), str(proper), "ok", ""))


def repair_misplaced_housekeeping(media_root: Path, logs: list[ExecutionRow]) -> None:
    for folder_name in ["_MediaRenamer_Quarantine", "_MediaRenamer_Duplicates"]:
        root_target = media_root / folder_name
        root_target.mkdir(parents=True, exist_ok=True)
        for found in sorted(media_root.rglob(folder_name), key=lambda p: len(p.parts), reverse=True):
            if not found.is_dir():
                continue
            if found.resolve() == root_target.resolve() or is_inside(found, root_target):
                continue
            try:
                parent_rel = found.parent.relative_to(media_root)
            except ValueError:
                parent_rel = Path("external")
            recovered_name = safe_name("recovered " + " ".join(parent_rel.parts) + " " + now_stamp())
            destination = unique_destination(root_target / recovered_name)
            shutil.move(str(found), str(destination))
            logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), "repair_misplaced_housekeeping", str(found), str(destination), "ok", ""))


def apply_plan(repo_root: Path, media_root: Path) -> tuple[Path, dict[str, int]]:
    plan_dir = latest_plan_dir(repo_root)
    payload = load_json(plan_dir / "scan_plan.json")
    rows = [PlanRow(**row) for row in payload.get("rows", [])]
    logs: list[ExecutionRow] = []
    errors = 0
    source_missing = 0
    repair_movies_case(media_root, logs)
    repair_misplaced_housekeeping(media_root, logs)

    for row in rows:
        if row.status != "ready":
            continue
        source = Path(row.source)
        dest = Path(row.destination) if row.destination else None
        try:
            if row.action == "repair_movies_folder_case":
                repair_movies_case(media_root, logs)
            elif row.action == "remove_empty_folder":
                if source.exists() and source.is_dir():
                    try:
                        source.rmdir()
                        logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), row.action, str(source), "", "ok", ""))
                    except OSError:
                        logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), row.action, str(source), "", "not_empty", "folder not empty"))
                else:
                    logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), row.action, str(source), "", "missing", ""))
            elif row.action in {"move_to_tv", "move_to_movies", "move_sidecar", "move_duplicate", "move_existing_duplicate", "quarantine"}:
                if not source.exists():
                    source_missing += 1
                    logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), row.action, str(source), str(dest or ""), "source_missing", ""))
                    continue
                if dest is None:
                    raise ValueError("destination is required")
                if dest.exists() and source.resolve() != dest.resolve() and row.action in {"move_to_tv", "move_to_movies", "move_sidecar"}:
                    duplicate_dest = duplicate_destination_for_conflict(media_root, plan_dir, source)
                    move_path(source, duplicate_dest)
                    logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), "move_conflict_duplicate", str(source), str(duplicate_dest), "ok", f"destination already existed: {dest}"))
                    continue
                move_path(source, dest)
                logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), row.action, str(source), str(dest), "ok", ""))
        except Exception as exc:  # visible in execution log
            errors += 1
            logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), row.action, str(source), str(dest or ""), "error", str(exc)))

    # Final pass: remove empty ShowA/ShowB/Shows if possible.
    final_movies = actual_child_dir(media_root, "Movies")
    cleanup_folders = [media_root / "TV" / "ShowA", media_root / "TV" / "ShowB", media_root / "Shows"]
    if final_movies is not None and final_movies.name != "Movies":
        cleanup_folders.append(final_movies)
    for folder in cleanup_folders:
        try:
            if folder.exists() and folder.is_dir():
                folder.rmdir()
                logs.append(ExecutionRow(datetime.now().isoformat(timespec="seconds"), "remove_empty_folder", str(folder), "", "ok", ""))
        except OSError:
            pass

    write_json(plan_dir / "execution_log.json", {"meta": {"version": VERSION, "generated_at": datetime.now().isoformat(timespec="seconds")}, "rows": [asdict(log) for log in logs]})
    with (plan_dir / "execution.log.txt").open("w", encoding="utf-8", newline="\n") as handle:
        for log in logs:
            handle.write(f"{log.timestamp}\t{log.action}\t{log.result}\t{log.source}\t{log.destination}\t{log.error}\n")
    summary = {"executed": sum(1 for l in logs if l.result == "ok"), "errors": errors, "source_missing": source_missing, "log_count": len(logs)}
    (plan_dir / "post_apply_summary.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Post Apply Summary</title></head><body>"
        f"<h1>Post Apply Summary</h1><pre>{html.escape(json.dumps(summary, indent=2))}</pre></body></html>",
        encoding="utf-8",
    )
    with zipfile.ZipFile(plan_dir.with_suffix(".zip"), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in plan_dir.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(plan_dir.parent))
    return plan_dir, summary


def run_self_test() -> None:
    names = [
        "Abbott_Elementary_Safety_Day_S05E15.mp4",
        "CIA_(2026)_(2026)_S01E010.mp4",
        "Hacks__5x04.mp4",
        "Come_Dine_with_Me_(S2026E01).mp4",
        "The_Devil_Wears_Prada_2.mp4",
        "vsembed.ru_embed_tv_126027_5_16.mp4",
        "The_Hunting_Party_(S02E10.mp4",
        "Watson_(S02E20).a.mp4",
    ]
    failures = []
    for name in names:
        _id, season, episode = parse_episode_identity(Path(name))
        if name == "The_Devil_Wears_Prada_2.mp4":
            continue
        if season is None or episode is None:
            failures.append(name)
    if failures:
        raise AssertionError(f"episode parser failed: {failures}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Two-step media cleanup pipeline")
    parser.add_argument("mode", choices=["plan", "apply", "self-test"])
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--media-root", default=str(DEFAULT_MEDIA_ROOT))
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    media_root = media_root_from_arg(args.media_root)
    if args.mode == "self-test":
        run_self_test()
        print("media cleanup pipeline self-test passed")
        return 0
    if not media_root.exists():
        raise FileNotFoundError(f"Media root does not exist: {media_root}")
    if args.mode == "plan":
        report_dir, _rows, summary = generate_plan(repo_root, media_root)
        print(json.dumps({"summary": summary, "report_dir": str(report_dir)}, indent=2))
        return 0
    plan_dir, summary = apply_plan(repo_root, media_root)
    print(json.dumps({"plan_dir": str(plan_dir), "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
