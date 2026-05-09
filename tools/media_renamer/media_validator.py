# FILE: tools/media_renamer/media_validator.py
# VERSION: v0.4.0
# CHANGE NOTES:
# - Provides ffprobe-based media validation for plan mode.
# - Keeps validation non-destructive and safe for dry-run planning.

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileValidation:
    status: str
    reason: str
    ffprobe_available: bool
    size_bytes: int
    duration_seconds: float = 0.0


def find_ffprobe() -> str:
    return shutil.which("ffprobe") or ""


def validate_media_file(path: Path, ffprobe_path: str | None = None, timeout_seconds: int = 20) -> FileValidation:
    size = path.stat().st_size if path.exists() else 0
    if size == 0:
        return FileValidation(status="broken", reason="zero-byte file", ffprobe_available=bool(ffprobe_path), size_bytes=size)
    if ".tmp" in path.name.lower():
        return FileValidation(status="partial", reason="temporary recording file", ffprobe_available=bool(ffprobe_path), size_bytes=size)
    probe = ffprobe_path or find_ffprobe()
    if not probe:
        return FileValidation(status="unknown", reason="ffprobe not available", ffprobe_available=False, size_bytes=size)
    command = [
        probe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as error:
        return FileValidation(status="problem", reason=f"ffprobe failed: {error}", ffprobe_available=True, size_bytes=size)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "ffprobe rejected file").strip().splitlines()[0:1]
        return FileValidation(status="broken", reason=detail[0] if detail else "ffprobe rejected file", ffprobe_available=True, size_bytes=size)
    duration_text = (completed.stdout or "").strip()
    try:
        duration = float(duration_text) if duration_text else 0.0
    except ValueError:
        duration = 0.0
    if duration <= 0:
        return FileValidation(status="problem", reason="duration not proven", ffprobe_available=True, size_bytes=size, duration_seconds=duration)
    return FileValidation(status="valid", reason="ffprobe valid", ffprobe_available=True, size_bytes=size, duration_seconds=duration)


__all__ = ["FileValidation", "find_ffprobe", "validate_media_file"]
