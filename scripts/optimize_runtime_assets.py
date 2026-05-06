#!/usr/bin/env python3
"""
Optimize runtime images from immutable originals.

Source: assets/original_downloads
Targets:
- assets/posters: 171x257
- assets/stills: 256x180 after 10% side crop
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

TARGETS = {
    "posters": {"size": (171, 257), "fit": "cover"},
    "stills": {"size": (256, 180), "fit": "still_crop"},
    "backdrops": {"max_width": 780},
    "logos": {"max_width": 256},
    "icons": {"max_width": 256},
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def target_for(src: Path) -> tuple[Path, dict[str, Any]] | None:
    try:
        rel = src.relative_to(ORIGINALS)
    except ValueError:
        return None
    if not rel.parts:
        return None
    family = rel.parts[0].lower()
    target = TARGETS.get(family)
    if not target:
        return None
    return ASSETS / rel, target


def target_for_runtime(src: Path) -> tuple[Path, dict[str, Any]] | None:
    try:
        rel = src.relative_to(ASSETS)
    except ValueError:
        return None
    if not rel.parts or rel.parts[0] == "original_downloads":
        return None
    family = rel.parts[0].lower()
    target = TARGETS.get(family)
    if not target:
        return None
    original = ORIGINALS / rel
    if original.exists():
        return None
    return src, target


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


def prepare_runtime_image(img: Image.Image, target: dict[str, Any]) -> Image.Image:
    fit = target.get("fit")
    size = target.get("size")
    if fit == "still_crop" and size:
        width, height = img.size
        crop_x = max(0, round(width * 0.10))
        if crop_x and width - (crop_x * 2) > 1:
            img = img.crop((crop_x, 0, width - crop_x, height))
        return ImageOps.fit(img, tuple(size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    if fit == "cover" and size:
        return ImageOps.fit(img, tuple(size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    max_width = int(target.get("max_width") or 0)
    if max_width > 0 and img.width > max_width:
        ratio = max_width / float(img.width)
        next_size = (max_width, max(1, round(img.height * ratio)))
        return img.resize(next_size, Image.Resampling.LANCZOS)
    return img


def optimize_one(src: Path, dry_run: bool = False) -> dict[str, Any] | None:
    mapped = target_for(src) or target_for_runtime(src)
    if not mapped:
        return None
    dest, target = mapped
    before = src.stat().st_size
    existing = dest.stat().st_size if dest.exists() else 0

    try:
        with Image.open(src) as raw:
            img = ImageOps.exif_transpose(raw)
            original_size = img.size
            img = prepare_runtime_image(img, target)
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
        "target_spec": target,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    original_files = [p for p in ORIGINALS.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    runtime_only_files = [
        p for p in ASSETS.rglob("*")
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTS
        and target_for_runtime(p)
    ]
    files = original_files + runtime_only_files
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
        "targets": TARGETS,
        "counts": {
            "source_files": len(original_files),
            "runtime_only_files": len(runtime_only_files),
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
