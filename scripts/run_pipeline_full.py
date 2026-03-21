
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def run_step(label: str, command: list[str]) -> dict:
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "label": label,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--editor-refresh", action="store_true")
    args = parser.parse_args()

    steps = [
        ("fetch_tmdb", [sys.executable, "scripts/fetch_tmdb.py"]),
        ("fetch_tmdb_assets", [sys.executable, "scripts/fetch_tmdb_assets.py"]),
        ("refresh_missing_assets", [sys.executable, "scripts/refresh_missing_assets_from_data.py", "--no-pause"]),
        ("qa_assets", [sys.executable, "scripts/qa_assets_against_data_json.py", "--no-pause"]),
    ]

    results = [run_step(label, command) for label, command in steps]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = DATA_DIR / "asset_refresh_summary.json"
    summary_path.write_text(json.dumps({"editor_refresh": args.editor_refresh, "steps": results}, indent=2), encoding="utf-8")

    failed = [step for step in results if step["returncode"] != 0]
    print("[START] run_pipeline_full")
    for step in results:
        print(f"[STEP] {step['label']} -> rc={step['returncode']}")
    print(f"[SUMMARY] {summary_path}")
    print("[DONE] run_pipeline_full")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
