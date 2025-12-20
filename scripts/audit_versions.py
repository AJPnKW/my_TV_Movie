#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/audit_versions.py
# [PROJECT] my_TV_Movie (My TV Hub)
# [ROLE]    Version/header inventory + validation across repo (deterministic)
# [VERSION] v1.6.0
# [UPDATED] 2025-12-19_00-00-00
# [BUILD]   14.01.05
#
# [BINDING RULES APPLIED]
# - No new architecture / no new repo structure required.
# - Canonical assets are binding; this script flags deprecated "image/" references.
# - Errors must surface visually (console + log) and via non-zero exit for CI.
# - Deterministic output ordering.
#
# [WHAT IT DOES]
# 1) Scans a fixed set of repo folders for files (no GitHub listing needed; local scan only)
# 2) Extracts header fields when present:
#      [FILE] [PROJECT] [ROLE] [VERSION] [UPDATED] [BUILD]
# 3) Produces:
#      - logs/audit_versions_YYYY-MM-DD_HHMMSS.log.txt
#      - data/version_inventory.json
#      - data/version_inventory.csv
# 4) Validation gates (configurable):
#      - Missing required header fields
#      - Duplicate [FILE] headers across different paths
#      - Deprecated path references: "image/" (binding rule: must not be referenced)
#
# [EXIT CODES]
#   0 = OK
#   2 = Findings (validation failures)
#   3 = Runtime error
# ==============================================================================

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import orjson  # type: ignore
except Exception:
    orjson = None  # noqa


# -------------------------
# Paths
# -------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"
DATA_DIR = REPO_ROOT / "data"

OUT_JSON = DATA_DIR / "version_inventory.json"
OUT_CSV = DATA_DIR / "version_inventory.csv"

# fixed scan roots (deterministic)
SCAN_ROOTS = [
    REPO_ROOT / "scripts",
    REPO_ROOT / "web",
    REPO_ROOT / ".github" / "workflows",
    REPO_ROOT / "docs",
]

# include extensions only (avoid noise)
INCLUDE_EXTS = {
    ".py",
    ".ps1",
    ".sh",
    ".yml",
    ".yaml",
    ".json",
    ".html",
    ".css",
    ".js",
    ".md",
    ".txt",
}

# exclude common large/noisy dirs if present
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

# header patterns
RE_HEADER_LINE = re.compile(r"^\s*#?\s*\[\s*(FILE|PROJECT|ROLE|VERSION|UPDATED|BUILD)\s*\]\s*(.+?)\s*$", re.IGNORECASE)
RE_DEPRECATED_IMAGE = re.compile(r"(?i)\bimage\/")  # binding rule: must not be referenced


@dataclass
class FileHeader:
    rel_path: str
    file_header: Optional[str]
    project: Optional[str]
    role: Optional[str]
    version: Optional[str]
    updated: Optional[str]
    build: Optional[str]
    has_deprecated_image_ref: bool
    header_missing_fields: List[str]


def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"audit_versions_{_now_stamp()}.log.txt"


def _write_log(fp, msg: str) -> None:
    line = f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    fp.write(line + "\n")
    fp.flush()
    print(line)


def _iter_files() -> List[Path]:
    files: List[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_dir():
                if p.name in EXCLUDE_DIR_NAMES:
                    # skip by pruning: rglob doesn't support prune; filter later by path parts
                    continue
            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
                continue
            if p.suffix.lower() not in INCLUDE_EXTS:
                continue
            files.append(p)
    # deterministic sort
    files_sorted = sorted(files, key=lambda x: x.as_posix().lower())
    return files_sorted


def _read_head(path: Path, max_lines: int = 80) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line)
            return "".join(lines)
    except Exception:
        return ""


def _read_all_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_header(head_text: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for line in head_text.splitlines():
        m = RE_HEADER_LINE.match(line)
        if not m:
            continue
        k = m.group(1).strip().upper()
        v = m.group(2).strip()
        fields[k] = v
    return fields


def _validate_missing(fields: Dict[str, str]) -> List[str]:
    missing = []
    for k in ["FILE", "PROJECT", "ROLE", "VERSION", "UPDATED", "BUILD"]:
        if not fields.get(k):
            missing.append(k)
    return missing


def _build_record(path: Path) -> FileHeader:
    rel = path.relative_to(REPO_ROOT).as_posix()
    head = _read_head(path, max_lines=120)
    fields = _extract_header(head)

    full_text = _read_all_text(path)
    has_image_ref = bool(RE_DEPRECATED_IMAGE.search(full_text))

    missing = _validate_missing(fields)

    return FileHeader(
        rel_path=rel,
        file_header=fields.get("FILE"),
        project=fields.get("PROJECT"),
        role=fields.get("ROLE"),
        version=fields.get("VERSION"),
        updated=fields.get("UPDATED"),
        build=fields.get("BUILD"),
        has_deprecated_image_ref=has_image_ref,
        header_missing_fields=missing,
    )


def _write_outputs(records: List[FileHeader], log_fp) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    out_json_obj = {
        "generated_at_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": REPO_ROOT.as_posix(),
        "counts": {
            "files_scanned": len(records),
            "missing_headers": sum(1 for r in records if len(r.header_missing_fields) > 0),
            "deprecated_image_refs": sum(1 for r in records if r.has_deprecated_image_ref),
        },
        "records": [
            {
                "rel_path": r.rel_path,
                "header": {
                    "FILE": r.file_header,
                    "PROJECT": r.project,
                    "ROLE": r.role,
                    "VERSION": r.version,
                    "UPDATED": r.updated,
                    "BUILD": r.build,
                },
                "flags": {
                    "deprecated_image_ref": r.has_deprecated_image_ref,
                    "missing_header_fields": r.header_missing_fields,
                },
            }
            for r in records
        ],
    }

    if orjson is not None:
        OUT_JSON.write_bytes(orjson.dumps(out_json_obj, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    else:
        OUT_JSON.write_text(json.dumps(out_json_obj, indent=2, sort_keys=True), encoding="utf-8")
    _write_log(log_fp, f"WROTE {OUT_JSON.as_posix()}")

    # CSV
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "rel_path",
                "header_file",
                "project",
                "role",
                "version",
                "updated",
                "build",
                "missing_header_fields",
                "deprecated_image_ref",
            ]
        )
        for r in records:
            w.writerow(
                [
                    r.rel_path,
                    r.file_header or "",
                    r.project or "",
                    r.role or "",
                    r.version or "",
                    r.updated or "",
                    r.build or "",
                    ",".join(r.header_missing_fields),
                    "YES" if r.has_deprecated_image_ref else "NO",
                ]
            )
    _write_log(log_fp, f"WROTE {OUT_CSV.as_posix()}")


def _summarize_findings(records: List[FileHeader], log_fp) -> Tuple[int, List[str]]:
    findings: List[str] = []

    missing = [r for r in records if r.header_missing_fields]
    if missing:
        findings.append(f"FAIL missing header fields in {len(missing)} file(s)")

    img_refs = [r for r in records if r.has_deprecated_image_ref]
    if img_refs:
        findings.append(f"FAIL deprecated 'image/' reference(s) in {len(img_refs)} file(s)")

    # Duplicate [FILE] header values across different rel paths
    seen: Dict[str, str] = {}
    dups: List[Tuple[str, str, str]] = []
    for r in records:
        if not r.file_header:
            continue
        key = r.file_header.strip()
        if key in seen and seen[key] != r.rel_path:
            dups.append((key, seen[key], r.rel_path))
        else:
            seen[key] = r.rel_path
    if dups:
        findings.append(f"FAIL duplicate [FILE] header values in {len(dups)} case(s)")

    # write detail lists (deterministic)
    if missing:
        _write_log(log_fp, "---- Missing header fields ----")
        for r in missing:
            _write_log(log_fp, f"MISSING {r.rel_path} :: {','.join(r.header_missing_fields)}")
    if img_refs:
        _write_log(log_fp, "---- Deprecated image/ references ----")
        for r in img_refs:
            _write_log(log_fp, f"DEPRECATED image/ :: {r.rel_path}")
    if dups:
        _write_log(log_fp, "---- Duplicate [FILE] header values ----")
        for k, p1, p2 in sorted(dups, key=lambda x: (x[0].lower(), x[1].lower(), x[2].lower())):
            _write_log(log_fp, f"DUP [FILE]={k} :: {p1} AND {p2}")

    exit_code = 0 if not findings else 2
    return exit_code, findings


def main() -> int:
    lp = _log_path()
    with lp.open("w", encoding="utf-8") as log_fp:
        _write_log(log_fp, "[audit_versions] START")
        _write_log(log_fp, f"repo_root={REPO_ROOT.as_posix()}")

        try:
            files = _iter_files()
            _write_log(log_fp, f"files_scanned={len(files)}")
            records = [_build_record(p) for p in files]
            _write_outputs(records, log_fp)
            exit_code, findings = _summarize_findings(records, log_fp)

            if findings:
                _write_log(log_fp, "---- Findings ----")
                for f in findings:
                    _write_log(log_fp, f)

            _write_log(log_fp, f"[audit_versions] END exit_code={exit_code} log={lp.as_posix()}")
        except Exception as e:
            _write_log(log_fp, f"[audit_versions] ERROR {e}")
            _write_log(log_fp, f"[audit_versions] END exit_code=3 log={lp.as_posix()}")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
            return 3

    try:
        input("Press Enter to close...")
    except Exception:
        pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
