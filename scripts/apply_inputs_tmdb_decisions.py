#!/usr/bin/env python3
# =============================================================================
# apply_inputs_tmdb_decisions.py
# Version: 0.1.0
#
# Purpose:
#   Apply your decisions from _inputs_tmdb_decisions.tsv to data/inputs.json.
#
# Input TSV columns (required):
#   GROUP, BUCKET, INDEX, SLUG, LOCAL_TITLE, LOCAL_TMDB_ID, ...,
#   DECISION, NEW_BUCKET, NEW_TMDB_ID, NOTES
#
# Decisions supported:
#   - KEEP                 : no change
#   - FIX_ID               : set tmdb_id to NEW_TMDB_ID (same bucket)
#   - MOVE_BUCKET          : move item to NEW_BUCKET (same tmdb_id)
#   - FIX_ID_AND_BUCKET    : move + set tmdb_id
#   - DELETE               : remove item
#
# Output:
#   - data/inputs.json updated in-place (atomic write) + backup:
#       data/inputs.json.bak_decisions
#   - _apply_inputs_tmdb_decisions.report.json
#   - _apply_inputs_tmdb_decisions.log.txt
#
# Usage (repo root):
#   python .\scripts\apply_inputs_tmdb_decisions.py
# =============================================================================

from __future__ import annotations

import json
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT = "apply_inputs_tmdb_decisions.py"
VERSION = "0.1.0"

REPO_ROOT = Path.cwd()
INPUTS_PATH = REPO_ROOT / "data" / "inputs.json"
BACKUP_PATH = REPO_ROOT / "data" / "inputs.json.bak_decisions"
TSV_PATH = REPO_ROOT / "_inputs_tmdb_decisions.tsv"
REPORT_PATH = REPO_ROOT / "_apply_inputs_tmdb_decisions.report.json"
LOG_PATH = REPO_ROOT / "_apply_inputs_tmdb_decisions.log.txt"


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def read_tsv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f.readlines()]
    if not lines:
        return []
    headers = lines[0].split("\t")
    out: List[Dict[str, str]] = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        parts = ln.split("\t")
        row = {headers[i]: (parts[i] if i < len(parts) else "") for i in range(len(headers))}
        out.append(row)
    return out


def _as_list(x: Any) -> List[Dict[str, Any]]:
    return x if isinstance(x, list) else []


def get_group_list(doc: Dict[str, Any], group: str) -> Tuple[List[Dict[str, Any]], str]:
    # returns (list_ref, bucket_kind movie|tv|unknown)
    if group == "movies":
        return _as_list(doc.setdefault("movies", [])), "movie"
    if group == "tv":
        return _as_list(doc.setdefault("tv", [])), "tv"

    if group.startswith("watchlist"):
        w = doc.setdefault("watchlist", {})
        if isinstance(w, list):
            # legacy list shape; treat as unknown list
            return w, "unknown"
        if not isinstance(w, dict):
            doc["watchlist"] = {}
            w = doc["watchlist"]

        if group == "watchlist.movies":
            return _as_list(w.setdefault("movies", [])), "movie"
        if group == "watchlist.tv":
            return _as_list(w.setdefault("tv", [])), "tv"
        if group == "watchlist":
            # if a dict, we can't represent a single list; treat as tv list by default? NO.
            # refuse to apply to this ambiguous target.
            raise RuntimeError("TSV uses GROUP=watchlist but inputs.json watchlist is an object. Use watchlist.movies or watchlist.tv.")

    raise RuntimeError(f"Unknown GROUP: {group}")


def move_item(doc: Dict[str, Any], src_group: str, src_index: int, dst_bucket: str) -> Dict[str, Any]:
    src_list, _ = get_group_list(doc, src_group)
    if src_index < 0 or src_index >= len(src_list):
        raise IndexError(f"Index out of range: {src_group}[{src_index}]")
    item = src_list.pop(src_index)

    # destination group determined by dst_bucket only
    if dst_bucket == "movie":
        dst_list, _ = get_group_list(doc, "movies")
    elif dst_bucket == "tv":
        dst_list, _ = get_group_list(doc, "tv")
    else:
        raise ValueError("NEW_BUCKET must be 'movie' or 'tv'")

    dst_list.append(item)
    return item


def main() -> int:
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    log(f"{SCRIPT} v{VERSION} start")
    log(f"inputs={INPUTS_PATH}")
    log(f"tsv={TSV_PATH}")

    if not INPUTS_PATH.exists():
        print(f"ERROR: Not found: {INPUTS_PATH}", file=sys.stderr)
        return 2
    if not TSV_PATH.exists():
        print(f"ERROR: Not found: {TSV_PATH}", file=sys.stderr)
        return 2

    doc = load_json(INPUTS_PATH)
    if not isinstance(doc, dict):
        print("ERROR: inputs.json root must be an object", file=sys.stderr)
        return 2

    original = deepcopy(doc)

    rows = read_tsv(TSV_PATH)
    applied: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    # apply in descending INDEX per GROUP to keep indices stable for deletes/fixes
    # we still key by GROUP+INDEX as the primary locator (deterministic).
    by_group: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        decision = (r.get("DECISION") or "").strip().upper()
        if not decision or decision == "KEEP":
            continue
        g = (r.get("GROUP") or "").strip()
        by_group.setdefault(g, []).append(r)

    for g, items in by_group.items():
        # sort desc index
        def _idx(rr: Dict[str, str]) -> int:
            try:
                return int(rr.get("INDEX") or -1)
            except Exception:
                return -1
        items.sort(key=_idx, reverse=True)

        for r in items:
            decision = (r.get("DECISION") or "").strip().upper()
            slug = (r.get("SLUG") or "").strip()
            title = (r.get("LOCAL_TITLE") or "").strip()
            try:
                idx = int(r.get("INDEX") or -1)
            except Exception:
                skipped.append({"group": g, "index": r.get("INDEX"), "slug": slug, "reason": "bad_index"})
                continue

            try:
                lst, _ = get_group_list(doc, g)
                if idx < 0 or idx >= len(lst):
                    skipped.append({"group": g, "index": idx, "slug": slug, "reason": "index_out_of_range"})
                    continue

                if decision == "DELETE":
                    removed = lst.pop(idx)
                    applied.append({"decision": "DELETE", "group": g, "index": idx, "slug": removed.get("slug"), "title": removed.get("title")})
                    log(f"DELETE {g}[{idx}] {slug}")
                    continue

                if decision in ("FIX_ID", "FIX_ID_AND_BUCKET"):
                    new_id_raw = (r.get("NEW_TMDB_ID") or "").strip()
                    if not new_id_raw:
                        skipped.append({"group": g, "index": idx, "slug": slug, "reason": "missing_new_tmdb_id"})
                        continue
                    try:
                        new_id = int(new_id_raw)
                    except Exception:
                        skipped.append({"group": g, "index": idx, "slug": slug, "reason": "bad_new_tmdb_id"})
                        continue
                    lst[idx]["tmdb_id"] = new_id
                    applied.append({"decision": "FIX_ID", "group": g, "index": idx, "slug": lst[idx].get("slug"), "title": lst[idx].get("title"), "new_tmdb_id": new_id})
                    log(f"FIX_ID {g}[{idx}] {slug} -> {new_id}")

                if decision in ("MOVE_BUCKET", "FIX_ID_AND_BUCKET"):
                    new_bucket = (r.get("NEW_BUCKET") or "").strip().lower()
                    if new_bucket not in ("movie", "tv"):
                        skipped.append({"group": g, "index": idx, "slug": slug, "reason": "bad_new_bucket"})
                        continue
                    moved_item = move_item(doc, g, idx, new_bucket)
                    applied.append({"decision": "MOVE_BUCKET", "from": g, "from_index": idx, "to_bucket": new_bucket, "slug": moved_item.get("slug"), "title": moved_item.get("title")})
                    log(f"MOVE {g}[{idx}] {slug} -> {new_bucket}")

                if decision not in ("FIX_ID", "MOVE_BUCKET", "FIX_ID_AND_BUCKET", "DELETE", "KEEP"):
                    skipped.append({"group": g, "index": idx, "slug": slug, "reason": f"unknown_decision:{decision}"})

            except Exception as e:
                skipped.append({"group": g, "index": idx, "slug": slug, "title": title, "reason": f"exception:{e}"})

    # write backup + updated file
    save_json(BACKUP_PATH, original)
    save_json(INPUTS_PATH, doc)

    report = {
        "meta": {
            "script": SCRIPT,
            "version": VERSION,
            "inputs": str(INPUTS_PATH),
            "backup": str(BACKUP_PATH),
            "tsv": str(TSV_PATH),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "counts": {"applied": len(applied), "skipped": len(skipped)},
        "applied": applied,
        "skipped": skipped,
    }
    save_json(REPORT_PATH, report)

    print(f"Updated: {INPUTS_PATH}")
    print(f"Backup:  {BACKUP_PATH}")
    print(f"Report:  {REPORT_PATH}")
    print(f"Log:     {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
