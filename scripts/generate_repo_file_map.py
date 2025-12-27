#!/usr/bin/env python3
# ==============================================================================
# FILE: C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie\scripts\generate_repo_file_map.py
#
# PURPOSE:
#   Generate a key file listing for my_TV_Movie, extrapolate GitHub RAW URLs,
#   validate local existence under the repo root, and output a 4-column table:
#     1) repo_relative_path
#     2) local_full_path
#     3) github_raw_url
#     4) status (OK / MISSING_LOCAL / MISSING_EXPECTED / DUPLICATE / ERROR)
#
# OUTPUTS (written to repo root):
#   - _repo_file_map_<timestamp>.csv
#   - _repo_file_map_<timestamp>.md
#   - _repo_file_map_<timestamp>.log.txt
#
# RULES:
#   - No silent failures
#   - Deterministic ordering
#   - Includes a "key files" section + optional full inventory (toggle)
#   - Waits for Enter at end
#
# USAGE:
#   python scripts\generate_repo_file_map.py
#   python scripts\generate_repo_file_map.py --full
#   python scripts\generate_repo_file_map.py --branch main
# ==============================================================================

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class Row:
    repo_rel: str
    local_path: str
    raw_url: str
    status: str


def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def now_line() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log(log_path: Path, msg: str) -> None:
    line = f"[{now_line()}] {msg}"
    print(line)
    log_path.open("a", encoding="utf-8").write(line + "\n")


def sha256_file(path: Path, max_bytes: Optional[int] = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        if max_bytes is None:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        else:
            remaining = max_bytes
            while remaining > 0:
                chunk = f.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                h.update(chunk)
                remaining -= len(chunk)
    return h.hexdigest()


def to_posix(rel: str) -> str:
    return rel.replace("\\", "/").lstrip("/")


def build_raw_url(owner: str, repo: str, branch: str, repo_rel_posix: str) -> str:
    # Your required format example:
    # https://raw.githubusercontent.com/AJPnKW/my_TV_Movie/refs/heads/main/web/index.html
    return f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{repo_rel_posix}"


def md_table(rows: Sequence[Row]) -> str:
    header = "| repo_relative_path | local_full_path | github_raw_url | status |\n|---|---|---|---|\n"
    lines = []
    for r in rows:
        # escape pipes
        repo_rel = r.repo_rel.replace("|", "\\|")
        local_path = r.local_path.replace("|", "\\|")
        raw_url = r.raw_url.replace("|", "\\|")
        status = r.status.replace("|", "\\|")
        lines.append(f"| `{repo_rel}` | `{local_path}` | {raw_url} | **{status}** |")
    return header + "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--repo-root", default=r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
    parser.add_argument("--owner", default="AJPnKW")
    parser.add_argument("--repo", default="my_TV_Movie")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--full", action="store_true", help="Include full repo inventory (not just key files).")
    parser.add_argument("--hash", action="store_true", help="Add SHA256 file hash columns to CSV (local files only).")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"Repo root not found: {repo_root}")
        return 1

    s = stamp()
    out_csv = repo_root / f"_repo_file_map_{s}.csv"
    out_md = repo_root / f"_repo_file_map_{s}.md"
    log_path = repo_root / f"_repo_file_map_{s}.log.txt"

    write_log(log_path, "START generate_repo_file_map")
    write_log(log_path, f"repo_root: {repo_root}")
    write_log(log_path, f"owner/repo: {args.owner}/{args.repo}")
    write_log(log_path, f"branch: {args.branch}")
    write_log(log_path, f"mode: {'FULL' if args.full else 'KEY_ONLY'}")
    write_log(log_path, f"outputs: {out_csv.name}, {out_md.name}, {log_path.name}")

    # Key files you typically care about (add/remove freely)
    key_rel_paths: List[str] = [
        "web/index.html",
        "web/watchlist.html",
        "web/config.html",
        "web/config.js",
        "web/config.json",
        "data/data.json",
        "fetch_tmdb.py",
        "fetch_trakt.py",
        "sync_trakt.py",
        ".github/workflows/build-data.yml",
        "requirements.txt",
        "scripts/parse_txt_to_json.py",
        "inputs/movies_list.txt",
        "inputs/tv_list.txt",
        "tv_list.txt",
        "movies_list.txt",
        "README.md",
    ]

    # If FULL inventory: list all files excluding noisy folders
    exclude_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }

    rel_candidates: List[str] = []
    if args.full:
        for p in repo_root.rglob("*"):
            if not p.is_file():
                continue
            parts = set(p.relative_to(repo_root).parts)
            if any(part in exclude_dirs for part in parts):
                continue
            rel_candidates.append(to_posix(str(p.relative_to(repo_root))))
    else:
        rel_candidates = [to_posix(x) for x in key_rel_paths]

    # Deterministic ordering + de-dupe
    rel_candidates = sorted(set(rel_candidates), key=lambda x: x.lower())

    # Detect duplicates in key list (path duplicates after normalization)
    dupes = {}
    if not args.full:
        normed = [to_posix(x) for x in key_rel_paths]
        for p in normed:
            dupes[p] = dupes.get(p, 0) + 1

    rows: List[Row] = []
    missing_expected: List[str] = []
    errors: List[str] = []

    write_log(log_path, f"paths_to_process: {len(rel_candidates)}")

    # Build rows
    for i, rel in enumerate(rel_candidates, start=1):
        local = repo_root / rel
        raw = build_raw_url(args.owner, args.repo, args.branch, rel)

        status = "OK"
        if not local.exists():
            status = "MISSING_LOCAL"
            if not args.full:
                missing_expected.append(rel)

        if not args.full and dupes.get(rel, 0) > 1:
            status = "DUPLICATE"

        rows.append(Row(repo_rel=rel, local_path=str(local), raw_url=raw, status=status))

        if i % 25 == 0 or i == len(rel_candidates):
            write_log(log_path, f"progress: {i}/{len(rel_candidates)}")

    # Write CSV
    write_log(log_path, "writing CSV...")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if args.hash:
            w.writerow(["repo_relative_path", "local_full_path", "github_raw_url", "status", "local_sha256"])
            for r in rows:
                sha = ""
                if r.status in ("OK", "DUPLICATE") and Path(r.local_path).exists():
                    try:
                        sha = sha256_file(Path(r.local_path))
                    except Exception as e:
                        sha = f"ERROR:{type(e).__name__}"
                w.writerow([r.repo_rel, r.local_path, r.raw_url, r.status, sha])
        else:
            w.writerow(["repo_relative_path", "local_full_path", "github_raw_url", "status"])
            for r in rows:
                w.writerow([r.repo_rel, r.local_path, r.raw_url, r.status])

    # Write Markdown
    write_log(log_path, "writing Markdown table...")
    md = []
    md.append(f"# my_TV_Movie — Repo File Map ({s})\n")
    md.append(f"- Repo root: `{repo_root}`\n")
    md.append(f"- GitHub: `https://github.com/{args.owner}/{args.repo}`\n")
    md.append(f"- Raw base: `https://raw.githubusercontent.com/{args.owner}/{args.repo}/refs/heads/{args.branch}/`\n")
    md.append(f"- Mode: `{'FULL' if args.full else 'KEY_ONLY'}`\n")

    if not args.full:
        md.append("## Key files (expected)\n")
    else:
        md.append("## Full inventory (filtered)\n")

    md.append(md_table(rows))

    if not args.full:
        md.append("## Summary\n")
        ok = sum(1 for r in rows if r.status == "OK")
        missing = sum(1 for r in rows if r.status == "MISSING_LOCAL")
        dup = sum(1 for r in rows if r.status == "DUPLICATE")
        md.append(f"- OK: {ok}\n")
        md.append(f"- Missing locally: {missing}\n")
        md.append(f"- Duplicate keys: {dup}\n")
        if missing_expected:
            md.append("\n### Missing expected files (local)\n")
            for p in missing_expected:
                md.append(f"- `{p}`\n")

    out_md.write_text("".join(md), encoding="utf-8")

    write_log(log_path, "SUCCESS")
    write_log(log_path, f"CSV: {out_csv}")
    write_log(log_path, f"MD : {out_md}")
    write_log(log_path, f"LOG: {log_path}")

    input("Press Enter to exit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
