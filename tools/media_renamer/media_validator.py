from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class ValidationResult:
    checked: bool
    valid: bool | None
    reason: str

def validate_media(path: Path, ffprobe: str | None = "ffprobe") -> ValidationResult:
    if not path.exists():
        return ValidationResult(True, False, "missing")
    if path.is_file() and path.stat().st_size == 0:
        return ValidationResult(True, False, "zero-byte")
    if path.name.casefold().endswith(".tmp.mp4"):
        return ValidationResult(True, False, "temporary recording")
    if not ffprobe:
        return ValidationResult(False, None, "ffprobe not configured")
    try:
        completed = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", "-show_streams", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return ValidationResult(False, None, f"ffprobe unavailable: {exc}")
    if completed.returncode == 0 and completed.stdout.strip():
        return ValidationResult(True, True, "ffprobe valid")
    return ValidationResult(True, False, completed.stderr.strip() or "ffprobe invalid")
