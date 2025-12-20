#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/download_service_logos.py
# [PROJECT] my_TV_Movie (My TV Hub)
# [ROLE]    Download/update streaming service logos into canonical assets hierarchy
# [VERSION] v1.8.0
# [UPDATED] 2025-12-19_00-00-00
# [BUILD]   14.01.05
#
# [BINDING RULES APPLIED]
# - Canonical asset hierarchy ONLY:
#     assets/logos/services/
#     assets/logos/services/archive/
# - Never reference deprecated "image/" folder.
# - No silent failures: all errors logged + surfaced in console.
# - No invented project files: this script requires an explicit input file path.
#
# [INPUT]
# - REQUIRED: --input <path> to a CSV or JSON file defining logo sources
#
#   CSV format (header required):
#     service_slug,url,filename
#   - service_slug : stable key/slug for the service (e.g., vidsrc, videasy, tmdb)
#   - url          : direct download URL for the logo image
#   - filename     : optional; if blank, derived from service_slug + URL extension
#
#   JSON format:
#   [
#     {"service_slug":"vidsrc","url":"https://.../vidsrc.png","filename":"vidsrc.png"},
#     ...
#   ]
#
# [OUTPUT]
# - Downloads into: assets/logos/services/<filename>
# - If --archive-existing is set and a destination file exists and will be replaced,
#   it is moved to: assets/logos/services/archive/<YYYY-MM-DD_HHMMSS>/<filename>
# - Log file: logs/download_service_logos_YYYY-MM-DD_HHMMSS.log.txt
#
# [USAGE]
#   python scripts/download_service_logos.py --input C:\path\service_logos.csv
#   python scripts/download_service_logos.py --input service_logos.json --force
#   python scripts/download_service_logos.py --input service_logos.csv --archive-existing
#
# ==============================================================================

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    print("ERROR: Missing dependency 'requests'. Install with:", file=sys.stderr)
    print("  python -m pip install requests", file=sys.stderr)
    raise

try:
    from tqdm import tqdm  # type: ignore
except Exception:
    tqdm = None  # noqa


# -------------------------
# Paths (repo-relative)
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"

ASSETS_DIR = REPO_ROOT / "assets"
ASSETS_LOGOS_SERVICES = ASSETS_DIR / "logos" / "services"
ASSETS_LOGOS_SERVICES_ARCHIVE = ASSETS_LOGOS_SERVICES / "archive"


# -------------------------
# Logging (deterministic)
# -------------------------
def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"download_service_logos_{_now_stamp()}.log.txt"


def _write_log(fp, msg: str) -> None:
    line = f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    fp.write(line + "\n")
    fp.flush()
    print(line)


# -------------------------
# Data model
# -------------------------
@dataclass(frozen=True)
class LogoSource:
    service_slug: str
    url: str
    filename: str


# -------------------------
# Helpers
# -------------------------
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_filename(name: str) -> str:
    s = (name or "").strip()
    s = _SAFE_NAME_RE.sub("_", s)
    s = s.strip("._-")
    return s or "logo"


def _ext_from_url(url: str) -> str:
    u = (url or "").strip()
    # strip query
    u = u.split("?", 1)[0]
    # last segment
    seg = u.rsplit("/", 1)[-1]
    if "." in seg:
        ext = "." + seg.rsplit(".", 1)[-1].lower()
        if len(ext) <= 6:  # .webp .jpeg etc
            return ext
    return ""


def _ensure_dirs() -> None:
    ASSETS_LOGOS_SERVICES.mkdir(parents=True, exist_ok=True)
    ASSETS_LOGOS_SERVICES_ARCHIVE.mkdir(parents=True, exist_ok=True)


def _read_csv_sources(path: Path) -> List[LogoSource]:
    out: List[LogoSource] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        required = {"service_slug", "url"}
        missing = required - set(x.strip() for x in reader.fieldnames if x)
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")
        for row in reader:
            slug = (row.get("service_slug") or "").strip()
            url = (row.get("url") or "").strip()
            fn = (row.get("filename") or "").strip()
            if not slug or not url:
                continue
            out.append(_normalize_source(slug, url, fn))
    return out


def _read_json_sources(path: Path) -> List[LogoSource]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    try:
        j = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    if not isinstance(j, list):
        raise ValueError("JSON must be an array of objects.")
    out: List[LogoSource] = []
    for obj in j:
        if not isinstance(obj, dict):
            continue
        slug = str(obj.get("service_slug") or "").strip()
        url = str(obj.get("url") or "").strip()
        fn = str(obj.get("filename") or "").strip()
        if not slug or not url:
            continue
        out.append(_normalize_source(slug, url, fn))
    return out


def _normalize_source(service_slug: str, url: str, filename: str) -> LogoSource:
    slug = _safe_filename(service_slug.lower())
    ext = _ext_from_url(url)
    if filename:
        fn = _safe_filename(filename)
        # if caller omitted extension, attempt to apply from URL
        if "." not in fn and ext:
            fn = fn + ext
    else:
        fn = slug + (ext if ext else ".png")
    return LogoSource(service_slug=slug, url=url.strip(), filename=fn)


def _download_with_retries(
    url: str,
    timeout: int,
    retries: int,
    backoff_seconds: float,
    user_agent: str,
) -> Tuple[bool, Optional[bytes], str]:
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": user_agent},
                timeout=timeout,
                stream=True,
            )
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                raise RuntimeError(last_err)
            content = r.content
            if not content or len(content) == 0:
                last_err = "Empty body"
                raise RuntimeError(last_err)
            return True, content, ""
        except Exception as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
            continue
    return False, None, last_err


def _atomic_write_bytes(dst: Path, data: bytes) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_bytes(data)
    # basic verification
    if tmp.stat().st_size <= 0:
        raise RuntimeError("Temporary file write produced empty file.")
    tmp.replace(dst)


def _archive_existing(dst: Path, archive_root: Path, stamp: str, log_fp) -> Optional[Path]:
    if not dst.exists():
        return None
    target_dir = archive_root / stamp
    target_dir.mkdir(parents=True, exist_ok=True)
    archived = target_dir / dst.name
    try:
        dst.replace(archived)
        _write_log(log_fp, f"ARCHIVE moved existing -> {archived.as_posix()}")
        return archived
    except Exception as e:
        _write_log(log_fp, f"ARCHIVE FAIL {dst.as_posix()} -> {archived.as_posix()} :: {e}")
        return None


# -------------------------
# Main
# -------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="download_service_logos.py",
        description="Download/update streaming service logos into assets/logos/services/ (canonical).",
    )
    parser.add_argument("--input", required=True, help="Path to CSV or JSON logo source list.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    parser.add_argument(
        "--archive-existing",
        action="store_true",
        help="If overwriting, move existing logos to assets/logos/services/archive/<timestamp>/",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds.")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retries per logo.")
    parser.add_argument("--backoff", type=float, default=0.6, help="Backoff multiplier for retries.")
    args = parser.parse_args()

    lp = _log_path()
    stamp = _now_stamp()

    with lp.open("w", encoding="utf-8") as log_fp:
        _write_log(log_fp, f"[download_service_logos] START {stamp}")
        _write_log(log_fp, f"repo_root={REPO_ROOT.as_posix()}")
        _write_log(log_fp, f"input={args.input}")
        _write_log(log_fp, f"force={args.force} archive_existing={args.archive_existing}")
        _write_log(log_fp, f"timeout={args.timeout} retries={args.retries} backoff={args.backoff}")

        try:
            _ensure_dirs()
        except Exception as e:
            _write_log(log_fp, f"FAIL ensure_dirs :: {e}")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 2

        src_path = Path(args.input).expanduser()
        if not src_path.is_absolute():
            src_path = (Path.cwd() / src_path).resolve()

        if not src_path.exists():
            _write_log(log_fp, f"FAIL input file not found: {src_path.as_posix()}")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 3

        # Load sources
        try:
            if src_path.suffix.lower() == ".csv":
                sources = _read_csv_sources(src_path)
            elif src_path.suffix.lower() == ".json":
                sources = _read_json_sources(src_path)
            else:
                raise ValueError("Input file must be .csv or .json")
        except Exception as e:
            _write_log(log_fp, f"FAIL parse input :: {e}")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 4

        if not sources:
            _write_log(log_fp, "FAIL input list parsed but contained 0 valid rows.")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 5

        # Deduplicate by (service_slug, filename) deterministically (first wins)
        seen = set()
        deduped: List[LogoSource] = []
        for s in sources:
            k = (s.service_slug, s.filename)
            if k in seen:
                continue
            seen.add(k)
            deduped.append(s)

        _write_log(log_fp, f"loaded_sources={len(sources)} deduped_sources={len(deduped)}")

        # Progress
        iterator = deduped
        if tqdm is not None:
            iterator = tqdm(deduped, desc="Service logos", unit="logo")  # type: ignore

        ok_count = 0
        skip_count = 0
        fail_count = 0
        wrote_count = 0
        archived_count = 0

        for src in iterator:
            dst = ASSETS_LOGOS_SERVICES / src.filename

            # Never allow deprecated "image/" anywhere
            if "image/" in dst.as_posix():
                _write_log(log_fp, f"FAIL deprecated path detected (image/): {dst.as_posix()}")
                fail_count += 1
                continue

            if dst.exists() and dst.stat().st_size > 0 and not args.force:
                _write_log(log_fp, f"SKIP exists: {dst.as_posix()}")
                skip_count += 1
                ok_count += 1
                continue

            if dst.exists() and dst.stat().st_size > 0 and args.force and args.archive_existing:
                archived = _archive_existing(dst, ASSETS_LOGOS_SERVICES_ARCHIVE, stamp, log_fp)
                if archived:
                    archived_count += 1

            _write_log(log_fp, f"GET {src.service_slug} -> {src.url}")
            success, content, err = _download_with_retries(
                url=src.url,
                timeout=int(args.timeout),
                retries=int(args.retries),
                backoff_seconds=float(args.backoff),
                user_agent="my_TV_Movie download_service_logos.py",
            )
            if not success or content is None:
                _write_log(log_fp, f"FAIL download {src.service_slug} :: {err}")
                fail_count += 1
                continue

            try:
                _atomic_write_bytes(dst, content)
                _write_log(log_fp, f"WROTE {dst.as_posix()} bytes={len(content)}")
                wrote_count += 1
                ok_count += 1
            except Exception as e:
                _write_log(log_fp, f"FAIL write {dst.as_posix()} :: {e}")
                fail_count += 1

        _write_log(log_fp, "-----------------")
        _write_log(log_fp, f"RESULT ok={ok_count} wrote={wrote_count} skipped={skip_count} archived={archived_count} failed={fail_count}")
        _write_log(log_fp, f"[download_service_logos] END log={lp.as_posix()}")

    try:
        input("Press Enter to close...")
    except Exception:
        pass

    return 0 if fail_count == 0 else 6


if __name__ == "__main__":
    raise SystemExit(main())
