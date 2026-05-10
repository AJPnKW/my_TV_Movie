# FILE: tools/media_renamer/media_catalog_builder.py
# VERSION: v0.4.4
from __future__ import annotations

from pathlib import Path
from .media_cleanup_pipeline import build_reference


def main() -> int:
    shows, movies = build_reference(Path.cwd())
    print(f"media_reference.json built: {len(shows)} shows, {len(movies)} movies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
