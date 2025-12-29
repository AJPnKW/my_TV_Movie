#!/usr/bin/env python3
# ==============================================================================
# generate_repo_file_map.py
#
# Interactive + CLI repo file mapper
# - Canonical pipeline-aware paths
# - Legacy aliases resolved (never false-missing)
# - Optional full inventory
# - Optional SHA256 hashing
#
# Outputs:
#   logs\_repo_file_map_<stamp>.log.txt
#   reports\_repo_file_map_<stamp>.csv
#   reports\_repo_file_map_<stamp>.md
# ==============================================================================

from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------

@dataclass
class Row:
    repo_relative_path: str
    local_full_path: str
    github_raw_url: str
    status: str
    sha256: str = ""


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def posix(p: str) -> str:
    return p.replace("\\", "/").lstrip("/")


def raw_url(owner: str, repo: str, branch: str, rel: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{rel}"


def sha256_file(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def log(log_path: Path, msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line)
    log_path.open("a", encoding="utf-8").write(line + "\n")


def md_table(rows: List[Row], include_hash: bool) -> str:
    if include_hash:
        header = "| repo_relative_path | local_full_path | github_raw_url | status | sha256 |\n"
        header += "|---|---|---|---|---|\n"
        body = "\n".join(
            f"| `{r.repo_relative_path}` | `{r.local_full_path}` | {r.github_raw_url} | **{r.status}** | `{r.sha256}` |"
            for r in rows
        )
    else:
        header = "| repo_relative_path | local_full_path | github_raw_url | status |\n"
        header += "|---|---|---|---|\n"
        body = "\n".join(
            f"| `{r.repo_relative_path}` | `{r.local_full_path}` | {r.github_raw_url} | **{r.status}** |"
            for r in rows
        )
    return header + body + "\n"


def iter_repo_files(repo_root: Path, exclude: Set[str]) -> List[Path]:
    out: List[Path] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in exclude for part in p.relative_to(repo_root).parts):
            continue
        out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
    ap.add_argument("--owner", default="AJPnKW")
    ap.add_argument("--repo", default="my_TV_Movie")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--hash", action="store_true")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    logs_dir = repo_root / "logs"
    reports_dir = repo_root / "reports"
    logs_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    s = stamp()
    log_path = logs_dir / f"_repo_file_map_{s}.log.txt"
    csv_path = reports_dir / f"_repo_file_map_{s}.csv"
    md_path = reports_dir / f"_repo_file_map_{s}.md"

    # ---------------- Menu (if no switches) ----------------
    if not args.full and not args.hash:
        print("\nSelect run mode:")
        print("  1) Key files only (default)")
        print("  2) Full repository inventory")
        print("  3) Key files + SHA256 hashes")
        print("  4) Full inventory + SHA256 hashes")
        choice = input("\nEnter choice [1-4]: ").strip()

        if choice == "2":
            args.full = True
        elif choice == "3":
            args.hash = True
        elif choice == "4":
            args.full = True
            args.hash = True

    log(log_path, "START generate_repo_file_map")
    log(log_path, f"repo_root: {repo_root}")
    log(log_path, f"mode: {'FULL' if args.full else 'KEY_ONLY'} | hash={'ON' if args.hash else 'OFF'}")

    canonical = [
        ".github/workflows/build-data.yml",
        "data/data.json",
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
        "inputs/schema.json",
        "web/index.html",
        "web/watchlist.html",
        "web/config.json",
        "web/config.html",
        "web/config.js",
        "requirements.txt",
        "README.md",
    ]

    legacy_alias = {
        "fetch_tmdb.py": "scripts/fetch_tmdb.py",
        "fetch_trakt.py": "scripts/fetch_trakt.py",
        "sync_trakt.py": "scripts/sync_trakt.py",
        "movies_list.txt": "inputs/movies_list.txt",
        "tv_list.txt": "inputs/tv_list.txt",
        "watchlist.txt": "inputs/watchlist.txt",
    }

    rows: List[Row] = []

    exclude_dirs = {
        ".git", ".venv", "venv", "__pycache__", "node_modules",
        "logs", "reports", ".idea", ".vscode"
    }

    if args.full:
        files = iter_repo_files(repo_root, exclude_dirs)
        for p in files:
            rel = p.relative_to(repo_root).as_posix()
            rows.append(
                Row(
                    rel,
                    str(p),
                    raw_url(args.owner, args.repo, args.branch, rel),
                    "OK",
                    sha256_file(p) if args.hash else ""
                )
            )
    else:
        for rel in canonical:
            rel = posix(rel)
            p = repo_root / rel
            rows.append(
                Row(
                    rel,
                    str(p),
                    raw_url(args.owner, args.repo, args.branch, rel),
                    "OK" if p.exists() else "MISSING_LOCAL",
                    sha256_file(p) if args.hash and p.exists() else ""
                )
            )

        for alias, canon in legacy_alias.items():
            alias_p = repo_root / alias
            canon_p = repo_root / canon
            if alias_p.exists():
                status = "OK (legacy)"
                resolved = alias_p
            elif canon_p.exists():
                status = f"ALIAS -> {canon}"
                resolved = canon_p
            else:
                status = "MISSING_LOCAL"
                resolved = alias_p

            rows.append(
                Row(
                    alias,
                    str(resolved),
                    raw_url(args.owner, args.repo, args.branch, alias),
                    status,
                    sha256_file(resolved) if args.hash and resolved.exists() else ""
                )
            )

    log(log_path, "writing CSV...")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        headers = ["repo_relative_path", "local_full_path", "github_raw_url", "status"]
        if args.hash:
            headers.append("sha256")
        w.writerow(headers)
        for r in rows:
            row = [r.repo_relative_path, r.local_full_path, r.github_raw_url, r.status]
            if args.hash:
                row.append(r.sha256)
            w.writerow(row)

    log(log_path, "writing Markdown...")
    md = [
        f"# my_TV_Movie Repo File Map ({s})\n\n",
        f"- Mode: {'FULL' if args.full else 'KEY_ONLY'}\n",
        f"- Hashing: {'ON' if args.hash else 'OFF'}\n\n",
        md_table(rows, args.hash),
    ]
    md_path.write_text("".join(md), encoding="utf-8")

    log(log_path, "SUCCESS")
    log(log_path, f"CSV: {csv_path}")
    log(log_path, f"MD : {md_path}")
    log(log_path, f"LOG: {log_path}")

    input("Press Enter to exit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
