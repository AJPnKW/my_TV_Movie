import copy
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
INPUTS_PATH = ROOT / "data" / "inputs.json"
DATA_PATH = ROOT / "data" / "data.json"


REQUESTED_SHOWS = [
    {"tmdb_id": 155431, "title": "RuPaul's Drag Race UK Versus the World", "season_spec": "*"},
    {"tmdb_id": 245927, "title": "Paradise", "season_spec": "*"},
    {"tmdb_id": 276241, "title": "Small Achievable Goals", "season_spec": "2+"},
    {"tmdb_id": 84910, "title": "The Masked Singer", "season_spec": "14+"},
    {"tmdb_id": 40936, "title": "Allegiance", "season_spec": "3+"},
    {"tmdb_id": 247723, "title": "The Hunting Game", "season_spec": "*"},
]


def now_stamp() -> Tuple[str, str, str]:
    now = dt.datetime.now()
    utc = dt.datetime.now(dt.timezone.utc)
    ts_dir = now.strftime("%Y%m%d_%H%M%S")
    generated_local = now.strftime("%Y-%m-%dT%H:%M:%S")
    generated_utc = utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return ts_dir, generated_local, generated_utc


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def clean_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def slug_signal(title: str, year: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{base}|{year}"


def infer_year_from_text(text: str) -> str:
    m = re.search(r"\((\d{4})\)", text or "")
    return m.group(1) if m else ""


def pick_first_non_empty(a: Any, b: Any) -> Any:
    return a if clean_str(a) else b


def merge_dict_preferring_first(base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in other.items():
        if key not in out:
            out[key] = copy.deepcopy(val)
            continue
        if isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = merge_dict_preferring_first(out[key], val)
            continue
        if isinstance(out[key], list) and isinstance(val, list):
            if not out[key] and val:
                out[key] = copy.deepcopy(val)
            continue
        if clean_str(out[key]) == "" and clean_str(val) != "":
            out[key] = copy.deepcopy(val)
    return out


def dedupe_inputs_tv(tv_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    seen: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    dropped: List[Dict[str, Any]] = []

    for row in tv_rows:
        tmdb_id = clean_str(row.get("tmdb_id"))
        if not tmdb_id:
            # Keep malformed rows as-is in order to avoid data loss.
            key = f"__no_id__{len(order)}"
            seen[key] = copy.deepcopy(row)
            order.append(key)
            continue
        if tmdb_id not in seen:
            seen[tmdb_id] = copy.deepcopy(row)
            order.append(tmdb_id)
            continue
        prior = seen[tmdb_id]
        merged = copy.deepcopy(prior)
        merged["title"] = pick_first_non_empty(prior.get("title"), row.get("title"))
        merged["season_spec"] = pick_first_non_empty(prior.get("season_spec"), row.get("season_spec"))
        seen[tmdb_id] = merge_dict_preferring_first(merged, row)
        dropped.append(copy.deepcopy(row))

    return [seen[k] for k in order], dropped


def upsert_requested_shows(tv_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in tv_rows:
        key = clean_str(row.get("tmdb_id"))
        if key not in by_id:
            by_id[key] = row
            order.append(key)

    added: List[Dict[str, Any]] = []
    updated: List[Dict[str, Any]] = []
    unchanged: List[Dict[str, Any]] = []

    for req in REQUESTED_SHOWS:
        key = str(req["tmdb_id"])
        if key not in by_id:
            row = {"title": req["title"], "tmdb_id": req["tmdb_id"], "season_spec": req["season_spec"]}
            by_id[key] = row
            order.append(key)
            added.append(copy.deepcopy(row))
            continue
        row = by_id[key]
        before = copy.deepcopy(row)
        row["title"] = clean_str(row.get("title")) or req["title"]
        row["season_spec"] = req["season_spec"]
        if row != before:
            updated.append({"before": before, "after": copy.deepcopy(row)})
        else:
            unchanged.append(copy.deepcopy(row))

    return {
        "tv": [by_id[k] for k in order],
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
    }


def dedupe_episode_list(episodes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    seen: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    dropped = 0
    for ep in episodes:
        en = clean_str(ep.get("episode_number"))
        key = en if en else f"__idx__{len(order)}"
        if key not in seen:
            seen[key] = copy.deepcopy(ep)
            order.append(key)
        else:
            seen[key] = merge_dict_preferring_first(seen[key], ep)
            dropped += 1
    return [seen[k] for k in order], dropped


def merge_show_rows(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], int, int]:
    merged = copy.deepcopy(rows[0])
    season_dropped = 0
    episode_dropped = 0

    season_seen: Dict[str, Dict[str, Any]] = {}
    season_order: List[str] = []
    for row in rows:
        for season in row.get("seasons", []) if isinstance(row.get("seasons", []), list) else []:
            sn = clean_str(season.get("season_number"))
            key = sn if sn else f"__sidx__{len(season_order)}"
            if key not in season_seen:
                season_seen[key] = copy.deepcopy(season)
                season_order.append(key)
            else:
                season_seen[key] = merge_dict_preferring_first(season_seen[key], season)
                season_dropped += 1

    final_seasons: List[Dict[str, Any]] = []
    for key in season_order:
        s = season_seen[key]
        eps = s.get("episodes", [])
        if isinstance(eps, list):
            deduped_eps, dropped = dedupe_episode_list(eps)
            s["episodes"] = deduped_eps
            episode_dropped += dropped
        final_seasons.append(s)

    for row in rows[1:]:
        merged = merge_dict_preferring_first(merged, row)
    merged["seasons"] = final_seasons
    return merged, season_dropped, episode_dropped


def dedupe_data_shows(show_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    for row in show_rows:
        tmdb_id = clean_str(row.get("tmdb_id"))
        key = tmdb_id if tmdb_id else f"__no_id__{len(order)}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)

    out: List[Dict[str, Any]] = []
    merged_groups: List[Dict[str, Any]] = []
    total_show_dropped = 0
    total_season_dropped = 0
    total_episode_dropped = 0

    for key in order:
        rows = groups[key]
        if len(rows) == 1:
            row = copy.deepcopy(rows[0])
            eps_dropped = 0
            if isinstance(row.get("seasons", []), list):
                seasons_out = []
                for s in row["seasons"]:
                    s_copy = copy.deepcopy(s)
                    eps = s_copy.get("episodes", [])
                    if isinstance(eps, list):
                        deduped_eps, dropped = dedupe_episode_list(eps)
                        s_copy["episodes"] = deduped_eps
                        eps_dropped += dropped
                    seasons_out.append(s_copy)
                row["seasons"] = seasons_out
            total_episode_dropped += eps_dropped
            out.append(row)
            continue
        merged, seasons_dropped, episodes_dropped = merge_show_rows(rows)
        out.append(merged)
        total_show_dropped += len(rows) - 1
        total_season_dropped += seasons_dropped
        total_episode_dropped += episodes_dropped
        merged_groups.append(
            {
                "tmdb_id": key,
                "input_rows": len(rows),
                "dropped_show_rows": len(rows) - 1,
                "dropped_season_rows": seasons_dropped,
                "dropped_episode_rows": episodes_dropped,
            }
        )

    return {
        "shows": out,
        "merged_groups": merged_groups,
        "dropped_show_rows": total_show_dropped,
        "dropped_season_rows": total_season_dropped,
        "dropped_episode_rows": total_episode_dropped,
    }


def duplicate_metrics(inputs_obj: Dict[str, Any], data_obj: Dict[str, Any]) -> Dict[str, Any]:
    tv = inputs_obj.get("tv", []) if isinstance(inputs_obj.get("tv", []), list) else []
    movies_in = inputs_obj.get("movies", []) if isinstance(inputs_obj.get("movies", []), list) else []
    shows = data_obj.get("shows", []) if isinstance(data_obj.get("shows", []), list) else []
    movies = data_obj.get("movies", []) if isinstance(data_obj.get("movies", []), list) else []

    def tmdb_dups(rows: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in rows:
            key = clean_str(r.get("tmdb_id"))
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
        return {k: v for k, v in counts.items() if v > 1}

    def title_year_dups(rows: List[Dict[str, Any]], title_keys: List[str], year_keys: List[str]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in rows:
            title = ""
            for tk in title_keys:
                title = clean_str(r.get(tk))
                if title:
                    break
            year = ""
            for yk in year_keys:
                raw = clean_str(r.get(yk))
                if raw:
                    year = raw[:4]
                    break
            if not year:
                year = infer_year_from_text(title)
            sig = slug_signal(title or "untitled", year)
            counts[sig] = counts.get(sig, 0) + 1
        return {k: v for k, v in counts.items() if v > 1}

    def internal_id_dups(rows: List[Dict[str, Any]], keys: List[str]) -> Dict[str, Dict[str, int]]:
        out: Dict[str, Dict[str, int]] = {}
        for key in keys:
            counts: Dict[str, int] = {}
            for r in rows:
                val = clean_str(r.get(key))
                if not val:
                    continue
                counts[val] = counts.get(val, 0) + 1
            dup = {k: v for k, v in counts.items() if v > 1}
            if dup:
                out[key] = dup
        return out

    season_dups = 0
    episode_dups = 0
    for show in shows:
        seasons = show.get("seasons", [])
        if not isinstance(seasons, list):
            continue
        season_counts: Dict[str, int] = {}
        for s in seasons:
            sn = clean_str(s.get("season_number"))
            if sn:
                season_counts[sn] = season_counts.get(sn, 0) + 1
            eps = s.get("episodes", [])
            if isinstance(eps, list):
                ep_counts: Dict[str, int] = {}
                for ep in eps:
                    en = clean_str(ep.get("episode_number"))
                    if en:
                        ep_counts[en] = ep_counts.get(en, 0) + 1
                episode_dups += sum(1 for v in ep_counts.values() if v > 1)
        season_dups += sum(1 for v in season_counts.values() if v > 1)

    return {
        "counts": {
            "inputs_tv": len(tv),
            "inputs_movies": len(movies_in),
            "data_shows": len(shows),
            "data_movies": len(movies),
        },
        "duplicates": {
            "tmdb": {
                "inputs_tv": tmdb_dups(tv),
                "data_shows": tmdb_dups(shows),
                "data_movies": tmdb_dups(movies),
            },
            "slug_title_year": {
                "inputs_tv": title_year_dups(tv, ["title", "name"], ["first_air_date", "release_date"]),
                "data_shows": title_year_dups(shows, ["title", "name"], ["first_air_date", "release_date"]),
                "data_movies": title_year_dups(movies, ["title", "name"], ["release_date", "first_air_date"]),
            },
            "internal_ids": {
                "inputs_tv": internal_id_dups(tv, ["id", "show_id", "tv_id"]),
                "data_shows": internal_id_dups(shows, ["id", "show_id", "tv_id", "slug"]),
                "data_movies": internal_id_dups(movies, ["id", "movie_id", "slug"]),
            },
            "structural": {
                "season_number_duplicates_within_show_rows": season_dups,
                "episode_number_duplicates_within_season_rows": episode_dups,
            },
        },
    }


def build_text_report(report: Dict[str, Any]) -> str:
    before = report["before"]
    after = report["after"]
    changes = report["changes"]
    lines = []
    lines.append("QA Data JSON Audit Report")
    lines.append(f"timestamp_local={report['timestamp_local']}")
    lines.append(f"timestamp_utc={report['timestamp_utc']}")
    lines.append("")
    lines.append("Before Counts")
    lines.append(f"inputs.tv={before['counts']['inputs_tv']}")
    lines.append(f"inputs.movies={before['counts']['inputs_movies']}")
    lines.append(f"data.shows={before['counts']['data_shows']}")
    lines.append(f"data.movies={before['counts']['data_movies']}")
    lines.append("")
    lines.append("After Counts")
    lines.append(f"inputs.tv={after['counts']['inputs_tv']}")
    lines.append(f"inputs.movies={after['counts']['inputs_movies']}")
    lines.append(f"data.shows={after['counts']['data_shows']}")
    lines.append(f"data.movies={after['counts']['data_movies']}")
    lines.append("")
    lines.append("TMDB Duplicate Groups")
    lines.append(f"before.inputs.tv={len(before['duplicates']['tmdb']['inputs_tv'])}")
    lines.append(f"after.inputs.tv={len(after['duplicates']['tmdb']['inputs_tv'])}")
    lines.append(f"before.data.shows={len(before['duplicates']['tmdb']['data_shows'])}")
    lines.append(f"after.data.shows={len(after['duplicates']['tmdb']['data_shows'])}")
    lines.append(f"before.data.movies={len(before['duplicates']['tmdb']['data_movies'])}")
    lines.append(f"after.data.movies={len(after['duplicates']['tmdb']['data_movies'])}")
    lines.append("")
    lines.append("Structural Rules")
    lines.append(
        "after.season_number_duplicates_within_show_rows="
        f"{after['duplicates']['structural']['season_number_duplicates_within_show_rows']}"
    )
    lines.append(
        "after.episode_number_duplicates_within_season_rows="
        f"{after['duplicates']['structural']['episode_number_duplicates_within_season_rows']}"
    )
    lines.append("")
    lines.append("Changes Applied")
    lines.append(f"inputs.tv duplicate rows removed={changes['inputs_tv_dropped_rows']}")
    lines.append(f"data.shows duplicate show rows removed={changes['data_shows_dropped_rows']}")
    lines.append(f"data.shows duplicate season rows removed={changes['data_shows_dropped_season_rows']}")
    lines.append(f"data.shows duplicate episode rows removed={changes['data_shows_dropped_episode_rows']}")
    lines.append(f"requested_show_rows_added={len(changes['requested_added'])}")
    lines.append(f"requested_show_rows_updated={len(changes['requested_updated'])}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ts_dir, generated_local, generated_utc = now_stamp()
    out_dir = ROOT / "out" / "qa_data_json_audit" / ts_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs_obj = load_json(INPUTS_PATH)
    data_obj = load_json(DATA_PATH)

    before = duplicate_metrics(inputs_obj, data_obj)

    tv_rows = inputs_obj.get("tv", []) if isinstance(inputs_obj.get("tv", []), list) else []
    deduped_tv, dropped_tv = dedupe_inputs_tv(tv_rows)
    upsert = upsert_requested_shows(deduped_tv)
    inputs_obj["tv"] = upsert["tv"]
    inputs_obj["generated_local"] = generated_local
    inputs_obj["generated_utc"] = generated_utc

    shows_rows = data_obj.get("shows", []) if isinstance(data_obj.get("shows", []), list) else []
    deduped_shows = dedupe_data_shows(shows_rows)
    data_obj["shows"] = deduped_shows["shows"]

    # Validation parse gates before persisting.
    json.loads(json.dumps(inputs_obj))
    json.loads(json.dumps(data_obj))

    write_json(INPUTS_PATH, inputs_obj)
    write_json(DATA_PATH, data_obj)

    after = duplicate_metrics(inputs_obj, data_obj)

    report = {
        "timestamp_local": generated_local,
        "timestamp_utc": generated_utc,
        "rules": {
            "show_uniqueness": "one record per tmdb_id in top-level shows arrays",
            "season_uniqueness": "within a show, one season record per season_number",
            "episode_uniqueness": "within a season, one episode record per episode_number",
        },
        "before": before,
        "after": after,
        "changes": {
            "inputs_tv_dropped_rows": len(dropped_tv),
            "inputs_tv_dropped_examples": dropped_tv[:25],
            "data_shows_dropped_rows": deduped_shows["dropped_show_rows"],
            "data_shows_dropped_season_rows": deduped_shows["dropped_season_rows"],
            "data_shows_dropped_episode_rows": deduped_shows["dropped_episode_rows"],
            "data_show_merge_groups": deduped_shows["merged_groups"],
            "requested_added": upsert["added"],
            "requested_updated": upsert["updated"],
            "requested_unchanged": upsert["unchanged"],
        },
    }

    json_report_path = out_dir / "inputs_data_duplicate_report.json"
    txt_report_path = out_dir / "inputs_data_duplicate_report.txt"
    log_report_path = out_dir / "inputs_data_duplicate_report.log.txt"

    write_json(json_report_path, report)
    txt_body = build_text_report(report)
    txt_report_path.write_text(txt_body, encoding="utf-8", newline="\n")
    log_lines = [
        f"START {generated_local} / {generated_utc}",
        f"INPUTS_PATH={INPUTS_PATH}",
        f"DATA_PATH={DATA_PATH}",
        f"OUT_DIR={out_dir}",
        f"inputs.tv.before={before['counts']['inputs_tv']}",
        f"inputs.tv.after={after['counts']['inputs_tv']}",
        f"data.shows.before={before['counts']['data_shows']}",
        f"data.shows.after={after['counts']['data_shows']}",
        f"dup.inputs.tv.tmdb.before={len(before['duplicates']['tmdb']['inputs_tv'])}",
        f"dup.inputs.tv.tmdb.after={len(after['duplicates']['tmdb']['inputs_tv'])}",
        f"dup.data.shows.tmdb.before={len(before['duplicates']['tmdb']['data_shows'])}",
        f"dup.data.shows.tmdb.after={len(after['duplicates']['tmdb']['data_shows'])}",
        f"END {dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
    ]
    log_report_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8", newline="\n")

    patch_notes_dir = ROOT / "docs" / "_patch_notes"
    patch_notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = patch_notes_dir / f"{ts_dir}_qa_data_json_audit.md"
    note_lines = [
        "# QA Data JSON Audit + Dedup Fix",
        "",
        f"- Timestamp local: `{generated_local}`",
        f"- Timestamp UTC: `{generated_utc}`",
        "",
        "## Evidence",
        f"- `inputs.tv` duplicate TMDB groups before: `{len(before['duplicates']['tmdb']['inputs_tv'])}`",
        f"- `data.shows` duplicate TMDB groups before: `{len(before['duplicates']['tmdb']['data_shows'])}`",
        "- `watch_me` TV path had no show-level dedupe by TMDB/season/episode keys.",
        "",
        "## Changes",
        f"- Deduped `data/inputs.json` TV rows by `tmdb_id` (removed `{len(dropped_tv)}` duplicate rows).",
        "- Applied requested show entries idempotently:",
        "  - 155431 `*`",
        "  - 245927 `*`",
        "  - 276241 `2+`",
        "  - 84910 `14+`",
        "  - 40936 `3+`",
        "  - 247723 `*`",
        f"- Deduped `data/data.json` shows by `tmdb_id` (removed `{deduped_shows['dropped_show_rows']}` duplicate show rows).",
        f"- Deduped within merged shows: removed `{deduped_shows['dropped_season_rows']}` duplicate season rows and `{deduped_shows['dropped_episode_rows']}` duplicate episode rows.",
        "",
        "## Rule Validation (After)",
        f"- Show uniqueness (TMDB): `{len(after['duplicates']['tmdb']['data_shows'])}` duplicate groups.",
        f"- Season uniqueness within show: `{after['duplicates']['structural']['season_number_duplicates_within_show_rows']}` duplicate rows.",
        f"- Episode uniqueness within season: `{after['duplicates']['structural']['episode_number_duplicates_within_season_rows']}` duplicate rows.",
        "",
        "## Artifacts",
        f"- `out/qa_data_json_audit/{ts_dir}/inputs_data_duplicate_report.json`",
        f"- `out/qa_data_json_audit/{ts_dir}/inputs_data_duplicate_report.txt`",
        f"- `out/qa_data_json_audit/{ts_dir}/inputs_data_duplicate_report.log.txt`",
    ]
    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8", newline="\n")

    print(str(out_dir))


if __name__ == "__main__":
    main()
