"""Scan and safely organize home recordings into TV and Movies folders."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterable

from media_catalog_builder import build_media_reference, normalize_key, safe_int, safe_text


TOOL_DIR = Path(__file__).resolve().parent
RULES_PATH = TOOL_DIR / "media_rules.json"
REFERENCE_PATH = TOOL_DIR / "media_reference.json"
REPORT_ROOT = Path("reports/media_renamer")
DEFAULT_RECORDING_ROOT = Path(r"C:\X1_Share\Recordings")
SAFE_ACTIONS = {"move", "move_sidecar", "quarantine", "duplicate"}
ProgressCallback = Callable[[str], None]

EPISODE_PATTERNS = [
    re.compile(r"(?i)(?:^|[^a-z0-9])s(?P<season>\d{1,4})\s*[_. -]*e(?P<episode>\d{1,4})(?:$|[^a-z0-9])"),
    re.compile(r"(?i)(?:^|[^a-z0-9])s(?P<season>\d{1,4})\s*[_. -]*e(?P<episode>\d{1,4})[a-z]{1,3}(?:$|[^a-z0-9])"),
    re.compile(r"(?i)(?:^|[^a-z0-9])s(?P<season>\d{1,4})\s*[_ -]+e(?P<episode>\d{1,4})(?:$|[^a-z0-9])"),
    re.compile(r"(?i)(?:^|[^a-z0-9])(?P<season>\d{1,4})\s*x\s*(?P<episode>\d{1,4})(?:$|[^a-z0-9])"),
    re.compile(r"(?i)s(?P<season>\d{1,4})\s*[_. -]*e(?P<episode>\d{1,4})(?:$|[^a-z0-9])"),
    re.compile(r"(?i)s(?P<season>\d{1,4})\s*[_. -]*e(?P<episode>\d{1,4})[a-z]{1,3}(?:$|[^a-z0-9])"),
]
EMBED_TV_PATTERN = re.compile(r"(?i)embed[_ .-]*tv[_ .-]*(?P<tmdb>\d+)[_ .-]+(?P<season>\d+)[_ .-]+(?P<episode>\d+)")
TMDB_ID_PATTERN = re.compile(r"\[(?P<tmdb>\d{2,9})\]")
YEAR_PATTERN = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
BAD_CHARS = '<>:"/\\|?*'


@dataclass(frozen=True)
class ScanOptions:
    repo_root: Path
    input_root: Path = DEFAULT_RECORDING_ROOT
    output_root: Path = DEFAULT_RECORDING_ROOT
    validate_with_ffprobe: bool = True
    detect_hash_duplicates: bool = False
    skip_support_folders: bool = True
    minimum_auto_confidence: int = 85
    scan_workers: int = 4


@dataclass
class PlanItem:
    item_id: str
    category: str
    action: str
    safe: bool
    reason: str
    source_path: str
    original_filename: str
    destination_path: str
    destination_filename: str
    media_type: str
    matched_title: str
    tmdb_id: int
    season_number: int
    episode_number: int
    confidence: int
    size_bytes: int
    ffprobe_status: str
    duplicate_group: str
    notes: str


@dataclass(frozen=True)
class ExecutionOptions:
    repo_root: Path
    plan_json_path: Path
    move_files: bool = True


class MediaReference:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.movies = [item for item in payload.get("movies", []) if isinstance(item, dict)]
        self.shows = [item for item in payload.get("shows", []) if isinstance(item, dict)]
        self.movies_by_id = {safe_int(item.get("tmdb_id")): item for item in self.movies}
        self.shows_by_id = {safe_int(item.get("tmdb_id")): item for item in self.shows}
        self.episodes_by_identity: dict[tuple[int, int, int], dict[str, Any]] = {}
        for show in self.shows:
            show_id = safe_int(show.get("tmdb_id"))
            for season in show.get("seasons", []) if isinstance(show.get("seasons"), list) else []:
                season_number = safe_int(season.get("season_number"))
                for episode in season.get("episodes", []) if isinstance(season.get("episodes"), list) else []:
                    episode_number = safe_int(episode.get("episode_number"))
                    self.episodes_by_identity[(show_id, season_number, episode_number)] = {
                        "show": show,
                        "season": season,
                        "episode": episode,
                    }

    @classmethod
    def load_or_build(cls, repo_root: Path) -> "MediaReference":
        if not REFERENCE_PATH.exists():
            build_media_reference(repo_root)
        payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8-sig"))
        return cls(payload if isinstance(payload, dict) else {})


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_rules() -> dict[str, Any]:
    return json.loads(RULES_PATH.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_filename(value: str, fallback: str = "Unknown") -> str:
    text = safe_text(value) or fallback
    for char in BAD_CHARS:
        text = text.replace(char, " ")
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return text or fallback


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def ffprobe_exe() -> str:
    return shutil.which("ffprobe") or ""


def ffprobe_validate(path: Path) -> tuple[str, str]:
    exe = ffprobe_exe()
    if not exe:
        return "not checked", "ffprobe not found"
    try:
        completed = subprocess.run(
            [exe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return "broken", str(exc)
    if completed.returncode != 0:
        return "broken", (completed.stderr or completed.stdout or f"ffprobe exit {completed.returncode}")[:400]
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return "broken", "ffprobe returned unreadable output"
    streams = payload.get("streams") if isinstance(payload, dict) else None
    return ("ok", "video stream found") if streams else ("broken", "no video stream found")


def extract_tmdb_id_from_path(path: Path) -> int:
    for part in reversed(path.parts):
        match = TMDB_ID_PATTERN.search(part)
        if match:
            return safe_int(match.group("tmdb"))
    return 0


def parse_episode_identity(text_or_path: str | Path) -> tuple[int, int, int]:
    text = Path(text_or_path).name if isinstance(text_or_path, Path) else safe_text(text_or_path)
    embed = EMBED_TV_PATTERN.search(text)
    if embed:
        return safe_int(embed.group("season")), safe_int(embed.group("episode")), safe_int(embed.group("tmdb"))
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(text)
        if match:
            return safe_int(match.group("season")), safe_int(match.group("episode")), 0
    return 0, 0, 0


def title_hint_from_name(name: str) -> str:
    text = Path(name).stem
    text = EMBED_TV_PATTERN.sub(" ", text)
    text = TMDB_ID_PATTERN.sub(" ", text)
    text = re.sub(r"(?i)(?:^|[^a-z0-9])s\d{1,4}\s*[_. -]*e\d{1,4}(?:$|[^a-z0-9])", " ", text)
    text = re.sub(r"(?i)(?:^|[^a-z0-9])s\d{1,4}\s*[_. -]*e\d{1,4}[a-z]{1,3}(?:$|[^a-z0-9])", " ", text)
    text = re.sub(r"(?i)s\d{1,4}\s*[_. -]*e\d{1,4}(?:$|[^a-z0-9])", " ", text)
    text = re.sub(r"(?i)s\d{1,4}\s*[_. -]*e\d{1,4}[a-z]{1,3}(?:$|[^a-z0-9])", " ", text)
    text = re.sub(r"(?i)(?:^|[^a-z0-9])\d{1,4}\s*x\s*\d{1,4}(?:$|[^a-z0-9])", " ", text)
    text = YEAR_PATTERN.sub(" ", text)
    text = re.sub(r"(?i)\b(720p|1080p|2160p|4k|hd|fullhd|uhd|webrip|web dl|web-dl|hdtv|x264|x265|h264|h265|aac|tmp|copy|proper|repack)\b", " ", text)
    text = re.sub(r"(?i)(?:^|[\s_.-])(?:a|b|bb|f|copy|\d+)$", " ", text)
    text = re.sub(r"[_\.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip(" -_.()[]")


def title_hint_from_folder(name: str) -> str:
    return title_hint_from_name(name)


def similarity(left: str, right: str) -> int:
    left_key = normalize_key(left)
    right_key = normalize_key(right)
    if not left_key or not right_key:
        return 0
    if left_key == right_key:
        return 100
    left_tokens = set(left_key.split())
    right_tokens = set(right_key.split())
    overlap = left_tokens & right_tokens
    token_score = 0
    if overlap:
        precision = len(overlap) / len(left_tokens)
        recall = len(overlap) / len(right_tokens)
        token_score = round((2 * precision * recall / (precision + recall)) * 100) if precision + recall else 0
        if left_tokens.issubset(right_tokens) or right_tokens.issubset(left_tokens):
            token_score = max(token_score, 92)
    sequence = round(SequenceMatcher(None, left_key, right_key).ratio() * 100)
    return max(token_score, sequence)


def candidate_titles(path: Path, input_root: Path) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = [("filename", title_hint_from_name(path.name))]
    try:
        parts = list(path.relative_to(input_root).parts)
    except ValueError:
        parts = list(path.parts)
    lowered = [part.lower() for part in parts]
    if "tv" in lowered:
        index = lowered.index("tv")
        if len(parts) > index + 1:
            candidates.append(("show folder", title_hint_from_folder(parts[index + 1])))
    if "shows" in lowered:
        index = lowered.index("shows")
        if len(parts) > index + 1:
            candidates.append(("old shows folder", title_hint_from_folder(parts[index + 1])))
    parent = path.parent.name
    if parent.lower() not in {"tv", "movies", "shows", "_unsorted", "recordings"} and not parent.lower().startswith("season"):
        candidates.append(("parent folder", title_hint_from_folder(parent)))
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for source, value in candidates:
        key = normalize_key(value)
        if key and key not in seen:
            seen.add(key)
            unique.append((source, value))
    return unique


def best_catalog_match(candidates: list[tuple[str, str]], items: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, int, str]:
    best: dict[str, Any] | None = None
    best_score = 0
    best_source = ""
    for source, candidate in candidates:
        for item in items:
            titles = [safe_text(item.get("title"))]
            title_tokens = item.get("alternate_normalized_title_tokens")
            if isinstance(title_tokens, list):
                titles.extend(safe_text(token) for token in title_tokens)
            score = max((similarity(candidate, title) for title in titles if title), default=0)
            if source == "filename":
                score = min(100, score + 3)
            if score > best_score:
                best = item
                best_score = score
                best_source = source
    return best, min(best_score, 100), best_source


def path_kind_hint(path: Path, input_root: Path) -> str:
    try:
        lowered = [part.lower() for part in path.relative_to(input_root).parts]
    except ValueError:
        lowered = [part.lower() for part in path.parts]
    if "movies" in lowered or "movie" in lowered:
        return "movie"
    if "tv" in lowered or "shows" in lowered or "_unsorted" in lowered:
        return "tv"
    return ""


def episode_by_number(reference: MediaReference, show_id: int, season: int, episode: int) -> dict[str, Any] | None:
    return reference.episodes_by_identity.get((show_id, season, episode))


def season_folder_name(season: dict[str, Any], season_number: int) -> str:
    name = clean_filename(safe_text(season.get("season_name")), "")
    if not name:
        return f"Season {season_number:02d}"
    key = normalize_key(name)
    if key in {"season", str(season_number), f"{season_number:02d}", f"season {season_number}", f"season {season_number:02d}"}:
        return f"Season {season_number:02d}"
    return f"Season {season_number:02d} - {name}"


def episode_destination(output_root: Path, rules: dict[str, Any], show: dict[str, Any], season: dict[str, Any], episode: dict[str, Any], extension: str) -> Path:
    tree = rules["folder_tree"]
    show_title = clean_filename(safe_text(show.get("title")), "Unknown Show")
    season_number = safe_int(season.get("season_number"))
    episode_number = safe_int(episode.get("episode_number"))
    values = {
        "show_title": show_title,
        "tmdb_id": safe_int(show.get("tmdb_id")),
        "season_number_2": f"{season_number:02d}",
        "season_name": clean_filename(safe_text(season.get("season_name")), ""),
        "episode_number_2": f"{episode_number:02d}",
        "episode_name": clean_filename(safe_text(episode.get("episode_name")), f"Episode {episode_number:02d}"),
        "extension": extension.lower(),
    }
    show_folder = tree["show_folder"].format(**values)
    episode_file = tree["episode_file"].format(**values)
    return output_root / tree["tv_root"] / show_folder / season_folder_name(season, season_number) / episode_file


def movie_destination(output_root: Path, rules: dict[str, Any], movie: dict[str, Any], extension: str) -> Path:
    tree = rules["folder_tree"]
    title = clean_filename(safe_text(movie.get("title")), "Unknown Movie")
    year = safe_text(movie.get("release_year")) or "0000"
    values = {
        "movie_title": title,
        "year": year,
        "tmdb_id": safe_int(movie.get("tmdb_id")),
        "extension": extension.lower(),
    }
    return output_root / tree["movies_root"] / tree["movie_folder"].format(**values) / tree["movie_file"].format(**values)


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve())) if left.exists() else False


def support_dirs(rules: dict[str, Any]) -> set[str]:
    return {safe_text(name).lower() for name in rules.get("skip_directory_names", [])}


def iter_scan_files(input_root: Path, rules: dict[str, Any]) -> Iterable[Path]:
    skipped = support_dirs(rules)
    media_ext = {safe_text(ext).lower() for ext in rules.get("media_extensions", [])}
    sidecar_ext = {safe_text(ext).lower() for ext in rules.get("sidecar_extensions", [])}
    min_extensionless = safe_int(rules.get("extensionless_media_min_bytes"), 20_000_000)
    for root, dirnames, filenames in os.walk(input_root):
        root_path = Path(root)
        skipped_children = [name for name in dirnames if name.lower() in skipped]
        for child_name in skipped_children:
            child = root_path / child_name
            try:
                direct_children = list(child.iterdir())
            except OSError:
                direct_children = []
            for direct in direct_children:
                if not direct.is_file():
                    continue
                suffix = direct.suffix.lower()
                if suffix in media_ext or suffix in sidecar_ext or (suffix == "" and file_size(direct) >= min_extensionless):
                    yield direct
        dirnames[:] = [name for name in dirnames if name.lower() not in skipped]
        for filename in filenames:
            path = root_path / filename
            suffix = path.suffix.lower()
            if suffix in media_ext or suffix in sidecar_ext:
                yield path
            elif suffix == "" and file_size(path) >= min_extensionless:
                yield path


def quarantine_path(output_root: Path, stamp: str, source: Path) -> Path:
    return output_root / "_MediaRenamer_Quarantine" / stamp / source.name


def duplicates_path(output_root: Path, stamp: str, source: Path) -> Path:
    return output_root / "_MediaRenamer_Duplicates" / stamp / source.name


def classify_and_match(path: Path, options: ScanOptions, reference: MediaReference, rules: dict[str, Any], stamp: str) -> PlanItem:
    size = file_size(path)
    suffix = path.suffix.lower()
    media_ext = {safe_text(ext).lower() for ext in rules.get("media_extensions", [])}
    sidecar_ext = {safe_text(ext).lower() for ext in rules.get("sidecar_extensions", [])}
    ff_status = "not checked"
    ff_note = ""

    if suffix in sidecar_ext and suffix not in media_ext:
        return PlanItem("", "Skipped support files", "skip", False, "sidecar waits for matching media file", str(path), path.name, "", "", "sidecar", "", 0, 0, 0, 0, size, ff_status, "", "")
    if suffix not in media_ext and suffix != "":
        return PlanItem("", "Skipped support files", "skip", False, "support file", str(path), path.name, "", "", "support", "", 0, 0, 0, 0, size, ff_status, "", "")
    if size == 0:
        dest = quarantine_path(options.output_root, stamp, path)
        return PlanItem("", "Broken/empty", "quarantine", True, "zero-byte file", str(path), path.name, str(dest), dest.name, "unknown", "", 0, 0, 0, 100, size, "broken", "", "")
    if ".tmp." in path.name.lower() or path.name.lower().endswith(".tmp.mp4"):
        dest = quarantine_path(options.output_root, stamp, path)
        return PlanItem("", "Broken/empty", "quarantine", True, "partial-looking temporary file", str(path), path.name, str(dest), dest.name, "unknown", "", 0, 0, 0, 95, size, "suspect", "", "")
    if options.validate_with_ffprobe or suffix == "":
        ff_status, ff_note = ffprobe_validate(path)
        if ff_status == "broken":
            dest = quarantine_path(options.output_root, stamp, path)
            return PlanItem("", "Broken/empty", "quarantine", True, "file has no readable video stream", str(path), path.name, str(dest), dest.name, "unknown", "", 0, 0, 0, 95, size, ff_status, "", ff_note)
        if suffix == "" and ff_status != "ok":
            return PlanItem("", "Needs review", "review", False, "extensionless file could not be proven as media", str(path), path.name, "", "", "unknown", "", 0, 0, 0, 0, size, ff_status, "", ff_note)

    season_number, episode_number, embedded_id = parse_episode_identity(path.name)
    explicit_id = embedded_id or extract_tmdb_id_from_path(path)
    candidates = candidate_titles(path, options.input_root)
    kind_hint = path_kind_hint(path, options.input_root)
    extension = suffix or ".mp4"

    if season_number and episode_number:
        show = reference.shows_by_id.get(explicit_id) if explicit_id else None
        score = 100 if show else 0
        source = "TMDb ID" if show else ""
        if not show:
            show, score, source = best_catalog_match(candidates, reference.shows)
        if not show:
            return PlanItem("", "Needs review", "review", False, "show was not found in the catalog", str(path), path.name, "", "", "tv", "", 0, season_number, episode_number, 0, size, ff_status, "", "")
        show_id = safe_int(show.get("tmdb_id"))
        match = episode_by_number(reference, show_id, season_number, episode_number)
        if match:
            destination = episode_destination(options.output_root, rules, match["show"], match["season"], match["episode"], extension)
            episode_name = safe_text(match["episode"].get("episode_name"))
        else:
            season = {"season_number": season_number, "season_name": ""}
            episode = {"episode_number": episode_number, "episode_name": f"Episode {episode_number:02d}"}
            destination = episode_destination(options.output_root, rules, show, season, episode, extension)
            episode_name = episode["episode_name"]
            score = min(score, 84)
        confidence = 100 if explicit_id and explicit_id == show_id else min(99, score)
        if same_path(path, destination):
            return PlanItem("", "Already OK", "already_ok", False, "already in the correct TV folder", str(path), path.name, str(destination), destination.name, "tv", safe_text(show.get("title")), show_id, season_number, episode_number, 100, size, ff_status, "", episode_name)
        if confidence >= options.minimum_auto_confidence:
            return PlanItem("", "Ready to fix", "move", True, f"matched TV episode by {source or 'filename/folder'}", str(path), path.name, str(destination), destination.name, "tv", safe_text(show.get("title")), show_id, season_number, episode_number, confidence, size, ff_status, "", episode_name)
        return PlanItem("", "Needs review", "review", False, "TV match is below 85% confidence", str(path), path.name, str(destination), destination.name, "tv", safe_text(show.get("title")), show_id, season_number, episode_number, confidence, size, ff_status, "", episode_name)

    movie = reference.movies_by_id.get(explicit_id) if explicit_id else None
    movie_score = 100 if movie else 0
    movie_source = "TMDb ID" if movie else ""
    if not movie:
        movie, movie_score, movie_source = best_catalog_match(candidates, reference.movies)
    show_guess, show_score, _ = best_catalog_match(candidates, reference.shows)
    if kind_hint == "tv" and show_guess and show_score >= max(movie_score + 8, 85):
        return PlanItem("", "Needs review", "review", False, "looks like TV but no episode number was found", str(path), path.name, "", "", "tv", safe_text(show_guess.get("title")), safe_int(show_guess.get("tmdb_id")), 0, 0, show_score, size, ff_status, "", "")
    if not movie:
        return PlanItem("", "Needs review", "review", False, "movie was not found in the catalog", str(path), path.name, "", "", "movie", "", 0, 0, 0, 0, size, ff_status, "", "")
    confidence = min(100, movie_score)
    destination = movie_destination(options.output_root, rules, movie, extension)
    if same_path(path, destination):
        return PlanItem("", "Already OK", "already_ok", False, "already in the correct Movies folder", str(path), path.name, str(destination), destination.name, "movie", safe_text(movie.get("title")), safe_int(movie.get("tmdb_id")), 0, 0, 100, size, ff_status, "", "")
    if confidence >= options.minimum_auto_confidence:
        return PlanItem("", "Ready to fix", "move", True, f"matched movie by {movie_source or 'filename/folder'}", str(path), path.name, str(destination), destination.name, "movie", safe_text(movie.get("title")), safe_int(movie.get("tmdb_id")), 0, 0, confidence, size, ff_status, "", "")
    return PlanItem("", "Needs review", "review", False, "movie match is below 85% confidence", str(path), path.name, str(destination), destination.name, "movie", safe_text(movie.get("title")), safe_int(movie.get("tmdb_id")), 0, 0, confidence, size, ff_status, "", "")


def identity_key(item: PlanItem) -> tuple[str, int, int, int] | None:
    if item.action not in {"move", "already_ok"}:
        return None
    if item.media_type == "tv":
        return ("tv", item.tmdb_id, item.season_number, item.episode_number)
    if item.media_type == "movie":
        return ("movie", item.tmdb_id, 0, 0)
    return None


def normalized_bonus(item: PlanItem) -> int:
    return 1 if item.action == "already_ok" or item.source_path == item.destination_path else 0


def item_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mark_duplicates(items: list[PlanItem], output_root: Path, stamp: str, use_hash: bool) -> None:
    groups: dict[tuple[str, int, int, int], list[PlanItem]] = {}
    for item in items:
        key = identity_key(item)
        if key:
            groups.setdefault(key, []).append(item)
    group_index = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        group_index += 1
        group_id = f"duplicate-{group_index:04d}"
        best = max(members, key=lambda item: (item.ffprobe_status == "ok", item.size_bytes, normalized_bonus(item), item.confidence))
        hashes: dict[str, str] = {}
        if use_hash:
            same_size_members = [member for member in members if sum(1 for other in members if other.size_bytes == member.size_bytes) > 1]
            for member in same_size_members:
                try:
                    hashes[member.source_path] = item_hash(Path(member.source_path))
                except OSError:
                    hashes[member.source_path] = ""
        for member in members:
            member.duplicate_group = group_id
            if member is best:
                member.notes = append_note(member.notes, "kept as best duplicate copy")
                continue
            dest = duplicates_path(output_root, stamp, Path(member.source_path))
            member.category = "Duplicates"
            member.action = "duplicate"
            member.safe = True
            member.reason = f"duplicate of {best.source_path}"
            member.destination_path = str(dest)
            member.destination_filename = dest.name
            if use_hash and hashes.get(member.source_path):
                member.notes = append_note(member.notes, f"hash={hashes[member.source_path]}")


def append_note(existing: str, note: str) -> str:
    return "; ".join(part for part in [existing, note] if part)


def attach_sidecars(items: list[PlanItem], files: list[Path]) -> None:
    safe_media_by_base = {
        str(Path(item.source_path).with_suffix("").resolve()).lower(): item
        for item in items
        if item.action == "move" and item.safe
    }
    sidecar_items = [item for item in items if item.media_type == "sidecar"]
    for item in sidecar_items:
        path = Path(item.source_path)
        media_item = safe_media_by_base.get(str(path.with_suffix("").resolve()).lower())
        if not media_item:
            continue
        dest = Path(media_item.destination_path).with_suffix(path.suffix.lower())
        item.category = "Ready to fix"
        item.action = "move_sidecar"
        item.safe = True
        item.reason = "sidecar has the same base name as a safe media file"
        item.destination_path = str(dest)
        item.destination_filename = dest.name
        item.matched_title = media_item.matched_title
        item.tmdb_id = media_item.tmdb_id
        item.season_number = media_item.season_number
        item.episode_number = media_item.episode_number
        item.confidence = media_item.confidence
        item.duplicate_group = media_item.duplicate_group


def summarize(items: list[PlanItem]) -> dict[str, int]:
    categories = {
        "Ready to fix": 0,
        "Already OK": 0,
        "Needs review": 0,
        "Broken/empty": 0,
        "Duplicates": 0,
        "Skipped support files": 0,
    }
    for item in items:
        categories[item.category] = categories.get(item.category, 0) + 1
    categories["Total"] = len(items)
    categories["Safe actions"] = sum(1 for item in items if item.safe and item.action in SAFE_ACTIONS)
    return categories


def plan_scan(options: ScanOptions, progress_callback: ProgressCallback | None = None) -> tuple[Path, list[PlanItem]]:
    rules = load_rules()
    reference = MediaReference.load_or_build(options.repo_root)
    stamp = utc_stamp()
    report_dir = options.repo_root / REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=True)
    files = list(iter_scan_files(options.input_root, rules))
    worker_count = max(1, min(options.scan_workers, max(1, len(files))))
    items: list[PlanItem] = []

    if progress_callback:
        progress_callback(f"Found {len(files)} files to inspect.")
    if worker_count == 1:
        for path in files:
            items.append(classify_and_match(path, options, reference, rules, stamp))
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {executor.submit(classify_and_match, path, options, reference, rules, stamp): path for path in files}
            for index, future in enumerate(as_completed(futures), start=1):
                path = futures[future]
                try:
                    items.append(future.result())
                except Exception as exc:
                    items.append(PlanItem("", "Needs review", "review", False, "scan error", str(path), path.name, "", "", "unknown", "", 0, 0, 0, 0, file_size(path), "not checked", "", str(exc)))
                if progress_callback and (index % 25 == 0 or index == len(files)):
                    progress_callback(f"Checked {index} of {len(files)} files.")

    attach_sidecars(items, files)
    mark_duplicates(items, options.output_root, stamp, options.detect_hash_duplicates)
    items.sort(key=lambda item: (item.category, item.source_path.lower()))
    for index, item in enumerate(items, start=1):
        item.item_id = f"MR-{index:06d}"
    write_report_files(report_dir, options, items, [])
    return report_dir, items


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else list(asdict(PlanItem("", "", "", False, "", "", "", "", "", "", "", 0, 0, 0, 0, 0, "", "", "")).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report_files(report_dir: Path, options: ScanOptions, items: list[PlanItem], execution_rows: list[dict[str, Any]]) -> None:
    rows = [asdict(item) for item in items]
    summary = summarize(items)
    scan_json = report_dir / "scan_plan.json"
    scan_csv = report_dir / "scan_plan.csv"
    summary_html = report_dir / "summary.html"
    execution_json = report_dir / "execution_log.json"
    execution_txt = report_dir / "execution.log.txt"
    zip_path = Path(str(report_dir) + ".zip")

    write_json(scan_json, {"schema": "media_renamer.scan_plan.v3", "version": "0.3.0", "created_utc": datetime.now(timezone.utc).isoformat(), "options": options_dict(options), "summary": summary, "items": rows})
    write_csv(scan_csv, rows)
    summary_html.write_text(render_summary_html(summary, rows), encoding="utf-8")
    write_json(execution_json, {"schema": "media_renamer.execution_log.v3", "version": "0.3.0", "items": execution_rows})
    execution_txt.write_text(render_execution_text(execution_rows), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in [scan_json, scan_csv, summary_html, execution_json, execution_txt]:
            archive.write(path, path.name)


def options_dict(options: ScanOptions) -> dict[str, Any]:
    return {
        "repo_root": str(options.repo_root),
        "input_root": str(options.input_root),
        "output_root": str(options.output_root),
        "validate_with_ffprobe": options.validate_with_ffprobe,
        "detect_hash_duplicates": options.detect_hash_duplicates,
        "skip_support_folders": options.skip_support_folders,
        "minimum_auto_confidence": options.minimum_auto_confidence,
        "scan_workers": options.scan_workers,
    }


def render_summary_html(summary: dict[str, int], rows: list[dict[str, Any]]) -> str:
    headers = ["category", "action", "confidence", "reason", "original_filename", "destination_filename", "matched_title", "tmdb_id", "season_number", "episode_number", "source_path", "destination_path", "notes"]
    cards = "".join(f"<div class='card'><b>{html.escape(key)}</b><span>{value}</span></div>" for key, value in summary.items())
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers) + "</tr>")
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Media Renamer Summary</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#f8fafc;color:#111827}}
.cards{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}}.card{{border:1px solid #cbd5e1;border-radius:8px;padding:10px 12px;background:white;min-width:140px}}.card span{{display:block;font-size:24px;font-weight:700;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}th,td{{border-bottom:1px solid #e5e7eb;padding:7px;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#e2e8f0}}
</style></head>
<body><h1>Media Renamer Summary</h1><p>Safe matches will be fixed automatically. Problem files will be left alone.</p><div class="cards">{cards}</div>
<table><thead><tr>{''.join(f'<th>{html.escape(header)}</th>' for header in headers)}</tr></thead><tbody>{''.join(body)}</tbody></table></body></html>
"""


def render_execution_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No safe changes have been executed yet.\n"
    lines = []
    for row in rows:
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + "\n"


def load_plan(plan_json_path: Path) -> dict[str, Any]:
    return json.loads(plan_json_path.read_text(encoding="utf-8-sig"))


def move_path(source: Path, destination: Path, move_files: bool) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    final_destination = destination
    if final_destination.exists():
        counter = 1
        while final_destination.exists():
            final_destination = destination.with_name(f"{destination.stem} ({counter}){destination.suffix}")
            counter += 1
    if move_files:
        shutil.move(str(source), str(final_destination))
    return str(final_destination)


def cleanup_empty_source_folders(source: Path, input_root: Path, rows: list[dict[str, Any]], rules: dict[str, Any]) -> None:
    cleanup_names = {safe_text(name).lower() for name in rules.get("cleanup_folder_names", [])}
    cleanup_names.add("_unsorted")
    protected_names = {
        "tv",
        "movies",
        safe_text(rules.get("quarantine_folder", "_MediaRenamer_Quarantine")).lower(),
        safe_text(rules.get("duplicates_folder", "_MediaRenamer_Duplicates")).lower(),
    }
    folder = source
    while folder != input_root:
        if input_root not in folder.parents:
            break
        folder_name = folder.name.lower()
        if folder_name in protected_names:
            break
        try:
            folder.rmdir()
            rows.append(log_row("remove_empty_folder", str(folder), "", str(folder), "", 100, "empty source folder removed after safe moves", "executed", ""))
        except OSError as exc:
            if folder_name in cleanup_names:
                rows.append(log_row("remove_empty_folder", str(folder), "", str(folder), "", 0, "folder not empty after safe moves", "skipped", str(exc)))
            break
        folder = folder.parent


def log_row(action: str, source: str, destination: str, title: str, tmdb_id: Any, confidence: Any, reason: str, result: str, error: str, season: Any = "", episode: Any = "") -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "original full path": source,
        "original filename": Path(source).name if source else "",
        "destination full path": destination,
        "matched title": title,
        "tmdb_id": tmdb_id,
        "season number": season,
        "episode number": episode,
        "confidence": confidence,
        "reason": reason,
        "result": result,
        "error": error,
    }


def execute_plan(options: ExecutionOptions, progress_callback: ProgressCallback | None = None) -> tuple[Path, list[dict[str, Any]]]:
    payload = load_plan(options.plan_json_path)
    rules = load_rules()
    report_dir = options.plan_json_path.parent
    option_data = payload.get("options", {}) if isinstance(payload, dict) else {}
    input_root = Path(safe_text(option_data.get("input_root")) or str(DEFAULT_RECORDING_ROOT))
    rows = payload.get("items", []) if isinstance(payload, dict) else []
    execution_rows: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("safe") or row.get("action") not in SAFE_ACTIONS:
            continue
        source = Path(safe_text(row.get("source_path")))
        destination = Path(safe_text(row.get("destination_path")))
        if not source.exists():
            execution_rows.append(log_row(safe_text(row.get("action")), str(source), str(destination), safe_text(row.get("matched_title")), row.get("tmdb_id"), row.get("confidence"), safe_text(row.get("reason")), "failed", "source missing", row.get("season_number"), row.get("episode_number")))
            continue
        try:
            final_destination = move_path(source, destination, options.move_files)
            execution_rows.append(log_row(safe_text(row.get("action")), str(source), final_destination, safe_text(row.get("matched_title")), row.get("tmdb_id"), row.get("confidence"), safe_text(row.get("reason")), "executed", "", row.get("season_number"), row.get("episode_number")))
            if options.move_files:
                cleanup_empty_source_folders(source.parent, input_root, execution_rows, rules)
        except Exception as exc:
            execution_rows.append(log_row(safe_text(row.get("action")), str(source), str(destination), safe_text(row.get("matched_title")), row.get("tmdb_id"), row.get("confidence"), safe_text(row.get("reason")), "failed", str(exc), row.get("season_number"), row.get("episode_number")))
        if progress_callback:
            progress_callback(f"Handled {len(execution_rows)} safe actions.")

    items = [PlanItem(**item) for item in rows if isinstance(item, dict)]
    write_report_files(report_dir, ScanOptions(repo_root=options.repo_root, input_root=input_root, output_root=Path(safe_text(option_data.get("output_root")) or str(DEFAULT_RECORDING_ROOT))), items, execution_rows)
    return report_dir, execution_rows


def run_scan(
    repo_root: Path,
    input_root: Path,
    output_root: Path,
    validate_with_ffprobe: bool = False,
    detect_hash_duplicates: bool = False,
    scan_workers: int = 4,
    minimum_auto_confidence: int = 85,
    progress_callback: ProgressCallback | None = None,
) -> tuple[Path, list[PlanItem]]:
    return plan_scan(
        ScanOptions(
            repo_root=repo_root.resolve(),
            input_root=input_root.resolve(),
            output_root=output_root.resolve(),
            validate_with_ffprobe=validate_with_ffprobe,
            detect_hash_duplicates=detect_hash_duplicates,
            minimum_auto_confidence=minimum_auto_confidence,
            scan_workers=scan_workers,
        ),
        progress_callback,
    )


def run_self_test(repo_root: Path) -> None:
    reference_path, stats = build_media_reference(repo_root)
    reference = MediaReference(json.loads(reference_path.read_text(encoding="utf-8-sig")))
    samples = {
        "Abbott_Elementary_Safety_Day_S05E15.mp4": (5, 15, 0),
        "CIA_(2026)_(2026)_S01E010.mp4": (1, 10, 0),
        "Hacks__5x04.mp4": (5, 4, 0),
        "MarshalsS01E05.mp4": (1, 5, 0),
        "Come_Dine_with_Me_(S2026E01).mp4": (2026, 1, 0),
        "vsembed.ru_embed_tv_126027_5_16.mp4": (5, 16, 126027),
        "The_Hunting_Party_(S02E10.mp4": (2, 10, 0),
        "Watson_(S02E20).a.mp4": (2, 20, 0),
    }
    for name, expected in samples.items():
        actual = parse_episode_identity(name)
        if actual != expected:
            raise AssertionError(f"{name}: expected {expected}, got {actual}")
    if parse_episode_identity("The_Devil_Wears_Prada_2.mp4") != (0, 0, 0):
        raise AssertionError("Movie title number was misread as an episode")
    movie, score, _ = best_catalog_match([("filename", title_hint_from_name("The_Devil_Wears_Prada_2.mp4"))], reference.movies)
    if not movie or safe_text(movie.get("title")) != "The Devil Wears Prada 2" or score < 85:
        raise AssertionError("The Devil Wears Prada 2 did not match as a movie")
    if stats.shows <= 0 or stats.movies <= 0:
        raise AssertionError("Reference build did not produce shows and movies")
    with TemporaryDirectory() as temp:
        temp_root = Path(temp)
        report_dir, items = run_scan(repo_root, temp_root, temp_root, scan_workers=1, validate_with_ffprobe=False)
        required = ["scan_plan.json", "scan_plan.csv", "summary.html", "execution_log.json", "execution.log.txt"]
        missing = [name for name in required if not (report_dir / name).exists()]
        if missing:
            raise AssertionError(f"Missing self-test report files: {missing}")
        if items:
            raise AssertionError("Empty self-test folder should not produce plan items")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Scan recordings and create a safe media renamer plan.")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--input-root", default=str(DEFAULT_RECORDING_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_RECORDING_ROOT))
    parser.add_argument("--execute-plan")
    parser.add_argument("--ffprobe", action="store_true")
    parser.add_argument("--hash-duplicates", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root)
    if args.self_test:
        run_self_test(repo_root)
        print("SELF TEST PASSED")
        return
    if args.execute_plan:
        report_dir, rows = execute_plan(ExecutionOptions(repo_root=repo_root, plan_json_path=Path(args.execute_plan)))
        print(f"report_dir={report_dir}")
        print(f"executed_rows={len(rows)}")
        return
    report_dir, items = run_scan(
        repo_root=repo_root,
        input_root=Path(args.input_root),
        output_root=Path(args.output_root),
        validate_with_ffprobe=args.ffprobe,
        detect_hash_duplicates=args.hash_duplicates,
        scan_workers=args.workers,
    )
    print(f"report_dir={report_dir}")
    print(f"items={len(items)}")
    print(f"zip={report_dir}.zip")


if __name__ == "__main__":
    main()
