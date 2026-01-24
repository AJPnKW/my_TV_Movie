#!/usr/bin/env python3
# ==============================================================================
# File: scripts/crop_logo_padding.py
# Project: my_TV_Movie
# Purpose:
#   Trim transparent padding around logo PNGs to reduce empty edges.
#   Safe: only crops transparent pixels; no scaling or color changes.
#
# Usage:
#   python scripts/crop_logo_padding.py --dir assets/logos/services
#   python scripts/crop_logo_padding.py --dir assets/logos/services --dry-run
# ==============================================================================
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

from PIL import Image  # type: ignore


def nontransparent_bbox(img: Image.Image) -> Tuple[int, int, int, int] | None:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.split()[-1]
    return alpha.getbbox()


def crop_file(path: Path, dry_run: bool) -> bool:
    try:
        img = Image.open(path)
        bbox = nontransparent_bbox(img)
        if not bbox:
            return False
        # If no change, skip.
        if bbox == (0, 0, img.width, img.height):
            return False
        if dry_run:
            return True
        cropped = img.crop(bbox)
        cropped.save(path)
        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Trim transparent padding around logo PNGs.")
    ap.add_argument("--dir", required=True, help="Directory containing PNG logos")
    ap.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = ap.parse_args()

    root = Path(args.dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] Missing folder: {root}")
        return 2

    changed = 0
    total = 0
    for fp in root.rglob("*.png"):
        total += 1
        if crop_file(fp, args.dry_run):
            changed += 1

    mode = "DRY-RUN" if args.dry_run else "DONE"
    print(f"[{mode}] scanned={total} cropped={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
