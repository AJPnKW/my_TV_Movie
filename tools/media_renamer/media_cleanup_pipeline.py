# FILE: tools/media_renamer/media_cleanup_pipeline.py
# VERSION: v0.4.0
# CAPABILITY: media_cleanup_two_step_pipeline=YES
# CHANGE NOTES:
# - Replaces the complex review utility with a two-step pipeline: plan, apply.
# - Enforces TV and Movies only; never creates a Shows output folder.
# - Processes loose root files, TV/_Unsorted, movies/Movies, ShowA, ShowB, and prior accidental Shows folder.

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.media_renamer.media_catalog_builder import load_or_build_media_reference
    from tools.media_renamer.media_matcher import match_media, representative_parse_results, safe_text
    from tools.media_renamer.media_validator import find_ffprobe, validate_media_file
else:
    from .media_catalog_builder import load_or_build_media_reference
    from .media_matcher import match_media, representative_parse_results, safe_text
    from .media_validator import find_ffprobe, validate_media_file


PIPELINE_VERSION = "v0.4.0"
RULES_SCHEMA = "media_cleanup.rules.v1"
PLAN_SCHEMA = "media_cleanup.plan.v1"
DEFAULT_MEDIA_ROOT = Path(r"C:\X1_Share\Recordings")
SAFE_DESTINATION_FOLDERS = {"TV", "Movies"}


def utc_now_text() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_text() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def load_rules(repo_root: Path) -> dict[str, Any]:
    rules_path = repo_root / "tools" / "media_renamer" / "media_rules.json"
    with rules_path.open("r", encoding="utf-8") as handle:
        rules = json.load(handle)
    if rules.get("schema") != RULES_SCHEMA:
        raise ValueError(f"Unsupported rules schema in {rules_path}")
    return rules


def normalize_folder_name(value: object) -> str:
    return safe_text(value).lower().strip()


def is_skip_dir(path: Path, rules: dict[str, Any]) -> bool:
    name = normalize_folder_name(path.name)
    always_include = {normalize_folder_name(item) for item in rules.get("always_include_folders", [])}
    if name in always_include:
        return False
    if name == "shows":
        return False
    skip_exact = {normalize_folder_name(item) for item in rules.get("skip_folders", [])}
    if name in skip_exact:
        return True
    if name.startswith(".venv"):
        return True
    return False


def is_media_candidate(path: Path, rules: dict[str, Any], media_root: Path) -> bool:
    extension = path.suffix.lower()
    if extension in {item.lower() for item in rules.get("media_extensions", [])}:
        return True
    if extension:
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    min_size = int(rules.get("extensionless_min_size_bytes", 10_000_000))
    if size < min_size:
        return False
    relative_parts = {normalize_folder_name(part) for part in path.relative_to(media_root).parts[:-1]}
    return bool(relative_parts & {"movies", "movie", "tv"})


def scan_candidate_files(media_root: Path, rules: dict[str, Any]) -> tuple[list[Path], int]:
    candidates: list[Path] = []
    skipped_support_files = 0
    for current_root, dir_names, file_names in os.walk(media_root):
        current_path = Path(current_root)
        dir_names[:] = [name for name in dir_names if not is_skip_dir(current_path / name, rules)]
        for file_name in file_names:
            file_path = current_path / file_name
            if is_media_candidate(file_path, rules, media_root):
                candidates.append(file_path)
            else:
                skipped_support_files += 1
    return candidates, skipped_support_files


@dataclass
class PlanRow:
    row_id: int
    status: str
    action: str
    media_type: str
    source_path: str
    original_filename: str
    destination_path: str
    matched_title: str = ""
    tmdb_id: int = 0
    season_number: int = 0
    episode_number: int = 0
    confidence: int = 0
    reason: str = ""
    validation_status: str = ""
    validation_reason: str = ""
    size_bytes: int = 0
    identity_key: str = ""
    safe_to_apply: bool = False
    result: str = "planned"
    error: str = ""


@dataclass
class CleanupPlan:
    meta: dict[str, Any]
    summary: dict[str, int]
    rows: list[PlanRow] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta,
            "summary": self.summary,
            "rows": [asdict(row) for row in self.rows],
        }


def _destination_is_safe(destination_path: str, media_root: Path) -> bool:
    if not destination_path:
        return False
    destination = Path(destination_path)
    try:
        relative = destination.resolve().relative_to(media_root.resolve())
    except ValueError:
        return False
    parts = relative.parts
    if not parts:
        return False
    return parts[0] in SAFE_DESTINATION_FOLDERS and "Shows" not in parts


def _quarantine_destination(media_root: Path, source: Path, run_timestamp: str) -> Path:
    safe_name = source.name
    try:
        rel_parent = source.parent.relative_to(media_root)
    except ValueError:
        rel_parent = Path("external")
    return media_root / "_MediaRenamer_Quarantine" / run_timestamp / rel_parent / safe_name


def _duplicate_destination(media_root: Path, source: Path, run_timestamp: str) -> Path:
    safe_name = source.name
    try:
        rel_parent = source.parent.relative_to(media_root)
    except ValueError:
        rel_parent = Path("external")
    return media_root / "_MediaRenamer_Duplicates" / run_timestamp / rel_parent / safe_name


def _make_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _choose_duplicate_keep(rows: list[PlanRow]) -> PlanRow:
    def quality(row: PlanRow) -> tuple[int, int, int]:
        validation_rank = {"valid": 3, "unknown": 2, "problem": 1, "partial": 0, "broken": -1}.get(row.validation_status, 0)
        already_ok_rank = 1 if row.action == "already_ok" else 0
        return (validation_rank, row.size_bytes, already_ok_rank)
    return sorted(rows, key=quality, reverse=True)[0]


def _apply_duplicate_rules(rows: list[PlanRow], media_root: Path, run_timestamp: str) -> None:
    grouped: dict[str, list[PlanRow]] = {}
    for row in rows:
        if row.status == "safe" and row.identity_key and row.action in {"move_tv", "move_movie", "already_ok"}:
            grouped.setdefault(row.identity_key, []).append(row)
    for identity_rows in grouped.values():
        if len(identity_rows) < 2:
            continue
        keep = _choose_duplicate_keep(identity_rows)
        for row in identity_rows:
            if row is keep:
                row.reason = f"duplicate group keep; {row.reason}"
                continue
            source = Path(row.source_path)
            row.action = "move_duplicate"
            row.media_type = row.media_type or "duplicate"
            row.destination_path = str(_make_unique_path(_duplicate_destination(media_root, source, run_timestamp)))
            row.reason = f"duplicate loser; keeping {Path(keep.source_path).name}"
            row.safe_to_apply = True


def _row_from_source(row_id: int, source: Path, media_root: Path, reference: dict[str, Any], rules: dict[str, Any], validation_map: dict[str, Any], run_timestamp: str) -> PlanRow:
    validation = validation_map[str(source)]
    min_confidence = int(rules.get("min_confidence", 85))
    if validation.status in {"broken", "partial"}:
        return PlanRow(
            row_id=row_id,
            status="safe",
            action="quarantine",
            media_type="broken",
            source_path=str(source),
            original_filename=source.name,
            destination_path=str(_make_unique_path(_quarantine_destination(media_root, source, run_timestamp))),
            reason=validation.reason,
            validation_status=validation.status,
            validation_reason=validation.reason,
            size_bytes=validation.size_bytes,
            safe_to_apply=True,
        )
    match = match_media(source, media_root, reference, min_confidence)
    destination_safe = _destination_is_safe(match.destination_path, media_root) if match.destination_path else False
    safe_to_apply = match.status == "safe" and match.action != "review" and (destination_safe or match.action == "already_ok")
    return PlanRow(
        row_id=row_id,
        status="safe" if safe_to_apply or match.action == "already_ok" else "problem",
        action=match.action if safe_to_apply or match.action == "already_ok" else "review",
        media_type=match.media_type,
        source_path=str(source),
        original_filename=source.name,
        destination_path=match.destination_path,
        matched_title=match.title,
        tmdb_id=match.tmdb_id,
        season_number=match.season_number,
        episode_number=match.episode_number,
        confidence=match.confidence,
        reason=match.reason if destination_safe or match.action == "already_ok" else f"unsafe destination or no destination; {match.reason}",
        validation_status=validation.status,
        validation_reason=validation.reason,
        size_bytes=validation.size_bytes,
        identity_key=match.identity_key,
        safe_to_apply=safe_to_apply,
    )


def _summary(rows: list[PlanRow], skipped_support_files: int) -> dict[str, int]:
    summary = {
        "ready_to_fix": 0,
        "already_ok": 0,
        "move_to_tv": 0,
        "move_to_movies": 0,
        "duplicates_to_move": 0,
        "broken_to_quarantine": 0,
        "problem_files_left_alone": 0,
        "skipped_support_files": skipped_support_files,
    }
    for row in rows:
        if row.action == "already_ok":
            summary["already_ok"] += 1
        elif row.action == "move_tv":
            summary["ready_to_fix"] += 1
            summary["move_to_tv"] += 1
        elif row.action == "move_movie":
            summary["ready_to_fix"] += 1
            summary["move_to_movies"] += 1
        elif row.action == "move_duplicate":
            summary["ready_to_fix"] += 1
            summary["duplicates_to_move"] += 1
        elif row.action == "quarantine":
            summary["ready_to_fix"] += 1
            summary["broken_to_quarantine"] += 1
        elif row.status == "problem":
            summary["problem_files_left_alone"] += 1
    return summary


def _write_csv(rows: list[PlanRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(PlanRow(0, "", "", "", "", "", "").__dict__.keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _html_escape(value: object) -> str:
    text = safe_text(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _write_summary_html(plan: CleanupPlan, path: Path, title: str = "Media Cleanup Plan") -> None:
    rows = plan.rows
    problem_rows = [row for row in rows if row.status == "problem"][:200]
    summary_cards = "".join(
        f"<div class='card'><div class='num'>{value}</div><div>{_html_escape(key.replace('_', ' ').title())}</div></div>"
        for key, value in plan.summary.items()
    )
    problem_table_rows = "".join(
        "<tr>"
        f"<td>{_html_escape(row.original_filename)}</td>"
        f"<td>{_html_escape(row.reason)}</td>"
        f"<td>{row.confidence}</td>"
        f"<td>{_html_escape(row.source_path)}</td>"
        "</tr>"
        for row in problem_rows
    )
    safe_preview_rows = "".join(
        "<tr>"
        f"<td>{_html_escape(row.action)}</td>"
        f"<td>{_html_escape(row.original_filename)}</td>"
        f"<td>{_html_escape(row.matched_title)}</td>"
        f"<td>{row.confidence}</td>"
        f"<td>{_html_escape(row.destination_path)}</td>"
        "</tr>"
        for row in [item for item in rows if item.safe_to_apply][:200]
    )
    html = f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<title>{_html_escape(title)}</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f7f9; color: #1f2937; }}
h1 {{ margin-bottom: 6px; }}
.notice {{ padding: 14px 16px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 12px; margin: 16px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 18px 0; }}
.card {{ background: #fff; border: 1px solid #d1d5db; border-radius: 14px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,.04); }}
.num {{ font-size: 28px; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; margin: 12px 0 28px; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #e5e7eb; }}
code {{ background: #e5e7eb; padding: 2px 5px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>{_html_escape(title)}</h1>
<p>Generated: {_html_escape(plan.meta.get('generated_utc'))}</p>
<div class='notice'>Safe matches are planned automatically. Problem files are left alone.</div>
<div class='grid'>{summary_cards}</div>
<h2>Safe Actions Preview</h2>
<table><thead><tr><th>Action</th><th>Original File</th><th>Matched Title</th><th>Confidence</th><th>Destination</th></tr></thead><tbody>{safe_preview_rows}</tbody></table>
<h2>Problem Files Left Alone</h2>
<table><thead><tr><th>Original File</th><th>Reason</th><th>Confidence</th><th>Source</th></tr></thead><tbody>{problem_table_rows}</tbody></table>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")


def _zip_report(report_dir: Path) -> Path:
    zip_path = report_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in report_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(report_dir.parent))
    return zip_path


def _latest_plan_dir(repo_root: Path) -> Path:
    reports_root = repo_root / "reports" / "media_renamer"
    candidates = [path for path in reports_root.iterdir() if path.is_dir() and (path / "scan_plan.json").exists()] if reports_root.exists() else []
    if not candidates:
        raise FileNotFoundError("No cleanup plan found. Run Build Cleanup Plan first.")
    return sorted(candidates, key=lambda item: item.name)[-1]


def build_cleanup_plan(repo_root: Path, media_root: Path, force_reference: bool = True) -> CleanupPlan:
    repo_root = repo_root.resolve()
    media_root = media_root.resolve()
    if not media_root.exists():
        raise FileNotFoundError(f"Media root not found: {media_root}")
    run_timestamp = timestamp_text()
    rules = load_rules(repo_root)
    reference = load_or_build_media_reference(repo_root, force=force_reference)
    candidates, skipped_support_files = scan_candidate_files(media_root, rules)
    ffprobe_path = find_ffprobe()
    validation_map: dict[str, Any] = {}
    max_workers = max(1, int(rules.get("max_validation_workers", 4)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(validate_media_file, path, ffprobe_path): path for path in candidates}
        for future in as_completed(futures):
            path = futures[future]
            validation_map[str(path)] = future.result()
    rows = [
        _row_from_source(index + 1, source, media_root, reference, rules, validation_map, run_timestamp)
        for index, source in enumerate(sorted(candidates, key=lambda item: str(item).lower()))
    ]
    _apply_duplicate_rules(rows, media_root, run_timestamp)
    summary = _summary(rows, skipped_support_files)
    report_dir = repo_root / "reports" / "media_renamer" / run_timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    plan = CleanupPlan(
        meta={
            "schema": PLAN_SCHEMA,
            "pipeline_version": PIPELINE_VERSION,
            "generated_utc": utc_now_text(),
            "repo_root": str(repo_root),
            "media_root": str(media_root),
            "report_dir": str(report_dir),
            "ffprobe_available": bool(ffprobe_path),
            "candidate_file_count": len(candidates),
        },
        summary=summary,
        rows=rows,
    )
    (report_dir / "scan_plan.json").write_text(json.dumps(plan.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(rows, report_dir / "scan_plan.csv")
    _write_csv([row for row in rows if row.status == "problem"], report_dir / "problem_files.csv")
    _write_summary_html(plan, report_dir / "summary.html")
    preview_lines = [f"{row.action}: {row.source_path} -> {row.destination_path}" for row in rows if row.safe_to_apply]
    (report_dir / "execution_preview.log.txt").write_text("\n".join(preview_lines) + "\n", encoding="utf-8")
    _zip_report(report_dir)
    return plan


def _load_plan(plan_dir: Path) -> CleanupPlan:
    data = json.loads((plan_dir / "scan_plan.json").read_text(encoding="utf-8"))
    if data.get("meta", {}).get("schema") != PLAN_SCHEMA:
        raise ValueError(f"Unsupported cleanup plan schema: {plan_dir}")
    rows = [PlanRow(**row) for row in data.get("rows", [])]
    return CleanupPlan(meta=data.get("meta", {}), summary=data.get("summary", {}), rows=rows)


def _move_file(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    final_destination = _make_unique_path(destination) if destination.exists() and source.resolve() != destination.resolve() else destination
    if source.resolve() == final_destination.resolve():
        return "already_ok"
    shutil.move(str(source), str(final_destination))
    return str(final_destination)


def _remove_empty_cleanup_folders(media_root: Path, log_rows: list[dict[str, Any]]) -> None:
    protected = {media_root.resolve(), (media_root / "TV").resolve(), (media_root / "Movies").resolve()}
    for path in sorted(media_root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.is_dir() or path.resolve() in protected:
            continue
        if path.name in {"ShowA", "ShowB", "Shows", "_Unsorted"} or not any(path.iterdir()):
            try:
                path.rmdir()
                log_rows.append({"timestamp": utc_now_text(), "action": "remove_empty_folder", "source_path": str(path), "result": "removed"})
            except OSError:
                if path.name in {"ShowA", "ShowB", "Shows"}:
                    log_rows.append({"timestamp": utc_now_text(), "action": "remove_empty_folder", "source_path": str(path), "result": "not_empty"})


def apply_cleanup_plan(repo_root: Path, media_root: Path, plan_dir: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    media_root = media_root.resolve()
    selected_plan_dir = plan_dir or _latest_plan_dir(repo_root)
    plan = _load_plan(selected_plan_dir)
    if Path(plan.meta.get("media_root", "")).resolve() != media_root:
        raise ValueError("Plan media root does not match requested media root. Build a new cleanup plan first.")
    execution_rows: list[dict[str, Any]] = []
    for row in plan.rows:
        if not row.safe_to_apply:
            continue
        source = Path(row.source_path)
        destination = Path(row.destination_path)
        entry = asdict(row)
        entry["timestamp"] = utc_now_text()
        if not source.exists():
            entry["result"] = "source_missing"
            execution_rows.append(entry)
            continue
        if row.action == "already_ok":
            entry["result"] = "already_ok"
            execution_rows.append(entry)
            continue
        if row.action in {"move_tv", "move_movie", "move_duplicate", "quarantine"}:
            try:
                final_destination = _move_file(source, destination)
                entry["result"] = "moved"
                entry["actual_destination_path"] = final_destination
            except OSError as error:
                entry["result"] = "error"
                entry["error"] = str(error)
            execution_rows.append(entry)
    _remove_empty_cleanup_folders(media_root, execution_rows)
    result_summary = {
        "executed": sum(1 for row in execution_rows if row.get("result") in {"moved", "already_ok", "removed"}),
        "errors": sum(1 for row in execution_rows if row.get("result") == "error"),
        "source_missing": sum(1 for row in execution_rows if row.get("result") == "source_missing"),
        "log_count": len(execution_rows),
    }
    (selected_plan_dir / "execution_log.json").write_text(json.dumps({"summary": result_summary, "rows": execution_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    log_lines = [json.dumps(row, ensure_ascii=False) for row in execution_rows]
    (selected_plan_dir / "execution.log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    post_plan = CleanupPlan(meta={**plan.meta, "generated_utc": utc_now_text()}, summary=result_summary, rows=plan.rows)
    _write_summary_html(post_plan, selected_plan_dir / "post_apply_summary.html", title="Media Cleanup Apply Summary")
    _zip_report(selected_plan_dir)
    return {"plan_dir": str(selected_plan_dir), "summary": result_summary}


def run_self_test() -> dict[str, Any]:
    rows = representative_parse_results()
    expected = {
        "Abbott_Elementary_Safety_Day_S05E15.mp4": (5, 15),
        "CIA_(2026)_(2026)_S01E010.mp4": (1, 10),
        "Hacks__5x04.mp4": (5, 4),
        "Come_Dine_with_Me_(S2026E01).mp4": (2026, 1),
        "vsembed.ru_embed_tv_126027_5_16.mp4": (5, 16),
        "The_Hunting_Party_(S02E10.mp4": (2, 10),
        "Watson_(S02E20).a.mp4": (2, 20),
    }
    failures = []
    for row in rows:
        sample = row["sample"]
        if sample in expected:
            season, episode = expected[sample]
            if row["season_number"] != season or row["episode_number"] != episode:
                failures.append(row)
    if failures:
        raise AssertionError(f"Representative parse tests failed: {failures}")
    return {"status": "ok", "representative_parse_results": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Two-step media cleanup pipeline")
    parser.add_argument("mode", choices=["plan", "apply", "self-test"])
    parser.add_argument("--repo-root", default=str(repo_root_from_script()))
    parser.add_argument("--media-root", default=str(DEFAULT_MEDIA_ROOT))
    parser.add_argument("--plan-dir", default="")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    media_root = Path(args.media_root)
    if args.mode == "self-test":
        print(json.dumps(run_self_test(), indent=2))
        return 0
    if args.mode == "plan":
        plan = build_cleanup_plan(repo_root, media_root)
        print(json.dumps({"summary": plan.summary, "report_dir": plan.meta["report_dir"]}, indent=2))
        return 0
    plan_dir = Path(args.plan_dir) if args.plan_dir else None
    result = apply_cleanup_plan(repo_root, media_root, plan_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
