#!/usr/bin/env python
# =============================================================================
# File: scripts/audit_versions.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-08)
#
# Purpose:
#   Quick QA helper:
#     - Walk the repo
#     - For each file, report:
#         * relative path
#         * detected version string (from header, if any)
#         * line count
#
# Usage:
#   From repo root:
#       python scripts/audit_versions.py
#
#   Optional:
#       python scripts/audit_versions.py > audit_report.txt
#
# Notes:
#   - Looks for "Version:" (case-insensitive) in the first 40 lines.
#   - Supports comments in:
#       * Python (# ...)
#       * HTML/JS/CSS/INI/YAML/MD/TXT (any line containing "Version:")
#   - Files without a detectable version are marked as "MISSING".
#   - Intentionally lightweight: no external deps.
# =============================================================================

import os
import sys
import re
from pathlib import Path

# -----------------------------------------------------------------------------
# CONFIG: tweak if you like
# -----------------------------------------------------------------------------

# Directories to skip entirely
SKIP_DIRS = {
    ".git",
    ".github",      # include if you want workflow versions too
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
}

# File extensions we care less about; still scanned but you can trim
SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".lock",
    ".log",
    ".pyc",
    ".pyo",
    ".db",
}

# How many lines from top of file to scan for a Version header
HEADER_SCAN_LINES = 40

# Regex to detect a version-ish line
# Examples it will catch:
#   Version: v2.4.0 (2025-11-08)
#   Version v1.0
#   VERSION: 1.2.3
VERSION_RE = re.compile(
    r"version[:\s]+([vV]?[0-9][0-9A-Za-z\.\-\(\)\s]*)",
    re.IGNORECASE,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def find_repo_root() -> Path:
    """
    Resolve repo root as:
      - parent of this script's directory
    """
    here = Path(__file__).resolve()
    return here.parents[1]


def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIRS


def should_skip_file(path: Path) -> bool:
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    return False


def detect_version(path: Path) -> str:
    """
    Scan the first HEADER_SCAN_LINES lines for a version.
    Returns:
        version string if found, else "MISSING".
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for i in range(HEADER_SCAN_LINES):
                line = f.readline()
                if not line:
                    break
                m = VERSION_RE.search(line)
                if m:
                    # Clean up whitespace
                    v = m.group(1).strip()
                    return v or "MISSING"
    except Exception:
        # If unreadable, treat as missing
        return "MISSING"
    return "MISSING"


def count_lines(path: Path) -> int:
    """
    Count total lines in file. Returns 0 on error.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    repo_root = find_repo_root()
    rows = []

    for root, dirs, files in os.walk(repo_root):
        # prune dirs
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        for name in files:
            path = Path(root) / name
            rel = path.relative_to(repo_root)

            if should_skip_file(path):
                continue

            version = detect_version(path)
            line_count = count_lines(path)

            rows.append((str(rel).replace("\\", "/"), version, line_count))

    # Sort by path
    rows.sort(key=lambda r: r[0].lower())

    # Pretty print
    # Columns:
    #   PATH | VERSION | LINES
    col_path = "PATH"
    col_ver = "VERSION"
    col_lines = "LINES"

    # width guesses
    max_path = max(len(r[0]) for r in rows) if rows else len(col_path)
    max_ver = max(len(r[1]) for r in rows) if rows else len(col_ver)

    max_path = max(max_path, len(col_path))
    max_ver = max(max_ver, len(col_ver))

    header = f"{col_path:<{max_path}}  {col_ver:<{max_ver}}  {col_lines}"
    sep = "-" * len(header)

    print(header)
    print(sep)

    for rel, ver, cnt in rows:
        print(f"{rel:<{max_path}}  {ver:<{max_ver}}  {cnt}")

    # Optional: summary footer
    total_files = len(rows)
    missing = sum(1 for _, v, _ in rows if v == "MISSING")
    print()
    print(f"Total files scanned: {total_files}")
    print(f"Files missing version: {missing}")


if __name__ == "__main__":
    main()
