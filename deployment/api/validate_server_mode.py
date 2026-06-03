"""Focused validation for server-mode implementation scaffolds."""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (
    ROOT / "deployment" / "api",
    ROOT / "deployment" / "postgres",
    ROOT / "deployment" / "trakt_sync",
    ROOT / "deployment" / "media_library",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


REQUIRED_FILES = [
    "deployment/api/server_mode_api.py",
    "deployment/api/server_mode_config.py",
    "deployment/api/postgres_client.py",
    "deployment/postgres/apply_schema.py",
    "deployment/postgres/validate_schema.py",
    "deployment/postgres/json_migration.py",
    "deployment/trakt_sync/trakt_worker.py",
    "deployment/media_library/media_library_worker.py",
]


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    modules = [
        "server_mode_config",
        "postgres_client",
        "server_mode_api",
        "json_migration",
        "apply_schema",
        "validate_schema",
        "trakt_worker",
        "media_library_worker",
    ]
    import_errors = {}
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:
            import_errors[name] = f"{exc.__class__.__name__}: {exc}"
    text = "\n".join((ROOT / path).read_text(encoding="utf-8-sig") for path in REQUIRED_FILES if (ROOT / path).exists())
    forbidden = re.findall(r"(?im)^\s*(DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE|DELETE\s+FROM)\b", text)
    required_text = [
        "/api/v1",
        "127.0.0.1",
        "8000",
        "MYTV_POSTGRES_DSN",
        "JSON",
        "ffprobe",
        "ffmpeg",
        "192.168.1.x",
        "192.168.2.x",
    ]
    missing_text = [token for token in required_text if token not in text]
    result = {
        "missing_files": missing,
        "import_errors": import_errors,
        "forbidden_commands": forbidden,
        "missing_required_text": missing_text,
        "passed": not missing and not import_errors and not forbidden and not missing_text,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
