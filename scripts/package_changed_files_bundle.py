#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/package_changed_files_bundle.py
# [PROJECT] my_TV_Movie
# [ROLE]    Package the exact files changed in a commit range into a zip bundle.
# [VERSION] v1.0.0
# [UPDATED] 2026-03-21
# [BUILD]   21.03.02
# ==============================================================================

from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "reports" / "availability_status"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-ref", required=True)
    parser.add_argument("--to-ref", default="HEAD")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    changed = [line.strip() for line in _git("diff", "--name-only", f"{args.from_ref}..{args.to_ref}").splitlines() if line.strip()]
    if not changed:
        print(json.dumps({"result": "FAIL", "reason": "no changed files found"}, indent=2))
        return 1

    output = Path(args.output) if args.output else (OUT_DIR / f"availability_phase2_bundle_{args.from_ref[:7]}_{args.to_ref[:7]}.zip")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in changed:
            path = REPO_ROOT / rel
            if path.is_file():
                zf.write(path, arcname=rel)

    print(json.dumps({"result": "OK", "output": str(output), "file_count": len(changed), "files": changed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
