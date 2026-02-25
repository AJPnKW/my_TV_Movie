# FILE: scripts\qa_fix_duplicate_show_objects_in_data_json.py
# PURPOSE: Merge duplicate show objects in data/data.json that share the same tmdb_id (root cause of episode dupes in Watch Me).
# RUN:
#   py -3 -m py_compile scripts\qa_fix_duplicate_show_objects_in_data_json.py
#   py -3 scripts\qa_fix_duplicate_show_objects_in_data_json.py
#
# OUTPUT:
#   out/qa_episode_dupes/<stamp>/data.json.fixed.preview (written) + report.json + report.txt
#
# RULES:
# - Keep 1 show object per tmdb_id.
# - Merge show-level fields preferring the "best" (non-empty; longer lists).
# - Merge seasons by season_number; merge episodes by episode_number.
# - Episode merge: prefer non-empty fields; if both have values and differ, keep first and log conflict.
# - Stable ordering: preserve first-seen order of tmdb_id; seasons/episodes sorted numerically.

import copy
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "data.json"
OUT_ROOT = ROOT / "out" / "qa_episode_dupes"

def clean_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()

def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return clean_str(v) == ""
    if isinstance(v, list):
        return len(v) == 0
    if isinstance(v, dict):
        return len(v) == 0
    return False

def pick_better(a: Any, b: Any) -> Any:
    # Prefer non-empty; for lists/dicts prefer larger; otherwise keep a.
    if is_empty(a) and not is_empty(b):
        return copy.deepcopy(b)
    if not is_empty(a) and is_empty(b):
        return a
    if isinstance(a, list) and isinstance(b, list):
        return a if len(a) >= len(b) else copy.deepcopy(b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a if len(a) >= len(b) else copy.deepcopy(b)
    return a

def merge_dict_preferring_first(base: Dict[str, Any], other: Dict[str, Any], conflicts: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (other or {}).items():
        if k not in out:
            out[k] = copy.deepcopy(v)
            continue

        a = out[k]

        # nested dict merge
        if isinstance(a, dict) and isinstance(v, dict):
            out[k] = merge_dict_preferring_first(a, v, conflicts, {**ctx, "path": f"{ctx.get('path','')}.{k}".strip(".")})
            continue

        # lists: keep longer non-empty
        if isinstance(a, list) and isinstance(v, list):
            out[k] = pick_better(a, v)
            continue

        # scalars: prefer non-empty; if both non-empty and differ, log
        if is_empty(a) and not is_empty(v):
            out[k] = copy.deepcopy(v)
            continue

        if not is_empty(a) and not is_empty(v) and a != v:
            conflicts.append({
                **ctx,
                "field": k,
                "kept": a,
                "dropped": v,
            })
            continue

    return out

def index_by_number(items: List[Dict[str, Any]], key: str) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for it in items or []:
        n = it.get(key)
        if isinstance(n, int):
            out[n] = it
    return out

def merge_episode(a: Dict[str, Any], b: Dict[str, Any], conflicts: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    # Keep a as base
    out = merge_dict_preferring_first(a, b, conflicts, ctx)
    return out

def merge_season(a: Dict[str, Any], b: Dict[str, Any], conflicts: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    out = merge_dict_preferring_first(a, b, conflicts, ctx)

    eps_a = a.get("episodes") or []
    eps_b = b.get("episodes") or []

    by_en: Dict[int, Dict[str, Any]] = {}
    order: List[int] = []

    for ep in eps_a:
        en = ep.get("episode_number")
        if isinstance(en, int):
            by_en[en] = copy.deepcopy(ep)
            order.append(en)

    for ep in eps_b:
        en = ep.get("episode_number")
        if not isinstance(en, int):
            continue
        if en not in by_en:
            by_en[en] = copy.deepcopy(ep)
            order.append(en)
        else:
            by_en[en] = merge_episode(by_en[en], ep, conflicts, {**ctx, "episode_number": en, "path": f"{ctx.get('path','')}.episodes[{en}]".strip(".")})

    order_sorted = sorted(set(order))
    out["episodes"] = [by_en[n] for n in order_sorted]
    return out

def merge_show(a: Dict[str, Any], b: Dict[str, Any], conflicts: List[Dict[str, Any]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    out = merge_dict_preferring_first(a, b, conflicts, ctx)

    seasons_a = a.get("seasons") or []
    seasons_b = b.get("seasons") or []

    by_sn: Dict[int, Dict[str, Any]] = {}
    order: List[int] = []

    for s in seasons_a:
        sn = s.get("season_number")
        if isinstance(sn, int):
            by_sn[sn] = copy.deepcopy(s)
            order.append(sn)

    for s in seasons_b:
        sn = s.get("season_number")
        if not isinstance(sn, int):
            continue
        if sn not in by_sn:
            by_sn[sn] = copy.deepcopy(s)
            order.append(sn)
        else:
            by_sn[sn] = merge_season(by_sn[sn], s, conflicts, {**ctx, "season_number": sn, "path": f"{ctx.get('path','')}.seasons[{sn}]".strip(".")})

    order_sorted = sorted(set(order))
    out["seasons"] = [by_sn[n] for n in order_sorted]
    return out

def episode_dupe_count(shows: List[Dict[str, Any]]) -> int:
    # count duplicate (sid,sn,en) keys
    seen = set()
    dup = 0
    for s in shows or []:
        sid = s.get("tmdb_id")
        if not isinstance(sid, int):
            continue
        for season in (s.get("seasons") or []):
            sn = season.get("season_number")
            if not isinstance(sn, int):
                continue
            for ep in (season.get("episodes") or []):
                en = ep.get("episode_number")
                if not isinstance(en, int):
                    continue
                key = (sid, sn, en)
                if key in seen:
                    dup += 1
                else:
                    seen.add(key)
    return dup

def main() -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    shows: List[Dict[str, Any]] = data.get("shows", []) or []

    before_dupes = episode_dupe_count(shows)

    by_id: Dict[int, Dict[str, Any]] = {}
    order: List[int] = []
    merges: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    for idx, s in enumerate(shows):
        sid = s.get("tmdb_id")
        if not isinstance(sid, int):
            continue
        if sid not in by_id:
            by_id[sid] = copy.deepcopy(s)
            order.append(sid)
        else:
            merges.append({"tmdb_id": sid, "merged_in_index": idx})
            by_id[sid] = merge_show(by_id[sid], s, conflicts, {"tmdb_id": sid, "show_index": idx, "path": "show"})

    merged_shows = [by_id[sid] for sid in order]
    after_dupes = episode_dupe_count(merged_shows)

    fixed = copy.deepcopy(data)
    fixed["shows"] = merged_shows

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    out_preview = out_dir / "data.json.fixed.preview"
    out_report_json = out_dir / "fix_duplicate_shows_report.json"
    out_report_txt = out_dir / "fix_duplicate_shows_report.txt"

    out_preview.write_text(json.dumps(fixed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "data_path": str(DATA_PATH),
        "shows_before": len(shows),
        "shows_after": len(merged_shows),
        "duplicate_show_groups_merged": len({m["tmdb_id"] for m in merges}),
        "merge_events": len(merges),
        "episode_dupe_count_before": before_dupes,
        "episode_dupe_count_after": after_dupes,
        "conflicts_logged": len(conflicts),
        "note": "If episode_dupe_count_after==0, Watch Me dupes were caused by duplicate show objects in data.json sharing the same tmdb_id."
    }
    out_report_json.write_text(json.dumps({"report": report, "conflicts_sample_50": conflicts[:50]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = []
    lines.append(f"DATA={DATA_PATH}")
    lines.append(f"SHOWS_BEFORE={len(shows)}")
    lines.append(f"SHOWS_AFTER={len(merged_shows)}")
    lines.append(f"DUP_SHOW_GROUPS_MERGED={len({m['tmdb_id'] for m in merges})}")
    lines.append(f"MERGE_EVENTS={len(merges)}")
    lines.append(f"EPISODE_DUPE_COUNT_BEFORE={before_dupes}")
    lines.append(f"EPISODE_DUPE_COUNT_AFTER={after_dupes}")
    lines.append(f"CONFLICTS_LOGGED={len(conflicts)}")
    lines.append(f"PREVIEW_OUT={out_preview}")
    lines.append(f"REPORT_JSON={out_report_json}")
    out_report_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"PREVIEW={out_preview}")
    print(f"REPORT={out_report_txt}")
    print(f"EPISODE_DUPE_COUNT_BEFORE={before_dupes}")
    print(f"EPISODE_DUPE_COUNT_AFTER={after_dupes}")

    # do NOT overwrite data.json automatically; user will copy/rename once validated
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
