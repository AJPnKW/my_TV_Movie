from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from media_catalog_builder import MediaReference, SeasonRef, ShowRef, clean_title, load_reference, normalize_key, save_reference
from media_matcher import match_movie, match_tv
from media_validator import validate_media

VERSION = "0.4.8"
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv"}
SIDECAR_EXTENSIONS = {".srt", ".ass", ".vtt", ".nfo"}
SUPPORT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".pdf", ".docx", ".html", ".ps1", ".json", ".bak", ".txt"}
HOUSEKEEPING = {"_MediaRenamer_Duplicates", "_MediaRenamer_Quarantine", "_MediaRenamer_Review"}
NEVER_SKIP = {"TV", "Movies", "movies", "_Unsorted", "ShowA", "ShowB"}
SKIP_NAMES = {"_Metadata", "assets", "archived", "reports", ".git", "__pycache__"} | HOUSEKEEPING
SAFE_CONFIDENCE = 85
GENERIC_SEASON_SUFFIXES = {"season 1", "season 2", "season 3", "season 4", "season 5", "series 1", "series 2", "series 3", "series 4", "series 5"}

@dataclass(slots=True)
class PlanRow:
    action: str
    status: str
    source: str
    destination: str
    kind: str
    title: str
    tmdb_id: int | None
    season: int | None
    episode: int | None
    confidence: int
    reason: str

@dataclass(slots=True)
class AuditGap:
    category: str
    path: str
    detail: str

@dataclass(slots=True)
class RunContext:
    repo: Path
    media_root: Path
    timestamp: str
    report_dir: Path
    ref: MediaReference
    rows: list[PlanRow] = field(default_factory=list)
    execution_log: list[dict[str, Any]] = field(default_factory=list)
    audit_gaps: list[AuditGap] = field(default_factory=list)

def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_name(value: str) -> str:
    text = value.strip()
    text = re.sub(r"[<>:\"/\\|?*]", " - ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("...", "...")
    return text.rstrip(" .") or "Unknown"

def season_folder(show: ShowRef, season_number: int) -> str:
    season = show.seasons.get(season_number)
    base = f"Season {season_number:02d}" if season_number < 100 else f"Season {season_number}"
    if not season or not season.name:
        return base
    season_name = safe_name(season.name)
    norm = normalize_key(season_name)
    if norm in GENERIC_SEASON_SUFFIXES or norm == normalize_key(base):
        return base
    return f"{base} - {season_name}"

def tv_destination(media_root: Path, show: ShowRef, season: int, episode: int, episode_name: str, suffix: str) -> Path:
    ep_name = safe_name(episode_name or f"Episode {episode:02d}")
    show_name = safe_name(show.title)
    folder = media_root / "TV" / f"{show_name} [{show.tmdb_id}]" / season_folder(show, season)
    season_token = f"S{season:02d}" if season < 100 else f"S{season}"
    filename = f"{show_name} - {season_token}E{episode:02d} - {ep_name}{suffix.lower()}"
    return folder / filename

def movie_destination(media_root: Path, title: str, year: str, tmdb_id: int, suffix: str) -> Path:
    movie_name = safe_name(title)
    year_text = f" ({year})" if year else ""
    folder = media_root / "Movies" / f"{movie_name}{year_text} [{tmdb_id}]"
    filename = f"{movie_name}{year_text}{suffix.lower()}"
    return folder / filename

def is_media(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in MEDIA_EXTENSIONS

def is_sidecar(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in SIDECAR_EXTENSIONS

def under(path: Path, ancestor: Path) -> bool:
    try:
        path.resolve().relative_to(ancestor.resolve())
        return True
    except ValueError:
        return False

def should_scan(path: Path, media_root: Path) -> bool:
    rel_parts = path.relative_to(media_root).parts if under(path, media_root) else path.parts
    for part in rel_parts[:-1] if path.is_file() else rel_parts:
        if part in NEVER_SKIP:
            continue
        if part in SKIP_NAMES:
            return False
        if part.startswith(".venv"):
            return False
    return True

def all_files(media_root: Path) -> list[Path]:
    if not media_root.exists():
        raise FileNotFoundError(f"Media root does not exist: {media_root}")
    items = []
    for path in media_root.rglob("*"):
        if path.is_file() and should_scan(path, media_root):
            items.append(path)
    return sorted(items)

def classify_context(path: Path, media_root: Path) -> str:
    parts = [part.casefold() for part in path.relative_to(media_root).parts]
    if parts and parts[0] == "movies":
        return "movie"
    if parts and parts[0] == "tv":
        return "tv"
    if path.suffix.casefold() in MEDIA_EXTENSIONS:
        return "tv"
    return "support"

def build_context(repo: Path, media_root: Path) -> RunContext:
    save_reference(repo)
    ref = load_reference(repo)
    timestamp = now_stamp()
    report_dir = repo / "reports" / "media_renamer" / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    return RunContext(repo=repo, media_root=media_root, timestamp=timestamp, report_dir=report_dir, ref=ref)

def latest_plan_dir(repo: Path) -> Path:
    reports = repo / "reports" / "media_renamer"
    candidates = [p for p in reports.iterdir() if p.is_dir() and (p / "scan_plan.json").exists()]
    if not candidates:
        raise FileNotFoundError("No cleanup plan found. Run plan first.")
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]

def load_plan(repo: Path, media_root: Path) -> tuple[RunContext, list[PlanRow], Path]:
    plan_dir = latest_plan_dir(repo)
    payload = json.loads((plan_dir / "scan_plan.json").read_text(encoding="utf-8"))
    ctx = build_context(repo, media_root)
    ctx.report_dir = plan_dir
    rows = [PlanRow(**row) for row in payload.get("rows", [])]
    return ctx, rows, plan_dir

def plan(ctx: RunContext) -> None:
    for path in all_files(ctx.media_root):
        if path.name in {"dir_listing.txt", ".tivimate_index"}:
            ctx.rows.append(PlanRow("skip", "support", str(path), "", "support", "", None, None, None, 0, "listing/index support file"))
            continue
        validation = validate_media(path)
        if is_media(path):
            if validation.valid is False and validation.reason in {"zero-byte", "temporary recording"}:
                dest = ctx.media_root / "_MediaRenamer_Quarantine" / ctx.timestamp / path.relative_to(ctx.media_root)
                ctx.rows.append(PlanRow("quarantine", "ready", str(path), str(dest), "broken", "", None, None, None, 100, validation.reason))
                continue
            context = classify_context(path, ctx.media_root)
            match = match_movie(path, ctx.ref) if context == "movie" else match_tv(path, ctx.ref)
            if match.kind == "tv" and match.tmdb_id and match.season and match.episode:
                show = ctx.ref.shows[match.tmdb_id]
                dest = tv_destination(ctx.media_root, show, match.season, match.episode, match.episode_name, path.suffix)
                status = "ready" if match.confidence >= SAFE_CONFIDENCE else "problem"
                action = "move_tv" if status == "ready" else "review"
                if dest.resolve() == path.resolve():
                    status = "ok"
                    action = "already_ok"
                ctx.rows.append(PlanRow(action, status, str(path), str(dest), "tv", match.title, match.tmdb_id, match.season, match.episode, match.confidence, match.reason))
            elif match.kind == "movie" and match.tmdb_id:
                dest = movie_destination(ctx.media_root, match.title, match.year, match.tmdb_id, path.suffix or ".mp4")
                status = "ready" if match.confidence >= SAFE_CONFIDENCE else "problem"
                action = "move_movie" if status == "ready" else "review"
                if dest.resolve() == path.resolve():
                    status = "ok"
                    action = "already_ok"
                ctx.rows.append(PlanRow(action, status, str(path), str(dest), "movie", match.title, match.tmdb_id, None, None, match.confidence, match.reason))
            else:
                review_dest = ctx.media_root / "_MediaRenamer_Review" / ctx.timestamp / path.relative_to(ctx.media_root)
                ctx.rows.append(PlanRow("review_relocate", "ready", str(path), str(review_dest), "unknown", match.title, match.tmdb_id, match.season, match.episode, match.confidence, match.reason))
        elif is_sidecar(path):
            match = match_tv(path, ctx.ref)
            if match.kind == "tv" and match.tmdb_id and match.season and match.episode and match.confidence >= SAFE_CONFIDENCE:
                show = ctx.ref.shows[match.tmdb_id]
                dest = tv_destination(ctx.media_root, show, match.season, match.episode, match.episode_name, path.suffix)
                action = "move_sidecar"
                status = "ok" if dest.resolve() == path.resolve() else "ready"
                ctx.rows.append(PlanRow(action, status, str(path), str(dest), "sidecar", match.title, match.tmdb_id, match.season, match.episode, match.confidence, match.reason))
            else:
                ctx.rows.append(PlanRow("skip", "support", str(path), "", "sidecar", "", None, None, None, 0, "unlinked sidecar"))
        else:
            ctx.rows.append(PlanRow("skip", "support", str(path), "", "support", "", None, None, None, 0, "support file"))
    dedupe_plan(ctx)
    audit_library(ctx)
    write_plan_reports(ctx)

def identity(row: PlanRow) -> tuple[str, int | None, int | None, int | None]:
    return (row.kind, row.tmdb_id, row.season, row.episode)

def source_size(row: PlanRow) -> int:
    try:
        return Path(row.source).stat().st_size
    except OSError:
        return -1

def dedupe_plan(ctx: RunContext) -> None:
    groups: dict[tuple[str, int | None, int | None, int | None], list[PlanRow]] = {}
    for row in ctx.rows:
        if row.status in {"ready", "ok"} and row.kind in {"tv", "movie"}:
            groups.setdefault(identity(row), []).append(row)
    for group_rows in groups.values():
        if len(group_rows) < 2:
            continue
        winner = sorted(group_rows, key=lambda row: (row.status == "ok", source_size(row), row.confidence), reverse=True)[0]
        for row in group_rows:
            if row is winner:
                continue
            source = Path(row.source)
            row.action = "duplicate"
            row.status = "ready"
            row.destination = str(ctx.media_root / "_MediaRenamer_Duplicates" / ctx.timestamp / source.relative_to(ctx.media_root))
            row.reason = f"duplicate loser; kept {winner.destination or winner.source}"

def execute_move(ctx: RunContext, row: PlanRow) -> None:
    source = Path(row.source)
    destination = Path(row.destination)
    entry = {"timestamp": iso_now(), **asdict(row), "result": "pending", "error": ""}
    try:
        if not source.exists():
            entry["result"] = "source_missing"
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and destination.resolve() != source.resolve():
                duplicate_dest = ctx.media_root / "_MediaRenamer_Duplicates" / ctx.timestamp / source.relative_to(ctx.media_root)
                duplicate_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(unique_path(duplicate_dest)))
                entry["result"] = "destination_exists_moved_to_duplicates"
                entry["destination"] = str(duplicate_dest)
            elif destination.resolve() != source.resolve():
                shutil.move(str(source), str(destination))
                entry["result"] = "moved"
            else:
                entry["result"] = "already_ok"
    except Exception as exc:
        entry["result"] = "error"
        entry["error"] = str(exc)
    ctx.execution_log.append(entry)

def unique_path(path: Path) -> Path:
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

def apply(ctx: RunContext, rows: list[PlanRow]) -> None:
    for row in rows:
        if row.status == "ready" and row.action in {"move_tv", "move_movie", "quarantine", "duplicate", "move_sidecar", "review_relocate"}:
            execute_move(ctx, row)
    normalize_movies_folder(ctx)
    normalize_live_tv_library(ctx)
    remove_empty_dirs(ctx.media_root / "TV")
    remove_empty_dirs(ctx.media_root / "Movies")
    audit_library(ctx)
    write_apply_reports(ctx)

def normalize_movies_folder(ctx: RunContext) -> None:
    lower = ctx.media_root / "movies"
    proper = ctx.media_root / "Movies"
    if lower.exists() and lower.resolve() != proper.resolve():
        proper.mkdir(exist_ok=True)
        for item in sorted(lower.iterdir()):
            dest = proper / item.name
            if dest.exists():
                dup = ctx.media_root / "_MediaRenamer_Duplicates" / ctx.timestamp / "movies" / item.name
                dup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(unique_path(dup)))
            else:
                shutil.move(str(item), str(dest))
        try:
            lower.rmdir()
        except OSError:
            pass

def folder_tmdb(path: Path) -> int | None:
    match = re.search(r"\[(\d{2,})\]", path.name)
    return int(match.group(1)) if match else None

def canonical_show_folder(ctx: RunContext, tmdb_id: int) -> Path:
    show = ctx.ref.shows.get(tmdb_id)
    if not show:
        return ctx.media_root / "TV" / f"Unknown [{tmdb_id}]"
    return ctx.media_root / "TV" / f"{safe_name(show.title)} [{tmdb_id}]"

def normalize_live_tv_library(ctx: RunContext) -> None:
    tv = ctx.media_root / "TV"
    if not tv.exists():
        return
    # Merge duplicate same-TMDb folders into canonical repo-catalog title.
    for child in sorted([p for p in tv.iterdir() if p.is_dir()]):
        if child.name in HOUSEKEEPING or child.name == "_Unsorted":
            continue
        tmdb = folder_tmdb(child)
        if tmdb:
            canonical = canonical_show_folder(ctx, tmdb)
            if child.resolve() != canonical.resolve():
                merge_directory(child, canonical, ctx)
    # Collapse generic season-name duplicates.
    for show_folder in sorted([p for p in tv.iterdir() if p.is_dir() and folder_tmdb(p)]):
        collapse_generic_seasons(show_folder, ctx)
    # Merge same visible title with different ID when there is overlap or one is mostly generic duplicate.
    merge_duplicate_visible_titles(tv, ctx)
    # Relocate leftover legacy folders out of live TV.
    for child in sorted([p for p in tv.iterdir() if p.is_dir()]):
        if child.name in HOUSEKEEPING or child.name == "_Unsorted":
            continue
        if folder_tmdb(child) is None:
            if contains_media_or_sidecar(child):
                review = ctx.media_root / "_MediaRenamer_Review" / ctx.timestamp / "legacy_tv_folders" / child.name
                merge_directory(child, review, ctx)
            else:
                review = ctx.media_root / "_MediaRenamer_Review" / ctx.timestamp / "legacy_support_folders" / child.name
                merge_directory(child, review, ctx)
    unsorted = tv / "_Unsorted"
    if unsorted.exists() and not contains_media_or_sidecar(unsorted):
        remove_empty_dirs(unsorted)
        try:
            unsorted.rmdir()
        except OSError:
            pass

def merge_duplicate_visible_titles(tv: Path, ctx: RunContext) -> None:
    groups: dict[str, list[Path]] = {}
    for child in tv.iterdir():
        if not child.is_dir() or folder_tmdb(child) is None:
            continue
        visible = re.sub(r"\s*\[\d+\]$", "", child.name)
        groups.setdefault(normalize_key(visible), []).append(child)
    for folders in groups.values():
        if len(folders) < 2:
            continue
        # Prefer folder with most files, then TMDb ID present in more normalized names.
        target = sorted(folders, key=lambda p: count_files(p), reverse=True)[0]
        for source in folders:
            if source == target:
                continue
            merge_directory(source, target, ctx)

def count_files(path: Path) -> int:
    return sum(1 for p in path.rglob("*") if p.is_file())

def collapse_generic_seasons(show_folder: Path, ctx: RunContext) -> None:
    season_dirs = [p for p in show_folder.iterdir() if p.is_dir() and p.name.casefold().startswith("season ")]
    for season_dir in season_dirs:
        match = re.match(r"Season\s+(\d{1,4})\s+-\s+(.+)$", season_dir.name, re.IGNORECASE)
        if not match:
            continue
        season_no = int(match.group(1))
        suffix = normalize_key(match.group(2))
        base_name = f"Season {season_no:02d}" if season_no < 100 else f"Season {season_no}"
        if suffix in GENERIC_SEASON_SUFFIXES or suffix == normalize_key(base_name):
            merge_directory(season_dir, show_folder / base_name, ctx)

def merge_directory(source: Path, target: Path, ctx: RunContext) -> None:
    if not source.exists() or source.resolve() == target.resolve():
        return
    for item in sorted(source.rglob("*"), key=lambda p: len(p.parts)):
        if not item.is_file():
            continue
        rel = item.relative_to(source)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dup = ctx.media_root / "_MediaRenamer_Duplicates" / ctx.timestamp / item.relative_to(ctx.media_root)
            dup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(unique_path(dup)))
            ctx.execution_log.append({"timestamp": iso_now(), "action": "merge_duplicate_file", "source": str(item), "destination": str(dup), "result": "moved_to_duplicates"})
        else:
            shutil.move(str(item), str(dest))
            ctx.execution_log.append({"timestamp": iso_now(), "action": "merge_folder_file", "source": str(item), "destination": str(dest), "result": "moved"})
    remove_empty_dirs(source)
    try:
        source.rmdir()
    except OSError:
        pass

def contains_media_or_sidecar(folder: Path) -> bool:
    return any((p.suffix.casefold() in MEDIA_EXTENSIONS or p.suffix.casefold() in SIDECAR_EXTENSIONS) for p in folder.rglob("*") if p.is_file())

def remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted([p for p in root.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass

def has_exact_child(parent: Path, child_name: str) -> bool:
    if not parent.exists():
        return False
    return any(child.name == child_name for child in parent.iterdir())

def audit_library(ctx: RunContext) -> None:
    ctx.audit_gaps.clear()
    root_allowed_files = {".tivimate_index", "dir_listing.txt"}
    for item in ctx.media_root.iterdir():
        if item.is_file() and item.name not in root_allowed_files and item.suffix.casefold() in MEDIA_EXTENSIONS:
            ctx.audit_gaps.append(AuditGap("root_media", str(item), "media file remains in parent root"))
    if has_exact_child(ctx.media_root, "movies"):
        ctx.audit_gaps.append(AuditGap("movies_casing", str(ctx.media_root / "movies"), "lowercase movies folder remains; expected Movies"))
    if has_exact_child(ctx.media_root, "Shows"):
        ctx.audit_gaps.append(AuditGap("forbidden_folder", str(ctx.media_root / "Shows"), "Shows folder is forbidden"))
    tv = ctx.media_root / "TV"
    if tv.exists():
        seen_tmdb: dict[int, Path] = {}
        seen_visible: dict[str, Path] = {}
        for child in sorted([p for p in tv.iterdir() if p.is_dir()]):
            if child.name in HOUSEKEEPING:
                ctx.audit_gaps.append(AuditGap("housekeeping_in_tv", str(child), "housekeeping folder must be under parent root"))
                continue
            if child.name in {"ShowA", "ShowB"}:
                ctx.audit_gaps.append(AuditGap("placeholder_folder", str(child), "placeholder folder remains in live TV"))
            if child.name == "_Unsorted" and contains_media_or_sidecar(child):
                ctx.audit_gaps.append(AuditGap("unsorted_media", str(child), "_Unsorted still contains media/sidecar files"))
            tmdb = folder_tmdb(child)
            if tmdb is None and child.name != "_Unsorted" and contains_media_or_sidecar(child):
                ctx.audit_gaps.append(AuditGap("legacy_tv_folder", str(child), "non-normalized TV folder contains media/sidecar files"))
            if tmdb is not None:
                if tmdb in seen_tmdb:
                    ctx.audit_gaps.append(AuditGap("duplicate_tmdb_folder", str(child), f"same TMDb ID as {seen_tmdb[tmdb]}"))
                seen_tmdb[tmdb] = child
                visible = normalize_key(re.sub(r"\s*\[\d+\]$", "", child.name))
                if visible in seen_visible:
                    ctx.audit_gaps.append(AuditGap("duplicate_visible_title", str(child), f"same visible title as {seen_visible[visible]}"))
                seen_visible[visible] = child
            for season_dir in [p for p in child.iterdir() if p.is_dir() and p.name.casefold().startswith("season ")]:
                match = re.match(r"Season\s+(\d{1,4})\s+-\s+(.+)$", season_dir.name, re.IGNORECASE)
                if match:
                    suffix = normalize_key(match.group(2))
                    if suffix in GENERIC_SEASON_SUFFIXES:
                        ctx.audit_gaps.append(AuditGap("generic_duplicate_season", str(season_dir), "generic season-name suffix should be collapsed"))

def summary(ctx: RunContext) -> dict[str, int]:
    return {
        "ready_to_fix": sum(1 for row in ctx.rows if row.status == "ready"),
        "already_ok": sum(1 for row in ctx.rows if row.status == "ok"),
        "move_to_tv": sum(1 for row in ctx.rows if row.action == "move_tv" and row.status == "ready"),
        "move_to_movies": sum(1 for row in ctx.rows if row.action == "move_movie" and row.status == "ready"),
        "duplicates_to_move": sum(1 for row in ctx.rows if row.action == "duplicate" and row.status == "ready"),
        "broken_to_quarantine": sum(1 for row in ctx.rows if row.action == "quarantine" and row.status == "ready"),
        "review_relocate": sum(1 for row in ctx.rows if row.action == "review_relocate" and row.status == "ready"),
        "problem_files_left_alone": sum(1 for row in ctx.rows if row.status == "problem"),
        "skipped_support_files": sum(1 for row in ctx.rows if row.status == "support"),
        "acceptance_gaps": len(ctx.audit_gaps),
    }

def write_plan_reports(ctx: RunContext) -> None:
    data = {"version": VERSION, "timestamp": ctx.timestamp, "summary": summary(ctx), "rows": [asdict(row) for row in ctx.rows], "audit_gaps": [asdict(gap) for gap in ctx.audit_gaps]}
    (ctx.report_dir / "scan_plan.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(ctx.report_dir / "scan_plan.csv", [asdict(row) for row in ctx.rows])
    write_csv(ctx.report_dir / "problem_files.csv", [asdict(row) for row in ctx.rows if row.status == "problem"])
    write_csv(ctx.report_dir / "acceptance_gaps.csv", [asdict(gap) for gap in ctx.audit_gaps])
    html = render_summary_html("Cleanup Plan", data)
    (ctx.report_dir / "summary.html").write_text(html, encoding="utf-8")
    (ctx.report_dir / "acceptance_report.html").write_text(render_acceptance_html(ctx), encoding="utf-8")
    (ctx.report_dir / "acceptance_report.json").write_text(json.dumps([asdict(gap) for gap in ctx.audit_gaps], indent=2), encoding="utf-8")
    (ctx.report_dir / "execution_preview.log.txt").write_text("Plan only. No files changed.\n", encoding="utf-8")
    zip_report_dir(ctx.report_dir)
    print(json.dumps({"summary": summary(ctx), "report_dir": str(ctx.report_dir)}, indent=2))

def write_apply_reports(ctx: RunContext) -> None:
    payload = {"version": VERSION, "timestamp": ctx.timestamp, "execution_log": ctx.execution_log, "audit_gaps": [asdict(gap) for gap in ctx.audit_gaps]}
    (ctx.report_dir / "execution_log.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (ctx.report_dir / "execution.log.txt").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in ctx.execution_log), encoding="utf-8")
    (ctx.report_dir / "post_apply_summary.html").write_text(render_apply_html(ctx), encoding="utf-8")
    (ctx.report_dir / "acceptance_report.html").write_text(render_acceptance_html(ctx), encoding="utf-8")
    (ctx.report_dir / "acceptance_report.json").write_text(json.dumps([asdict(gap) for gap in ctx.audit_gaps], indent=2), encoding="utf-8")
    zip_report_dir(ctx.report_dir)
    print(json.dumps({"plan_dir": str(ctx.report_dir), "summary": {"executed": len(ctx.execution_log), "errors": sum(1 for row in ctx.execution_log if row.get("result") == "error"), "acceptance_gaps": len(ctx.audit_gaps)}}, indent=2))

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row.keys()}) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def render_summary_html(title: str, data: dict[str, Any]) -> str:
    rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in data["summary"].items())
    problems = "".join(f"<tr><td>{row['status']}</td><td>{row['action']}</td><td>{row['source']}</td><td>{row['reason']}</td></tr>" for row in data["rows"] if row["status"] in {"problem", "ready"})
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#eee}}</style></head><body><h1>{title}</h1><table>{rows}</table><h2>Action/problem rows</h2><table><tr><th>Status</th><th>Action</th><th>Source</th><th>Reason</th></tr>{problems}</table></body></html>"""

def render_acceptance_html(ctx: RunContext) -> str:
    status = "PASS" if not ctx.audit_gaps else "FAIL"
    gap_rows = "".join(f"<tr><td>{gap.category}</td><td>{gap.path}</td><td>{gap.detail}</td></tr>" for gap in ctx.audit_gaps)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Media Cleanup Acceptance Report</title><style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px}}.fail{{color:#9b1c1c;font-weight:700}}.pass{{color:#166534;font-weight:700}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#eee}}</style></head><body><h1>Media Cleanup Acceptance Report</h1><p>Status: <span class='{status.lower()}'>{status}</span></p><p>Gap count: {len(ctx.audit_gaps)}</p><table><tr><th>Category</th><th>Path</th><th>Detail</th></tr>{gap_rows}</table></body></html>"""

def render_apply_html(ctx: RunContext) -> str:
    rows = "".join(f"<tr><td>{item.get('result')}</td><td>{item.get('action')}</td><td>{item.get('source')}</td><td>{item.get('destination')}</td><td>{item.get('error')}</td></tr>" for item in ctx.execution_log)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Cleanup Apply Summary</title><style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#eee}}</style></head><body><h1>Cleanup Apply Summary</h1><table><tr><th>Result</th><th>Action</th><th>Source</th><th>Destination</th><th>Error</th></tr>{rows}</table></body></html>"""

def zip_report_dir(report_dir: Path) -> None:
    zip_path = report_dir.with_suffix(".zip")
    shutil.make_archive(str(report_dir), "zip", report_dir)

def main() -> int:
    parser = argparse.ArgumentParser(description="Media cleanup pipeline")
    parser.add_argument("mode", choices=["plan", "apply"])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--media-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo)
    media_root = Path(args.media_root)
    if args.mode == "plan":
        ctx = build_context(repo, media_root)
        plan(ctx)
    else:
        ctx, rows, _plan_dir = load_plan(repo, media_root)
        apply(ctx, rows)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
