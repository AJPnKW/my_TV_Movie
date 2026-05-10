# FILE: scripts/validate_media_renamer.py
# VERSION: v0.4.4
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))
from tools.media_renamer.media_validator import validate_repo


def main() -> int:
    validate_repo(Path.cwd())
    print("media cleanup pipeline validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
