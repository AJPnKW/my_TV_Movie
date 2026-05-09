"""Launch or self-test the PySide6 media renamer."""

from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = REPO_ROOT / "tools" / "media_renamer"
VENV_DIR = REPO_ROOT / ".venv_media_renamer_pyside6"
REQUIREMENTS = TOOL_DIR / "requirements.txt"
APP = TOOL_DIR / "media_renamer_app.py"
ENGINE = TOOL_DIR / "media_renamer_engine.py"


def python_exe() -> Path:
    if sys.platform.startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run(command: list[str], cwd: Path) -> None:
    print("RUN:", " ".join(command))
    completed = subprocess.run(command, cwd=str(cwd), text=True, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def ensure_environment() -> Path:
    if not APP.exists():
        raise SystemExit(f"Missing app: {APP}")
    if not VENV_DIR.exists():
        print(f"Creating virtual environment: {VENV_DIR}")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)
    py = python_exe()
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "--no-cache-dir"], REPO_ROOT)
    run([str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS), "--no-cache-dir"], REPO_ROOT)
    return py


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the media renamer.")
    parser.add_argument("--self-test", action="store_true", help="Run non-GUI checks and exit.")
    args = parser.parse_args()
    if args.self_test:
        run([sys.executable, str(ENGINE), "--repo-root", str(REPO_ROOT), "--self-test"], REPO_ROOT)
        return 0
    py = ensure_environment()
    run([str(py), str(APP)], REPO_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
