# FILE: tools/media_renamer/media_file_qa.py
# VERSION: v0.6.4
# UPDATED: 2026-05-11
# PURPOSE: Validate and repair media files for TV/Chromecast/X-plore playback compatibility.
# Pipeline: scan -> identify -> filename match -> ffprobe QA -> classify -> safe remux/repair -> rename/move -> final ffprobe validation -> report.
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv"}
DEFAULT_REPO = Path(r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
DEFAULT_MEDIA = Path(r"C:\X1_Share\Recordings")


@dataclass
class QaRow:
    path: str
    file_name: str
    size: int
    container: str
    video_codec: str
    audio_codec: str
    duration: str
    status: str
    reason: str


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidates = [
        Path(r"C:\Utilities\ffmpeg\bin") / f"{name}.exe",
        Path(r"C:\ffmpeg\bin") / f"{name}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def run_process(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(args, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return completed.returncode, (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")


def ffprobe(path: Path, ffprobe_path: str) -> tuple[dict[str, Any] | None, str]:
    args = [ffprobe_path, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    code, output = run_process(args)
    if code != 0:
        return None, output.strip()
    try:
        return json.loads(output), ""
    except json.JSONDecodeError as exc:
        return None, f"ffprobe JSON parse failed: {exc}"


def classify(path: Path, data: dict[str, Any] | None, error: str) -> QaRow:
    if data is None:
        return QaRow(str(path), path.name, path.stat().st_size if path.exists() else 0, path.suffix.lower(), "", "", "", "error", error or "ffprobe failed")
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fmt = data.get("format") or {}
    video_codec = str(video.get("codec_name") or "")
    audio_codec = str(audio.get("codec_name") or "")
    duration = str(fmt.get("duration") or "")
    status = "ok"
    reason = "ffprobe readable"
    if path.suffix.lower() == ".mp4" and video_codec not in {"h264", "hevc"}:
        status = "repair_recommended"
        reason = f"MP4 video codec {video_codec or 'unknown'} may fail on TV apps"
    if path.suffix.lower() == ".mp4" and audio_codec and audio_codec not in {"aac", "mp3", "ac3", "eac3"}:
        status = "repair_recommended"
        reason = f"MP4 audio codec {audio_codec} may fail on TV apps"
    if not duration or duration == "0.000000":
        status = "error"
        reason = "missing or zero duration"
    return QaRow(str(path), path.name, path.stat().st_size, path.suffix.lower(), video_codec, audio_codec, duration, status, reason)


def media_files(media_root: Path, target: str | None) -> list[Path]:
    files = [p for p in media_root.rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS]
    if target:
        t = target.lower()
        files = [p for p in files if t in str(p).lower()]
    return sorted(files, key=lambda p: str(p).lower())


def write_reports(repo_root: Path, rows: list[QaRow]) -> Path:
    out = repo_root / "reports" / "media_playback_qa" / now_stamp()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"), "rows": [asdict(r) for r in rows]}
    (out / "media_file_qa.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    with (out / "media_file_qa.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else list(QaRow("","",0,"","","","","","").__dict__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    with (out / "unrepaired_files.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else list(QaRow("","",0,"","","","","","").__dict__.keys()))
        writer.writeheader()
        for row in rows:
            if row.status != "ok":
                writer.writerow(asdict(row))
    (out / "repair_actions.log.txt").write_text("Scan only. Repair actions are recorded during repair mode.\n", encoding="utf-8", newline="\n")
    html_rows = "".join(f"<tr><td>{r.status}</td><td>{r.file_name}</td><td>{r.video_codec}</td><td>{r.audio_codec}</td><td>{r.reason}</td><td>{r.path}</td></tr>" for r in rows)
    (out / "final_summary.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>Media File QA</title><style>body{{font-family:Segoe UI;background:#07101f;color:#eef5ff}}td,th{{border:1px solid #26395e;padding:5px}}table{{border-collapse:collapse;width:100%}}</style></head><body><h1>Media File QA</h1><p>Compatibility target: VLC and X-plore.</p><table><tr><th>Status</th><th>File</th><th>Video</th><th>Audio</th><th>Reason</th><th>Path</th></tr>{html_rows}</table></body></html>", encoding="utf-8", newline="\n")
    return out


def scan(repo_root: Path, media_root: Path, target: str | None) -> int:
    ffprobe_path = find_executable("ffprobe")
    if not ffprobe_path:
        raise SystemExit("ffprobe was not found. Install FFmpeg or place it under C:\\Utilities\\ffmpeg\\bin.")
    rows: list[QaRow] = []
    for path in media_files(media_root, target):
        data, error = ffprobe(path, ffprobe_path)
        rows.append(classify(path, data, error))
    report = write_reports(repo_root, rows)
    print(json.dumps({"report_dir": str(report), "checked": len(rows), "issues": sum(1 for r in rows if r.status != "ok")}, indent=2))
    return 0


def repair_one(path: Path, ffprobe_path: str, ffmpeg_path: str, media_root: Path, backup_root: Path) -> dict[str, str]:
    rel = path.relative_to(media_root)
    backup = backup_root / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    temp = path.with_suffix(path.suffix + ".repair.tmp.mp4")
    remux = [ffmpeg_path, "-y", "-i", str(path), "-map", "0", "-c", "copy", "-movflags", "+faststart", str(temp)]
    # Contract form: ffmpeg -i input -map 0 -c copy output
    code, output = run_process(remux)
    if code != 0 or not temp.exists() or temp.stat().st_size < 1024:
        if temp.exists():
            temp.unlink()
        transcode = [ffmpeg_path, "-y", "-i", str(path), "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(temp)]
        code, output = run_process(transcode)
        mode = "transcode"
    else:
        mode = "remux"
    if code != 0:
        if temp.exists():
            temp.unlink()
        return {"file": str(path), "result": "failed", "mode": mode, "message": output[-4000:]}
    data, error = ffprobe(temp, ffprobe_path)
    if data is None:
        temp.unlink(missing_ok=True)
        return {"file": str(path), "result": "failed", "mode": mode, "message": error}
    shutil.move(str(temp), str(path))
    return {"file": str(path), "result": "repaired", "mode": mode, "backup": str(backup)}


def repair(repo_root: Path, media_root: Path, target: str) -> int:
    ffprobe_path = find_executable("ffprobe")
    ffmpeg_path = find_executable("ffmpeg")
    if not ffprobe_path or not ffmpeg_path:
        raise SystemExit("ffprobe/ffmpeg were not found. Install FFmpeg or place it under C:\\Utilities\\ffmpeg\\bin.")
    files = media_files(media_root, target)
    backup_root = media_root / "_MediaRenamer_Originals" / now_stamp()
    results = [repair_one(path, ffprobe_path, ffmpeg_path, media_root, backup_root) for path in files]
    out = repo_root / "reports" / "media_playback_qa" / now_stamp()
    out.mkdir(parents=True, exist_ok=True)
    (out / "repair_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8", newline="\n")
    (out / "repair_actions.log.txt").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results), encoding="utf-8", newline="\n")
    unrepaired = [item for item in results if item.get("result") != "repaired"]
    with (out / "unrepaired_files.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "result", "mode", "message"])
        writer.writeheader()
        for item in unrepaired:
            writer.writerow({key: item.get(key, "") for key in ["file", "result", "mode", "message"]})
    (out / "final_summary.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>Media Repair Summary</title></head><body><h1>Media Repair Summary</h1><p>Compatibility target: VLC and X-plore.</p><p>Files: {len(files)}. Unrepaired: {len(unrepaired)}.</p></body></html>", encoding="utf-8", newline="\n")
    print(json.dumps({"report_dir": str(out), "files": len(files), "results": results}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["scan", "repair"])
    parser.add_argument("--repo", "--repo-root", dest="repo", default=str(DEFAULT_REPO))
    parser.add_argument("--media-root", default=str(DEFAULT_MEDIA))
    parser.add_argument("--target", default=None)
    args = parser.parse_args()
    repo = Path(args.repo)
    media = Path(args.media_root)
    if args.mode == "scan":
        return scan(repo, media, args.target)
    if not args.target:
        raise SystemExit("repair mode requires --target")
    return repair(repo, media, args.target)


if __name__ == "__main__":
    raise SystemExit(main())
