"""Media Library inventory/QA worker scaffold."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from postgres_client import PostgresClient
from server_mode_config import ServerModeConfig


def scan_roots(roots: list[str], profile: str) -> dict[str, object]:
    files = []
    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for path in root_path.rglob("*"):
            if path.is_file():
                files.append(
                    {
                        "location_profile": profile,
                        "file_path": str(path),
                        "actual_filename": path.name,
                        "file_size_bytes": path.stat().st_size,
                        "file_status": "unknown",
                        "qa_status": "not_checked",
                    }
                )
    return {"discovered": files, "count": len(files)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Media Library scan/QA dry-run worker.")
    parser.add_argument("operation", choices=["scan", "qa", "remux"], nargs="?", default="scan")
    parser.add_argument("--profile", choices=["home", "trailer", "portable", "unknown"], default="unknown")
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    config = ServerModeConfig.from_env()
    client = PostgresClient(config.postgres_dsn)
    result = {
        "operation": args.operation,
        "profile": args.profile,
        "home_network": "192.168.1.x",
        "trailer_network": "192.168.2.x",
        "postgres": client.status(),
        "ffprobe": "available" if shutil.which("ffprobe") else "missing",
        "ffmpeg": "available" if shutil.which("ffmpeg") else "missing",
        "stores_binary_assets": False,
        "apply": args.apply,
    }
    if args.operation == "scan":
        result.update(scan_roots(args.root, args.profile))
    if args.apply and not client.ready:
        result["error"] = "PostgreSQL write path unavailable; dry-run result only."
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
