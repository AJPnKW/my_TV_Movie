#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/sync_local_watch_state.py
# [PROJECT] my_TV_Movie
# [ROLE]    Sync local watch_state from data/inputs.json into data/data.json
# [VERSION] v1.0.0
# [UPDATED] 2026-01-25
# [BUILD]   14.01.25
#
# Behavior:
# - If inputs.json lacks watch_state, no-op.
# - Writes data.watch_state.local = {generated_utc, source, movies{}, shows{}}
# - movies/shows maps are keyed by TMDB id (string), matching Trakt shape.
# ==============================================================================
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUTS_JSON = REPO_ROOT / "data" / "inputs.json"
DATA_JSON = REPO_ROOT / "data" / "data.json"


def _utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not INPUTS_JSON.exists() or not DATA_JSON.exists():
        return 0

    inp = _read_json(INPUTS_JSON)
    raw = inp.get("watch_state")
    if not raw:
        return 0

    local = raw.get("local") if isinstance(raw, dict) else None
    if not local and isinstance(raw, dict):
        local = raw
    if not isinstance(local, dict):
        return 0

    data = _read_json(DATA_JSON)
    data.setdefault("watch_state", {})
    data["watch_state"]["local"] = {
        "generated_utc": _utc(),
        "source": "inputs",
        "movies": local.get("movies") or {},
        "shows": local.get("shows") or {},
    }

    _write_json(DATA_JSON, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
