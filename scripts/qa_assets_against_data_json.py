# [CAPABILITY] my_tv_movie_asset_qa=YES
# version: 1.0
# purpose: QA audit local assets referenced by data/data.json against actual files under assets/
# usage:
#   python qa_assets_against_data_json.py
#   python qa_assets_against_data_json.py --repo-root "C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie"

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DEFAULT_REPO_ROOT = Path(r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")

LOCAL_ASSET_PREFIXES = ("assets/", "assets\\")
LOCAL_ASSET_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

STRING_KEY_HINTS = {
    "poster_local", "backdrop_local", "still_local", "logo_local",
    "poster", "backdrop", "still", "logo", "image", "thumb", "thumbnail",
}

def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def safe_rel_to_repo(path_text: str) -> str | None:
    if not isinstance(path_text, str):
        return None
    txt = path_text.strip()
    if not txt:
        return None
    norm = txt.replace("\\", "/").lstrip("./")
    if norm.lower().startswith("http://") or norm.lower().startswith("https://"):
        return None
    if norm.startswith(LOCAL_ASSET_PREFIXES):
        return norm
    return None

def classify_asset(rel_path: str) -> str:
    p = rel_path.replace("\\", "/").lower()
    if "/posters/" in p:
        return "poster"
    if "/backdrops/" in p:
        return "backdrop"
    if "/stills/" in p:
        return "still"
    if "/logos/" in p:
        return "logo"
    return "other"

def entity_label(context: dict[str, Any]) -> str:
    parts = [context.get("entity_type", "unknown")]
    if context.get("show_title"):
        parts.append(f"show={context['show_title']}")
    if context.get("movie_title"):
        parts.append(f"movie={context['movie_title']}")
    if context.get("season_number") is not None:
        parts.append(f"season={context['season_number']}")
    if context.get("episode_number") is not None:
        parts.append(f"episode={context['episode_number']}")
    if context.get("title"):
        parts.append(f"title={context['title']}")
    if context.get("tmdb_id") is not None:
        parts.append(f"tmdb_id={context['tmdb_id']}")
    return " | ".join(parts)

def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def collect_local_asset_refs(obj: Any, context: dict[str, Any], out: list[dict[str, Any]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                rel = safe_rel_to_repo(v)
                if rel and (k in STRING_KEY_HINTS or any(seg in rel.lower() for seg in ("posters/", "backdrops/", "stills/", "logos/"))):
                    out.append({
                        "entity_type": context.get("entity_type", "unknown"),
                        "tmdb_id": context.get("tmdb_id"),
                        "title": context.get("title"),
                        "show_title": context.get("show_title"),
                        "movie_title": context.get("movie_title"),
                        "season_number": context.get("season_number"),
                        "episode_number": context.get("episode_number"),
                        "json_key": k,
                        "asset_path": rel,
                        "asset_type": classify_asset(rel),
                    })
            elif isinstance(v, (dict, list)):
                collect_local_asset_refs(v, context, out)
    elif isinstance(obj, list):
        for item in obj:
            collect_local_asset_refs(item, context, out)

def build_show_context(show: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_type": "show",
        "tmdb_id": show.get("tmdb_id") or show.get("id"),
        "title": show.get("title") or show.get("name"),
        "show_title": show.get("title") or show.get("name"),
    }

def build_movie_context(movie: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_type": "movie",
        "tmdb_id": movie.get("tmdb_id") or movie.get("id"),
        "title": movie.get("title") or movie.get("name"),
        "movie_title": movie.get("title") or movie.get("name"),
    }

def collect_entities_and_refs(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []

    for show in data.get("shows", []):
        show_ctx = build_show_context(show)
        entities.append({
            **show_ctx,
            "entity_type": "show",
        })
        collect_local_asset_refs(show, show_ctx, refs)

        for season in show.get("seasons", []) or []:
            season_ctx = {
                **show_ctx,
                "entity_type": "season",
                "title": season.get("name") or f"Season {season.get('season_number')}",
                "season_number": season.get("season_number") or season.get("number"),
            }
            entities.append({**season_ctx})
            collect_local_asset_refs(season, season_ctx, refs)

            for ep in season.get("episodes", []) or []:
                ep_ctx = {
                    **show_ctx,
                    "entity_type": "episode",
                    "title": ep.get("title") or ep.get("name") or f"Episode {ep.get('episode_number')}",
                    "season_number": season_ctx.get("season_number"),
                    "episode_number": ep.get("episode_number") or ep.get("number"),
                }
                entities.append({**ep_ctx})
                collect_local_asset_refs(ep, ep_ctx, refs)

    for movie in data.get("movies", []):
        movie_ctx = build_movie_context(movie)
        entities.append({
            **movie_ctx,
            "entity_type": "movie",
        })
        collect_local_asset_refs(movie, movie_ctx, refs)

    return entities, refs

def asset_presence_summary(repo_root: Path, refs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter]:
    checked: list[dict[str, Any]] = []
    counts = Counter()
    seen = set()

    for ref in refs:
        key = (
            ref["entity_type"], ref.get("tmdb_id"), ref.get("season_number"),
            ref.get("episode_number"), ref["json_key"], ref["asset_path"]
        )
        if key in seen:
            continue
        seen.add(key)
        abs_path = repo_root / ref["asset_path"].replace("/", os.sep)
        exists = abs_path.exists()
        row = dict(ref)
        row["asset_exists"] = exists
        row["asset_abs_path"] = str(abs_path)
        checked.append(row)
        counts["referenced_total"] += 1
        counts[f"referenced_{ref['asset_type']}"] += 1
        if exists:
            counts["matched_total"] += 1
            counts[f"matched_{ref['asset_type']}"] += 1
        else:
            counts["missing_total"] += 1
            counts[f"missing_{ref['asset_type']}"] += 1

    return checked, counts

def scan_actual_assets(repo_root: Path) -> list[str]:
    assets_root = repo_root / "assets"
    if not assets_root.exists():
        return []
    rels = []
    for path in assets_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in LOCAL_ASSET_EXTS:
            rels.append(path.relative_to(repo_root).as_posix())
    return sorted(rels)

def summarize_missing_entities(checked: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    missing_rows = [r for r in checked if not r["asset_exists"]]

    movie_map: dict[tuple[Any, str], dict[str, Any]] = {}
    show_map: dict[tuple[Any, str], dict[str, Any]] = {}

    for row in missing_rows:
        if row["entity_type"] == "movie":
            key = (row.get("tmdb_id"), row.get("title"))
            entry = movie_map.setdefault(key, {
                "entity_type": "movie",
                "tmdb_id": row.get("tmdb_id"),
                "title": row.get("title"),
                "missing_asset_types": set(),
                "missing_paths": [],
            })
            entry["missing_asset_types"].add(row["asset_type"])
            entry["missing_paths"].append(row["asset_path"])
        elif row["entity_type"] in {"show", "season", "episode"}:
            key = (row.get("tmdb_id"), row.get("show_title"))
            entry = show_map.setdefault(key, {
                "entity_type": "show_family",
                "tmdb_id": row.get("tmdb_id"),
                "show_title": row.get("show_title"),
                "show_missing": False,
                "season_missing_count": 0,
                "episode_missing_count": 0,
                "missing_asset_types": set(),
                "missing_paths": [],
            })
            entry["missing_asset_types"].add(row["asset_type"])
            entry["missing_paths"].append(row["asset_path"])
            if row["entity_type"] == "show":
                entry["show_missing"] = True
            elif row["entity_type"] == "season":
                entry["season_missing_count"] += 1
            elif row["entity_type"] == "episode":
                entry["episode_missing_count"] += 1

    movie_rows = []
    for v in movie_map.values():
        movie_rows.append({
            "entity_type": v["entity_type"],
            "tmdb_id": v["tmdb_id"],
            "title": v["title"],
            "missing_asset_types": ", ".join(sorted(v["missing_asset_types"])),
            "missing_count": len(v["missing_paths"]),
            "missing_paths": " | ".join(v["missing_paths"][:10]),
        })

    show_rows = []
    for v in show_map.values():
        show_rows.append({
            "entity_type": v["entity_type"],
            "tmdb_id": v["tmdb_id"],
            "show_title": v["show_title"],
            "show_missing": v["show_missing"],
            "season_missing_count": v["season_missing_count"],
            "episode_missing_count": v["episode_missing_count"],
            "missing_asset_types": ", ".join(sorted(v["missing_asset_types"])),
            "missing_count": len(v["missing_paths"]),
            "missing_paths": " | ".join(v["missing_paths"][:10]),
        })

    movie_rows.sort(key=lambda r: (r["title"] or ""))
    show_rows.sort(key=lambda r: (r["show_title"] or ""))
    return movie_rows, show_rows

def build_console_summary(counts: Counter, orphan_count: int, movie_missing: list[dict[str, Any]], show_missing: list[dict[str, Any]]) -> str:
    lines = []
    lines.append("ASSET QA SUMMARY")
    lines.append("----------------")
    lines.append(f"Referenced local assets: {counts['referenced_total']}")
    lines.append(f"Matched local assets:    {counts['matched_total']}")
    lines.append(f"Missing local assets:    {counts['missing_total']}")
    lines.append(f"Orphan local assets:     {orphan_count}")
    lines.append("")
    lines.append("By type")
    for asset_type in ("poster", "backdrop", "still", "logo", "other"):
        lines.append(
            f"  {asset_type:<9} referenced={counts[f'referenced_{asset_type}']:<5} "
            f"matched={counts[f'matched_{asset_type}']:<5} missing={counts[f'missing_{asset_type}']:<5}"
        )
    lines.append("")
    lines.append(f"Movies with missing local assets: {len(movie_missing)}")
    for row in movie_missing[:20]:
        lines.append(f"  - {row['title']} | tmdb_id={row['tmdb_id']} | types={row['missing_asset_types']}")
    lines.append("")
    lines.append(f"Shows with missing show/season/episode assets: {len(show_missing)}")
    for row in show_missing[:20]:
        lines.append(
            f"  - {row['show_title']} | tmdb_id={row['tmdb_id']} | "
            f"show_missing={row['show_missing']} season_missing={row['season_missing_count']} "
            f"episode_missing={row['episode_missing_count']} | types={row['missing_asset_types']}"
        )
    return "\n".join(lines)

def zip_folder(folder: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(folder.parent))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    data_path = repo_root / "data" / "data.json"
    if not data_path.exists():
        print(f"ERROR: not found: {data_path}")
        return 1

    data = load_json(data_path)
    entities, refs = collect_entities_and_refs(data)
    checked, counts = asset_presence_summary(repo_root, refs)

    actual_assets = scan_actual_assets(repo_root)
    referenced_set = {r["asset_path"] for r in checked}
    orphan_assets = [p for p in actual_assets if p not in referenced_set]

    movie_missing, show_missing = summarize_missing_entities(checked)

    ts = now_stamp()
    out_dir = repo_root / "logs" / f"asset_qa_{ts}"
    ensure_dir(out_dir)

    write_json(out_dir / "asset_reference_check.json", checked)
    write_json(out_dir / "orphan_assets.json", orphan_assets)
    write_json(out_dir / "movie_missing_assets.json", movie_missing)
    write_json(out_dir / "show_missing_assets.json", show_missing)

    write_csv(out_dir / "asset_reference_check.csv", checked)
    write_csv(out_dir / "movie_missing_assets.csv", movie_missing)
    write_csv(out_dir / "show_missing_assets.csv", show_missing)
    write_csv(out_dir / "orphan_assets.csv", [{"asset_path": p, "asset_type": classify_asset(p)} for p in orphan_assets])

    summary = {
        "repo_root": str(repo_root),
        "data_json": str(data_path),
        "referenced_total": counts["referenced_total"],
        "matched_total": counts["matched_total"],
        "missing_total": counts["missing_total"],
        "orphan_total": len(orphan_assets),
        "referenced_by_type": {k.replace("referenced_", ""): v for k, v in counts.items() if k.startswith("referenced_")},
        "matched_by_type": {k.replace("matched_", ""): v for k, v in counts.items() if k.startswith("matched_")},
        "missing_by_type": {k.replace("missing_", ""): v for k, v in counts.items() if k.startswith("missing_")},
        "movies_with_missing_assets": len(movie_missing),
        "shows_with_missing_assets": len(show_missing),
    }
    write_json(out_dir / "summary.json", summary)

    summary_txt = build_console_summary(counts, len(orphan_assets), movie_missing, show_missing)
    (out_dir / "summary.txt").write_text(summary_txt, encoding="utf-8")

    zip_path = repo_root / "logs" / f"asset_qa_{ts}.zip"
    zip_folder(out_dir, zip_path)

    print(summary_txt)
    print("")
    print(f"Detailed report folder: {out_dir}")
    print(f"Zip bundle: {zip_path}")
    input("Press ENTER to exit...")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
