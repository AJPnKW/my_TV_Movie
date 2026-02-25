# FILE: scripts\qa_check_episode_dupes_detailed.py
# PURPOSE: Prove whether episode dupes come from (A) multiple show objects sharing the same tmdb_id, or (B) dupes inside one show object.
# RUN: py -3 scripts\qa_check_episode_dupes_detailed.py

import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "data.json"
OUT_ROOT = ROOT / "out" / "qa_episode_dupes"

def main() -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    shows: List[Dict[str, Any]] = data.get("shows", []) or []

    # 1) duplicate show objects by tmdb_id
    show_id_counts = Counter()
    show_id_to_indexes: Dict[int, List[int]] = defaultdict(list)
    for i, s in enumerate(shows):
        sid = s.get("tmdb_id")
        if isinstance(sid, int):
            show_id_counts[sid] += 1
            show_id_to_indexes[sid].append(i)

    dup_show_ids = {sid: c for sid, c in show_id_counts.items() if c > 1}

    # 2) episode key duplicates across ALL shows (what your earlier script did)
    #    key = (show_tmdb_id, season_number, episode_number)
    all_keys: List[Tuple[int, int, int, int]] = []  # (sid, sn, en, show_index)
    for i, s in enumerate(shows):
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
                all_keys.append((sid, sn, en, i))

    key_counts = Counter([(sid, sn, en) for (sid, sn, en, _) in all_keys])
    dup_episode_keys = [k for k, v in key_counts.items() if v > 1]

    # 3) explain each duplicate episode key: which show indexes produced it
    dup_key_to_show_indexes: Dict[str, List[int]] = defaultdict(list)
    for sid, sn, en in dup_episode_keys:
        indexes = sorted({idx for (a, b, c, idx) in all_keys if a == sid and b == sn and c == en})
        dup_key_to_show_indexes[f"{sid}:{sn}:{en}"] = indexes

    # 4) summary per show_tmdb_id: how many duplicate episode keys it contributes to
    sid_dupekey_counts = Counter()
    for k in dup_episode_keys:
        sid_dupekey_counts[k[0]] += 1

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    out_json = out_dir / "episode_dupes_detailed.json"
    payload = {
        "data_path": str(DATA_PATH),
        "shows_total": len(shows),
        "duplicate_show_tmdb_id_groups": len(dup_show_ids),
        "duplicate_show_tmdb_ids": dict(sorted(dup_show_ids.items(), key=lambda x: (-x[1], x[0]))),
        "total_episode_keys": len(all_keys),
        "duplicate_episode_keys": len(dup_episode_keys),
        "top_20_show_ids_by_duplicate_episode_keys": [
            {"tmdb_id": sid, "dupe_keys": cnt, "show_objects": show_id_counts.get(sid, 0), "show_indexes": show_id_to_indexes.get(sid, [])[:10]}
            for sid, cnt in sid_dupekey_counts.most_common(20)
        ],
        "duplicate_episode_key_to_show_indexes_sample_50": dict(list(dup_key_to_show_indexes.items())[:50]),
        "note": "If duplicate_show_tmdb_id_groups>0, episode dupes are almost always caused by multiple show objects sharing tmdb_id. If that is 0, dupes are inside seasons/episodes within a single show object."
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"OUT={out_json}")
    print(f"SHOWS_TOTAL={len(shows)}")
    print(f"DUP_SHOW_TMBD_ID_GROUPS={len(dup_show_ids)}")
    print(f"TOTAL_EPISODE_KEYS={len(all_keys)}")
    print(f"DUPLICATE_EPISODE_KEYS={len(dup_episode_keys)}")
    if dup_episode_keys:
        s0 = dup_episode_keys[0]
        print(f"SAMPLE_DUP_KEY={s0[0]}:{s0[1]}:{s0[2]}")
        print(f"SAMPLE_DUP_SHOW_INDEXES={dup_key_to_show_indexes.get(f'{s0[0]}:{s0[1]}:{s0[2]}', [])}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
