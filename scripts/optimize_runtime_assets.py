#!/usr/bin/env python3
"""
Optimize runtime images from immutable originals.

Source: assets/original_downloads
Targets:
- assets/posters: max width 342px
- assets/stills: max width 780px
- assets/backdrops: max width 780px
- assets/logos/assets/icons: max width 256px, lossless-friendly

Filenames and relative folders are preserved. Original files are never modified.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS = REPO_ROOT / "assets"
ORIGINALS = ASSETS / "original_downloads"
REPORT_DIR = REPO_ROOT / "reports" / "ui_stabilization"
REPORT_PATH = REPORT_DIR / "asset_optimization.json"

TARGET_WIDTHS = {
    "posters": 342,
    "stills": 780,
    "backdrops": 780,
    "logos": 256,
    "icons": 256,
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def target_for(src: Path) -> tuple[Path, int] | None:
    try:
        rel = src.relative_to(ORIGINALS)
    except ValueError:
        return None
    if not rel.parts:
        return None
    family = rel.parts[0].lower()
    max_width = TARGET_WIDTHS.get(family)
    if not max_width:
        return None
    return ASSETS / rel, max_width


def save_image(img: Image.Image, path: Path) -> None:
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in {".jpg", ".jpeg"}:
        if img.mode not in {"RGB", "L"}:
            img = img.convert("RGB")
        img.save(path, quality=82, optimize=True, progressive=True)
    elif suffix == ".png":
        img.save(path, optimize=True)
    elif suffix == ".webp":
        if img.mode not in {"RGB", "RGBA"}:
            img = img.convert("RGB")
        img.save(path, quality=82, method=6)
    else:
        img.save(path)


def optimize_one(src: Path, dry_run: bool = False) -> dict[str, Any] | None:
    mapped = target_for(src)
    if not mapped:
        return None
    dest, max_width = mapped
    before = src.stat().st_size
    existing = dest.stat().st_size if dest.exists() else 0

    try:
        with Image.open(src) as raw:
            img = ImageOps.exif_transpose(raw)
            original_size = img.size
            if img.width > max_width:
                ratio = max_width / float(img.width)
                next_size = (max_width, max(1, round(img.height * ratio)))
                img = img.resize(next_size, Image.Resampling.LANCZOS)
            optimized_size = img.size
            if not dry_run:
                save_image(img, dest)
    except Exception as exc:
        return {
            "source": str(src.relative_to(REPO_ROOT)),
            "target": str(dest.relative_to(REPO_ROOT)),
            "error": str(exc)[:300],
            "source_bytes": before,
            "previous_runtime_bytes": existing,
        }

    after = dest.stat().st_size if dest.exists() else 0
    return {
        "source": str(src.relative_to(REPO_ROOT)),
        "target": str(dest.relative_to(REPO_ROOT)),
        "source_bytes": before,
        "previous_runtime_bytes": existing,
        "runtime_bytes": after,
        "bytes_saved_vs_source": max(0, before - after),
        "bytes_saved_vs_previous": existing - after if existing else 0,
        "original_size": list(original_size),
        "runtime_size": list(optimized_size),
        "max_width": max_width,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = [p for p in ORIGINALS.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    rows: list[dict[str, Any]] = []
    for src in files:
        row = optimize_one(src, dry_run=args.dry_run)
        if row:
            rows.append(row)

    total_source = sum(int(r.get("source_bytes") or 0) for r in rows)
    total_previous = sum(int(r.get("previous_runtime_bytes") or 0) for r in rows)
    total_runtime = sum(int(r.get("runtime_bytes") or 0) for r in rows)
    report = {
        "generated_utc": utc_now(),
        "script": "scripts/optimize_runtime_assets.py",
        "dry_run": bool(args.dry_run),
        "source_root": "assets/original_downloads",
        "target_widths": TARGET_WIDTHS,
        "counts": {
            "source_files": len(files),
            "processed": len(rows),
            "errors": sum(1 for r in rows if r.get("error")),
        },
        "bytes": {
            "original_total": total_source,
            "previous_runtime_total": total_previous,
            "runtime_total": total_runtime,
            "saved_vs_original": max(0, total_source - total_runtime),
            "saved_vs_previous": total_previous - total_runtime,
        },
        "samples_largest_savings": sorted(rows, key=lambda r: int(r.get("bytes_saved_vs_source") or 0), reverse=True)[:50],
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))
    print(json.dumps(report["bytes"], indent=2))
    print(str(REPORT_PATH.relative_to(REPO_ROOT)))
    return 0 if report["counts"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
