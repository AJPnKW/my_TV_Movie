# FILE: scripts\qa_dump_show_episode_dupes.py
# PURPOSE: Dump exact duplicate-episode groups for a given show (tmdb_id), keyed by (season_number, episode_number)
# RUN: py -3 scripts\qa_dump_show_episode_dupes.py --show 245312
#      py -3 scripts\qa_dump_show_episode_dupes.py --show 42009

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "data.json"
OUT_ROOT = ROOT / "out" / "qa_episode_dupes"

KEEP_FIELDS = [
    "tmdb_id",
    "season_number",
    "episode_number",
    "name",
    "title",
    "air_date",
    "first_aired",
    "still_path",
    "still",
    "poster_path",
    "overview",
    "runtime",
    "duration",
    "links",
    "watch",
    "sources",
    "provider",
    "service",
]

def _safe(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return v

def pick_fields(ep: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in KEEP_FIELDS:
        if k in ep:
            out[k] = _safe(ep.get(k))
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, required=True)
    args = ap.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    shows = data.get("shows", [])
    show = next((s for s in shows if s.get("tmdb_id") == args.show), None)
    if not show:
        raise SystemExit(f"Show not found in data.json: tmdb_id={args.show}")

    groups: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    seasons = show.get("seasons", [])
    for season in seasons:
        sn = season.get("season_number")
        for ep in season.get("episodes", []):
            en = ep.get("episode_number")
            if sn is None or en is None:
                continue
            ep2 = dict(ep)
            ep2["tmdb_id"] = show.get("tmdb_id")
            ep2["season_number"] = sn
            ep2["episode_number"] = en
            groups[(int(sn), int(en))].append(ep2)

    dupes = { f"{sn}:{en}": [pick_fields(x) for x in items]
              for (sn, en), items in groups.items()
              if len(items) > 1 }

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    out_json = out_dir / f"show_{args.show}_episode_dupes.json"
    payload = {
        "tmdb_id": args.show,
        "total_seasons": len(seasons),
        "duplicate_groups": len(dupes),
        "groups": dupes,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"OUT={out_json}")
    print(f"DUPLICATE_GROUPS={len(dupes)}")
    if dupes:
        sample_key = next(iter(dupes.keys()))
        print(f"SAMPLE_KEY={sample_key}")
        print(f"SAMPLE_COUNT={len(dupes[sample_key])}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
