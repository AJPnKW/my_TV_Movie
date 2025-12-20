#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/audit_versions.py
# [PROJECT] my_TV_Movie (My TV Hub)
# [ROLE]    Version/header inventory + validation across repo (deterministic)
# [VERSION] v1.7.0
# [UPDATED] 2025-12-19_00-00-00
# [BUILD]   14.01.06
#
# [POLICY FIX]
# - Headers are REQUIRED ONLY for "code/config" file types that support comment headers.
# - Docs/reference files are still scanned for deprecated "image/" references, but do not
#   fail header validation unless their extension is in HEADER_REQUIRED_EXTS.
#
# [BINDING RULES APPLIED]
# - Canonical assets are binding; flags deprecated "image/" references.
# - No silent failures: console + log + non-zero exit for CI on findings.
# - Deterministic ordering.
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

# Scan file extensions (inventory scope)
SCAN_EXTS = {
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

# Header validation scope (policy: only where comment headers are sane)
HEADER_REQUIRED_EXTS = {
    ".py",
    ".ps1",
    ".sh",
    ".yml",
    ".yaml",
    ".html",
    ".css",
    ".js",
}

# Extensions where we NEVER require headers (even though we scan them)
HEADER_NEVER_REQUIRED_EXTS = {
    ".md",
    ".txt",
    ".json",
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

# header patterns: accept "# [KEY]" and "// [KEY]" and "<!-- [KEY]" styles
RE_HEADER_LINE = re.compile(
    r"^\s*(#|//|<!--)?\s*\[\s*(FILE|PROJECT|ROLE|VERSION|UPDATED|BUILD)\s*\]\s*(.+?)\s*(-->)?\s*$",
    re.IGNORECASE,
)

# binding: old image folder must not be referenced anywhere
RE_DEPRECATED_IMAGE = re.compile(r"(?i)\bimage\/")


@dataclass
class FileHeader:
    rel_path: str
    ext: str
    file_header: Optional[str]
    project: Optional[str]
    role: Optional[str]
    version: Optional[str]
    updated: Optional[str]
    build: Optional[str]
    has_deprecated_image_ref: bool
    header_required: bool
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
            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
                continue
            if p.suffix.lower() not in SCAN_EXTS:
                continue
            files.append(p)
    return sorted(files, key=lambda x: x.as_posix().lower())


def _read_head(path: Path, max_lines: int = 140) -> str:
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
        k = m.group(2).strip().upper()
        v = m.group(3).strip()
        fields[k] = v
    return fields


def _validate_missing(fields: Dict[str, str]) -> List[str]:
    missing = []
    for k in ["FILE", "PROJECT", "ROLE", "VERSION", "UPDATED", "BUILD"]:
        if not fields.get(k):
            missing.append(k)
    return missing


def _is_header_required(ext: str) -> bool:
    ext = ext.lower()
    if ext in HEADER_NEVER_REQUIRED_EXTS:
        return False
    return ext in HEADER_REQUIRED_EXTS


def _build_record(path: Path) -> FileHeader:
    rel = path.relative_to(REPO_ROOT).as_posix()
    ext = path.suffix.lower()

    head = _read_head(path, max_lines=160)
    fields = _extract_header(head)

    full_text = _read_all_text(path)
    has_image_ref = bool(RE_DEPRECATED_IMAGE.search(full_text))

    header_required = _is_header_required(ext)
    missing = _validate_missing(fields) if header_required else []

    return FileHeader(
        rel_path=rel,
        ext=ext,
        file_header=fields.get("FILE"),
        project=fields.get("PROJECT"),
        role=fields.get("ROLE"),
        version=fields.get("VERSION"),
        updated=fields.get("UPDATED"),
        build=fields.get("BUILD"),
        has_deprecated_image_ref=has_image_ref,
        header_required=header_required,
        header_missing_fields=missing,
    )


def _write_outputs(records: List[FileHeader], log_fp) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    out_json_obj = {
        "generated_at_utc": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": REPO_ROOT.as_posix(),
        "policy": {
            "scan_exts": sorted(SCAN_EXTS),
            "header_required_exts": sorted(HEADER_REQUIRED_EXTS),
            "header_never_required_exts": sorted(HEADER_NEVER_REQUIRED_EXTS),
        },
        "counts": {
            "files_scanned": len(records),
            "header_required_files": sum(1 for r in records if r.header_required),
            "missing_headers": sum(1 for r in records if r.header_required and len(r.header_missing_fields) > 0),
            "deprecated_image_refs": sum(1 for r in records if r.has_deprecated_image_ref),
        },
        "records": [
            {
                "rel_path": r.rel_path,
                "ext": r.ext,
                "header_required": r.header_required,
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

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "rel_path",
                "ext",
                "header_required",
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
                    r.ext,
                    "YES" if r.header_required else "NO",
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

    missing = [r for r in records if r.header_required and r.header_missing_fields]
    if missing:
        findings.append(f"FAIL missing header fields in {len(missing)} header-required file(s)")

    img_refs = [r for r in records if r.has_deprecated_image_ref]
    if img_refs:
        findings.append(f"FAIL deprecated 'image/' reference(s) in {len(img_refs)} file(s)")

    # Duplicate [FILE] header values across different rel paths (only among header-required files)
    seen: Dict[str, str] = {}
    dups: List[Tuple[str, str, str]] = []
    for r in records:
        if not r.header_required:
            continue
        if not r.file_header:
            continue
        key = r.file_header.strip()
        if key in seen and seen[key] != r.rel_path:
            dups.append((key, seen[key], r.rel_path))
        else:
            seen[key] = r.rel_path
    if dups:
        findings.append(f"FAIL duplicate [FILE] header values in {len(dups)} case(s)")

    if missing:
        _write_log(log_fp, "---- Missing header fields (header-required only) ----")
        for r in missing:
            _write_log(log_fp, f"MISSING {r.rel_path} :: {','.join(r.header_missing_fields)}")
    if img_refs:
        _write_log(log_fp, "---- Deprecated image/ references ----")
        for r in img_refs:
            _write_log(log_fp, f"DEPRECATED image/ :: {r.rel_path}")
    if dups:
        _write_log(log_fp, "---- Duplicate [FILE] header values (header-required only) ----")
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
