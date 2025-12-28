#!/usr/bin/env python3
# ==============================================================================
# scripts/generate_repo_file_map.py
#
# Clean repo map:
# - Canonical paths first (your real repo structure)
# - Legacy/root aliases are allowed, but NEVER treated as missing if canonical exists
# - Outputs:
#   logs\_repo_file_map_<stamp>.log.txt
#   reports\_repo_file_map_<stamp>.csv
#   reports\_repo_file_map_<stamp>.md
# ==============================================================================

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple


@dataclass
class Row:
    repo_relative_path: str
    local_full_path: str
    github_raw_url: str
    status: str


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _posix(rel: str) -> str:
    return rel.replace("\\", "/").lstrip("/")


def _raw_url(owner: str, repo: str, branch: str, rel_posix: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{rel_posix}"


def _write_log(log_path: Path, msg: str) -> None:
    line = f"[{_now()}] {msg}"
    print(line)
    log_path.open("a", encoding="utf-8").write(line + "\n")


def _md_table(rows: Sequence[Row]) -> str:
    header = "| repo_relative_path | local_full_path | github_raw_url | status |\n|---|---|---|---|\n"
    lines: List[str] = []
    for r in rows:
        lines.append(
            f"| `{r.repo_relative_path}` | `{r.local_full_path}` | {r.github_raw_url} | **{r.status}** |"
        )
    return header + "\n".join(lines) + "\n"


def _iter_repo_files_filtered(repo_root: Path, exclude_dirs: Set[str]) -> List[Path]:
    out: List[Path] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if any(part in exclude_dirs for part in rel.parts):
            continue
        out.append(p)
    out.sort(key=lambda x: str(x).lower())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
    ap.add_argument("--owner", default="AJPnKW")
    ap.add_argument("--repo", default="my_TV_Movie")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--full", action="store_true", help="List full repo inventory (filtered).")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print(f"Repo root not found: {repo_root}")
        return 1

    logs_dir = repo_root / "logs"
    reports_dir = repo_root / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    s = _stamp()
    log_path = logs_dir / f"_repo_file_map_{s}.log.txt"
    csv_path = reports_dir / f"_repo_file_map_{s}.csv"
    md_path = reports_dir / f"_repo_file_map_{s}.md"

    _write_log(log_path, "START generate_repo_file_map")
    _write_log(log_path, f"repo_root: {repo_root}")
    _write_log(log_path, f"owner/repo: {args.owner}/{args.repo}")
    _write_log(log_path, f"branch: {args.branch}")
    _write_log(log_path, f"mode: {'FULL' if args.full else 'KEY_ONLY'}")
    _write_log(log_path, f"outputs: {csv_path.name}, {md_path.name}, {log_path.name}")

    # Canonical keys (your real structure)
    canonical_keys: List[str] = [
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
        "inputs/schema.json",
        "requirements.txt",
        "README.md",
    ]

    # Legacy aliases (old expectations)
    # If alias exists locally -> OK (root file truly exists)
    # Else if canonical exists -> ALIAS -> canonical (not missing)
    # Else -> MISSING_LOCAL
    legacy_alias_to_canonical: Dict[str, str] = {
        "fetch_tmdb.py": "scripts/fetch_tmdb.py",
        "fetch_trakt.py": "scripts/fetch_trakt.py",
        "sync_trakt.py": "scripts/sync_trakt.py",
        "movies_list.txt": "inputs/movies_list.txt",
        "tv_list.txt": "inputs/tv_list.txt",
        "watchlist.txt": "inputs/watchlist.txt",
        "show_pages.txt": "inputs/show_pages.txt",
        "livetv_list.txt": "inputs/livetv_list.txt",
    }

    exclude_dirs = {
        ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        "node_modules", "dist", "build", ".idea", ".vscode", "logs", "reports"
    }

    rows: List[Row] = []

    if args.full:
        files = _iter_repo_files_filtered(repo_root, exclude_dirs)
        _write_log(log_path, f"paths_to_process: {len(files)}")
        for i, p in enumerate(files, start=1):
            rel = p.relative_to(repo_root).as_posix()
            rows.append(
                Row(rel, str(p), _raw_url(args.owner, args.repo, args.branch, rel), "OK")
            )
            if i % 50 == 0 or i == len(files):
                _write_log(log_path, f"progress: {i}/{len(files)}")
    else:
        # Process canonical keys first
        canon = sorted(set(_posix(x) for x in canonical_keys), key=lambda x: x.lower())
        _write_log(log_path, f"paths_to_process (canonical): {len(canon)}")
        for rel in canon:
            p = repo_root / rel
            status = "OK" if p.exists() else "MISSING_LOCAL"
            rows.append(Row(rel, str(p), _raw_url(args.owner, args.repo, args.branch, rel), status))

        # Then append legacy aliases for visibility (but do not let them create fake "missing")
        legacy = sorted(set(_posix(x) for x in legacy_alias_to_canonical.keys()), key=lambda x: x.lower())
        _write_log(log_path, f"paths_to_process (legacy): {len(legacy)}")
        for alias in legacy:
            alias_path = repo_root / alias
            canon_rel = _posix(legacy_alias_to_canonical[alias])
            canon_path = repo_root / canon_rel

            if alias_path.exists():
                status = "OK (legacy file exists)"
                resolved = alias_path
            elif canon_path.exists():
                status = f"ALIAS -> {canon_rel}"
                resolved = canon_path
            else:
                status = "MISSING_LOCAL"
                resolved = alias_path

            rows.append(Row(alias, str(resolved), _raw_url(args.owner, args.repo, args.branch, alias), status))

    # Summary counts: only true missing rows count as missing
    missing = sum(1 for r in rows if r.status == "MISSING_LOCAL")
    ok = len(rows) - missing

    _write_log(log_path, f"summary_ok: {ok}")
    _write_log(log_path, f"summary_missing: {missing}")

    _write_log(log_path, "writing CSV...")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["repo_relative_path", "local_full_path", "github_raw_url", "status"])
        for r in rows:
            w.writerow([r.repo_relative_path, r.local_full_path, r.github_raw_url, r.status])

    _write_log(log_path, "writing Markdown table...")
    md: List[str] = []
    md.append(f"# my_TV_Movie — Repo File Map ({s})\n\n")
    md.append(f"- Repo root: `{repo_root}`\n")
    md.append(f"- GitHub: `https://github.com/{args.owner}/{args.repo}`\n")
    md.append(f"- Raw base: `https://raw.githubusercontent.com/{args.owner}/{args.repo}/refs/heads/{args.branch}/`\n")
    md.append(f"- Mode: `{'FULL' if args.full else 'KEY_ONLY (canonical + legacy aliases)'}`\n\n")
    md.append("## Files\n\n")
    md.append(_md_table(rows))
    md.append("\n## Summary\n\n")
    md.append(f"- OK: {ok}\n")
    md.append(f"- Missing locally: {missing}\n")

    md_path.write_text("".join(md), encoding="utf-8")

    _write_log(log_path, "SUCCESS")
    _write_log(log_path, f"CSV: {csv_path}")
    _write_log(log_path, f"MD : {md_path}")
    _write_log(log_path, f"LOG: {log_path}")

    input("Press Enter to exit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
