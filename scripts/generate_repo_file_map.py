#!/usr/bin/env python3
# ==============================================================================
# FILE: scripts/generate_repo_file_map.py
#
# PURPOSE:
#   Generate a repo file listing, extrapolate GitHub RAW URLs for main branch,
#   validate local existence under repo root, and output a 4-column table:
#     1) repo_relative_path
#     2) local_full_path
#     3) github_raw_url
#     4) status (OK / MISSING_LOCAL / DUPLICATE / ERROR)
#
# OUTPUTS:
#   - LOG:     <repo>\logs\_repo_file_map_<timestamp>.log.txt
#   - REPORTS: <repo>\reports\_repo_file_map_<timestamp>.csv
#              <repo>\reports\_repo_file_map_<timestamp>.md
#
# NOTES:
#   - KEY_ONLY by default uses YOUR repo's current structure:
#       scripts/* pipeline scripts
#       inputs/* input lists
#       web/* ui + config
#       data/data.json
#       .github/workflows/build-data.yml (or build-data.yaml)
#   - --full includes full repo inventory (filtered)
#   - Deterministic ordering
#   - No silent failures
#   - Waits for Enter at end
# ==============================================================================

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Set


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_posix(rel: str) -> str:
    return rel.replace("\\", "/").lstrip("/")


def build_raw_url(owner: str, repo: str, branch: str, repo_rel_posix: str) -> str:
    # Required format:
    # https://raw.githubusercontent.com/AJPnKW/my_TV_Movie/refs/heads/main/web/index.html
    return f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{repo_rel_posix}"


def md_table(rows: Sequence[Row]) -> str:
    header = "| repo_relative_path | local_full_path | github_raw_url | status |\n|---|---|---|---|\n"
    lines = []
    for r in rows:
        repo_rel = r.repo_rel.replace("|", "\\|")
        local_path = r.local_path.replace("|", "\\|")
        raw_url = r.raw_url.replace("|", "\\|")
        status = r.status.replace("|", "\\|")
        lines.append(f"| `{repo_rel}` | `{local_path}` | {raw_url} | **{status}** |")
    return header + "\n".join(lines) + "\n"


def iter_glob_files(repo_root: Path, rel_glob: str) -> List[Path]:
    rel_glob_norm = rel_glob.replace("\\", "/")
    out: List[Path] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root).as_posix()
        if fnmatch.fnmatch(rel, rel_glob_norm):
            out.append(p)
    out.sort(key=lambda x: str(x).lower())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--repo-root", default=r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
    parser.add_argument("--owner", default="AJPnKW")
    parser.add_argument("--repo", default="my_TV_Movie")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--full", action="store_true", help="Include full repo inventory (filtered).")
    parser.add_argument("--hash", action="store_true", help="Add SHA256 column to CSV (local files only).")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"Repo root not found: {repo_root}")
        return 1

    logs_dir = repo_root / "logs"
    reports_dir = repo_root / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    s = stamp()
    out_csv = reports_dir / f"_repo_file_map_{s}.csv"
    out_md = reports_dir / f"_repo_file_map_{s}.md"
    log_path = logs_dir / f"_repo_file_map_{s}.log.txt"

    write_log(log_path, "START generate_repo_file_map")
    write_log(log_path, f"repo_root: {repo_root}")
    write_log(log_path, f"owner/repo: {args.owner}/{args.repo}")
    write_log(log_path, f"branch: {args.branch}")
    write_log(log_path, f"mode: {'FULL' if args.full else 'KEY_ONLY'}")
    write_log(log_path, f"outputs: {out_csv.name}, {out_md.name}, {log_path.name}")

    # KEY FILES: aligned to YOUR repo structure (as per your directory listing)
    key_rel_paths: List[str] = [
        ".github/workflows/build-data.yml",
        ".github/workflows/build-data.yaml",
        "data/data.json",
        "web/index.html",
        "web/watchlist.html",
        "web/config.json",
        "web/config.html",
        "web/config.js",
        "scripts/fetch_tmdb.py",
        "scripts/fetch_trakt.py",
        "scripts/sync_trakt.py",
        "scripts/fetch_tvmaze.py",
        "scripts/parse_txt_to_json.py",
        "inputs/movies_list.txt",
        "inputs/tv_list.txt",
        "inputs/watchlist.txt",
        "inputs/show_pages.txt",
        "inputs/livetv_list.txt",
        "requirements.txt",
        "README.md",
    ]

    # FULL inventory excludes noisy folders
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

    # Build candidate list
    if args.full:
        rel_candidates: List[str] = []
        for p in repo_root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(repo_root)
            if any(part in exclude_dirs for part in rel.parts):
                continue
            rel_candidates.append(rel.as_posix())
    else:
        rel_candidates = [to_posix(x) for x in key_rel_paths]

    # de-dupe + deterministic sort
    rel_candidates = sorted(set(rel_candidates), key=lambda x: x.lower())

    # duplicate detection (only meaningful for key-only)
    dupes = {}
    if not args.full:
        for p in [to_posix(x) for x in key_rel_paths]:
            dupes[p] = dupes.get(p, 0) + 1

    rows: List[Row] = []
    write_log(log_path, f"paths_to_process: {len(rel_candidates)}")

    for i, rel in enumerate(rel_candidates, start=1):
        local = repo_root / rel
        raw = build_raw_url(args.owner, args.repo, args.branch, rel)

        status = "OK"
        if not local.exists():
            status = "MISSING_LOCAL"
        if not args.full and dupes.get(rel, 0) > 1:
            status = "DUPLICATE"

        rows.append(Row(repo_rel=rel, local_path=str(local), raw_url=raw, status=status))

        if i % 25 == 0 or i == len(rel_candidates):
            write_log(log_path, f"progress: {i}/{len(rel_candidates)}")

    ok = sum(1 for r in rows if r.status == "OK")
    missing = sum(1 for r in rows if r.status == "MISSING_LOCAL")
    dup = sum(1 for r in rows if r.status == "DUPLICATE")

    # CSV
    write_log(log_path, "writing CSV...")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if args.hash:
            w.writerow(["repo_relative_path", "local_full_path", "github_raw_url", "status", "local_sha256"])
            for r in rows:
                sha = ""
                p = Path(r.local_path)
                if p.exists() and p.is_file():
                    try:
                        sha = sha256_file(p)
                    except Exception as e:
                        sha = f"ERROR:{type(e).__name__}"
                w.writerow([r.repo_rel, r.local_path, r.raw_url, r.status, sha])
        else:
            w.writerow(["repo_relative_path", "local_full_path", "github_raw_url", "status"])
            for r in rows:
                w.writerow([r.repo_rel, r.local_path, r.raw_url, r.status])

    # Markdown
    write_log(log_path, "writing Markdown table...")
    md: List[str] = []
    md.append(f"# my_TV_Movie — Repo File Map ({s})\n\n")
    md.append(f"- Repo root: `{repo_root}`\n")
    md.append(f"- GitHub: `https://github.com/{args.owner}/{args.repo}`\n")
    md.append(f"- Raw base: `https://raw.githubusercontent.com/{args.owner}/{args.repo}/refs/heads/{args.branch}/`\n")
    md.append(f"- Mode: `{'FULL' if args.full else 'KEY_ONLY'}`\n\n")
    md.append("## Files\n\n")
    md.append(md_table(rows))
    md.append("\n## Summary\n\n")
    md.append(f"- OK: {ok}\n")
    md.append(f"- Missing locally: {missing}\n")
    md.append(f"- Duplicate keys: {dup}\n")

    out_md.write_text("".join(md), encoding="utf-8")

    write_log(log_path, "SUCCESS")
    write_log(log_path, f"CSV: {out_csv}")
    write_log(log_path, f"MD : {out_md}")
    write_log(log_path, f"LOG: {log_path}")

    input("Press Enter to exit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
