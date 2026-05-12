# FILE: tools/media_renamer/media_playback_qa.py
# VERSION: v0.6.8
# UPDATED: 2026-05-11
# CHANGE NOTES:
# - Scans all TV/Movie files with ffprobe.
# - Flags files that are likely to fail on Chromecast/Android/X-plore.
# - Repairs flagged files using safe remux first, transcode second, with original backup.
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "0.6.8"
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv"}
SAFE_VIDEO_CODECS = {"h264", "hevc", "h265"}
SAFE_AUDIO_CODECS = {"aac", "mp3", "ac3", "eac3"}


@dataclass
class QaRow:
    path: str
    relative_path: str
    status: str
    action: str
    container: str
    video_codec: str
    audio_codec: str
    duration: float
    size_mb: float
    reason: str
    repaired_path: str = ""
    backup_path: str = ""
    error: str = ""


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    return found


def iter_media(media_root: Path, title_filter: str = "") -> list[Path]:
    roots = [media_root / "TV", media_root / "Movies"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
                if title_filter and title_filter.lower() not in str(path).lower():
                    continue
                files.append(path)
    return sorted(files, key=lambda p: str(p).lower())


def run_json(command: list[str], timeout: int = 60) -> tuple[int, dict[str, Any], str]:
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        return completed.returncode, {}, (completed.stderr or completed.stdout or "").strip()
    try:
        return completed.returncode, json.loads(completed.stdout or "{}"), ""
    except json.JSONDecodeError as exc:
        return 9, {}, f"ffprobe json parse failed: {exc}"


def inspect_file(path: Path, media_root: Path, ffprobe: str | None) -> QaRow:
    size_mb = round(path.stat().st_size / 1024 / 1024, 1) if path.exists() else 0.0
    rel = path.relative_to(media_root).as_posix()
    if size_mb <= 0:
        return QaRow(str(path), rel, "repair_needed", "repair", path.suffix.lower(), "", "", 0.0, size_mb, "zero-byte or missing file")
    if not ffprobe:
        return QaRow(str(path), rel, "unknown", "none", path.suffix.lower(), "", "", 0.0, size_mb, "ffprobe not found")
    code, data, error = run_json([
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ])
    if code != 0:
        return QaRow(str(path), rel, "repair_needed", "repair", path.suffix.lower(), "", "", 0.0, size_mb, f"ffprobe failed: {error}")
    streams = data.get("streams", []) or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    video_codec = str(video.get("codec_name") or "")
    audio_codec = str(audio.get("codec_name") or "")
    duration_text = str((data.get("format") or {}).get("duration") or "0")
    try:
        duration = float(duration_text)
    except ValueError:
        duration = 0.0
    container = str((data.get("format") or {}).get("format_name") or path.suffix.lower())
    reasons: list[str] = []
    if not video_codec:
        reasons.append("missing video stream")
    if duration <= 0:
        reasons.append("missing/zero duration")
    if path.suffix.lower() != ".mp4":
        reasons.append("not mp4 container")
    if video_codec and video_codec not in SAFE_VIDEO_CODECS:
        reasons.append(f"video codec {video_codec} may not be TV-safe")
    if audio_codec and audio_codec not in SAFE_AUDIO_CODECS:
        reasons.append(f"audio codec {audio_codec} may not be TV-safe")
    if reasons:
        return QaRow(str(path), rel, "repair_needed", "repair", container, video_codec, audio_codec, duration, size_mb, "; ".join(reasons))
    return QaRow(str(path), rel, "ok", "none", container, video_codec, audio_codec, duration, size_mb, "ffprobe passed and file is TV-safe enough")


def repair_file(row: QaRow, media_root: Path, backup_root: Path, ffmpeg: str | None, ffprobe: str | None) -> QaRow:
    if row.status != "repair_needed":
        return row
    source = Path(row.path)
    if not ffmpeg:
        row.status = "repair_skipped"
        row.action = "none"
        row.error = "ffmpeg not found"
        return row
    if not source.exists():
        row.status = "repair_failed"
        row.error = "source missing"
        return row
    target = source.with_suffix(".mp4")
    if target == source:
        target_tmp = source.with_name(source.stem + ".repair.tmp.mp4")
    else:
        target_tmp = target.with_name(target.stem + ".repair.tmp.mp4")
    rel = source.relative_to(media_root)
    backup = backup_root / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    target_tmp.parent.mkdir(parents=True, exist_ok=True)

    def run_ffmpeg(args: list[str]) -> tuple[bool, str]:
        completed = subprocess.run([ffmpeg, "-y", *args], capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout or "ffmpeg failed")[-4000:]
        return True, ""

    ok, error = run_ffmpeg(["-i", str(source), "-map", "0", "-c", "copy", "-movflags", "+faststart", str(target_tmp)])
    if not ok:
        ok, error = run_ffmpeg(["-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(target_tmp)])
    if not ok:
        row.status = "repair_failed"
        row.error = error
        return row
    verify = inspect_file(target_tmp, media_root, ffprobe)
    if verify.status not in {"ok", "repair_needed"} or verify.duration <= 0:
        row.status = "repair_failed"
        row.error = "repaired file failed verification"
        target_tmp.unlink(missing_ok=True)
        return row
    shutil.move(str(source), str(backup))
    shutil.move(str(target_tmp), str(target))
    row.status = "repaired"
    row.action = "repaired"
    row.repaired_path = str(target)
    row.backup_path = str(backup)
    row.error = ""
    return row


def write_reports(repo_root: Path, rows: list[QaRow], mode: str) -> Path:
    report_dir = repo_root / "reports" / "media_file_qa" / now_stamp()
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {"version": VERSION, "mode": mode, "generated_at": datetime.now().isoformat(timespec="seconds"), "summary": summarize(rows), "rows": [asdict(r) for r in rows]}
    (report_dir / "media_playback_qa.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    with (report_dir / "media_playback_qa.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else list(QaRow("","","","","","","",0,0,"").__dict__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    html_rows = "".join(f"<tr><td>{r.status}</td><td>{r.relative_path}</td><td>{r.video_codec}</td><td>{r.audio_codec}</td><td>{r.duration:.1f}</td><td>{r.reason}</td><td>{r.error}</td></tr>" for r in rows)
    (report_dir / "media_playback_qa.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>Media Playback QA</title><style>body{{font-family:Segoe UI,Arial;background:#06101f;color:#f4f7ff}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #25426d;padding:5px}}</style></head><body><h1>Media Playback QA</h1><pre>{json.dumps(summarize(rows), indent=2)}</pre><table><tr><th>Status</th><th>File</th><th>Video</th><th>Audio</th><th>Duration</th><th>Reason</th><th>Error</th></tr>{html_rows}</table></body></html>", encoding="utf-8", newline="\n")
    with zipfile.ZipFile(report_dir.with_suffix(".zip"), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in report_dir.rglob("*"):
            archive.write(file, file.relative_to(report_dir.parent))
    return report_dir


def summarize(rows: list[QaRow]) -> dict[str, int]:
    result: dict[str, int] = {"total": len(rows), "ok": 0, "repair_needed": 0, "repaired": 0, "repair_failed": 0, "repair_skipped": 0, "unknown": 0}
    for row in rows:
        result[row.status] = result.get(row.status, 0) + 1
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA and repair local media playback files.")
    parser.add_argument("mode", choices=["scan", "repair"])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--media-root", required=True)
    parser.add_argument("--title-filter", default="")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    repo_root = Path(args.repo)
    media_root = Path(args.media_root)
    ffprobe = find_executable("ffprobe")
    ffmpeg = find_executable("ffmpeg")
    files = iter_media(media_root, args.title_filter)
    rows: list[QaRow] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(inspect_file, path, media_root, ffprobe): path for path in files}
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda r: r.relative_path.lower())
    if args.mode == "repair":
        backup_root = media_root / "_MediaRenamer_Originals" / now_stamp()
        repaired: list[QaRow] = []
        for row in rows:
            repaired.append(repair_file(row, media_root, backup_root, ffmpeg, ffprobe))
        rows = repaired
    report_dir = write_reports(repo_root, rows, args.mode)
    print(json.dumps({"summary": summarize(rows), "report_dir": str(report_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
