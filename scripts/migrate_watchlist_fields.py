import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUTS_PATH = REPO_ROOT / "data" / "inputs.json"
DATA_PATH = REPO_ROOT / "data" / "data.json"


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    inputs = load_json(INPUTS_PATH)
    if not isinstance(inputs, dict):
        return 0
    data = load_json(DATA_PATH) or {}
    shows = data.get("shows") or []
    movies = data.get("movies") or []
    show_ids = {str(s.get("tmdb_id")) for s in shows if s.get("tmdb_id") is not None}
    movie_ids = {str(m.get("tmdb_id")) for m in movies if m.get("tmdb_id") is not None}

    watchlist = inputs.get("watchlist")
    if not isinstance(watchlist, list):
        return 0

    changed = False
    for item in watchlist:
        if not isinstance(item, dict):
            continue
        tmdb_id = item.get("tmdb_id")
        if tmdb_id is None:
            continue
        tmdb_key = str(tmdb_id)

        if "media_kind" not in item and "kind" in item:
            item["media_kind"] = str(item["kind"])
            del item["kind"]
            changed = True
        if "watch_status" not in item and "status" in item:
            item["watch_status"] = str(item["status"])
            del item["status"]
            changed = True

        if "media_kind" not in item:
            if tmdb_key in show_ids:
                item["media_kind"] = "show"
            elif tmdb_key in movie_ids:
                item["media_kind"] = "movie"
            else:
                item["media_kind"] = "unknown"
            changed = True

        if "watch_status" not in item:
            item["watch_status"] = "watchlist"
            changed = True

        if "added_utc" not in item:
            item["added_utc"] = now_utc_iso()
            changed = True

    if changed:
        with INPUTS_PATH.open("w", encoding="utf-8") as f:
            json.dump(inputs, f, indent=2, ensure_ascii=True)
            f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
