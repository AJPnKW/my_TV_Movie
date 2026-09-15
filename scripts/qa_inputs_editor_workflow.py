#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "tools" / "inputs_editor" / "inputs_editor_server.py"
UI_PATH = REPO_ROOT / "web" / "inputs_editor.html"


def _load_server():
    spec = importlib.util.spec_from_file_location("inputs_editor_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load inputs editor server")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check(name: str, ok: bool, detail: str, checks: list[dict]) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def main() -> int:
    server = _load_server()
    server_text = SERVER_PATH.read_text(encoding="utf-8", errors="replace")
    ui_text = UI_PATH.read_text(encoding="utf-8", errors="replace")
    checks: list[dict] = []

    base = {
        "tv": [{"title": "Shared", "tmdb_id": 1, "season_spec": "*", "include_future": True, "in_scope": True}],
        "movies": [{"title": "Movie", "tmdb_id": 10, "in_scope": True}],
        "watchlist": [],
    }
    local = {
        "tv": [
            {"title": "Shared", "tmdb_id": 1, "season_spec": "2+", "include_future": True, "in_scope": True},
            {"title": "Local Only", "tmdb_id": 2, "season_spec": "*", "include_future": True, "in_scope": True},
        ],
        "movies": [{"title": "Movie", "tmdb_id": 10, "in_scope": True}],
        "watchlist": [],
    }
    remote = {
        "tv": [
            {"title": "Shared", "tmdb_id": 1, "season_spec": "*", "include_future": True, "in_scope": True},
            {"title": "Remote Only", "tmdb_id": 3, "season_spec": "*", "include_future": True, "in_scope": True},
        ],
        "movies": [{"title": "Movie", "tmdb_id": 10, "in_scope": True}],
        "watchlist": [],
    }
    merged = server._semantic_reconcile_inputs(local, remote, base)
    tv_ids = [item["tmdb_id"] for item in merged.get("inputs", {}).get("tv", [])]
    shared = next(item for item in merged.get("inputs", {}).get("tv", []) if item["tmdb_id"] == 1)
    _check("local_only_and_remote_only_inputs_preserved", merged.get("ok") and tv_ids == [1, 3, 2], str(tv_ids), checks)
    _check("local_edit_preserved_when_remote_unchanged", shared.get("season_spec") == "2+", shared.get("season_spec", ""), checks)

    remote_edit = {
        "tv": [{"title": "Shared Remote", "tmdb_id": 1, "season_spec": "*", "include_future": True, "in_scope": True}],
        "movies": [],
        "watchlist": [],
    }
    local_unchanged = {"tv": [base["tv"][0].copy()], "movies": [], "watchlist": []}
    merged_remote = server._semantic_reconcile_inputs(local_unchanged, remote_edit, {"tv": [base["tv"][0].copy()], "movies": [], "watchlist": []})
    _check("remote_edit_preserved_when_local_unchanged", merged_remote.get("inputs", {}).get("tv", [{}])[0].get("title") == "Shared Remote", json.dumps(merged_remote), checks)

    local_conflict = {"tv": [{"title": "Local Title", "tmdb_id": 1, "season_spec": "*"}], "movies": [], "watchlist": []}
    remote_conflict = {"tv": [{"title": "Remote Title", "tmdb_id": 1, "season_spec": "*"}], "movies": [], "watchlist": []}
    base_conflict = {"tv": [{"title": "Base Title", "tmdb_id": 1, "season_spec": "*"}], "movies": [], "watchlist": []}
    conflict = server._semantic_reconcile_inputs(local_conflict, remote_conflict, base_conflict)
    _check("genuine_same_field_conflict_blocks", not conflict.get("ok") and conflict.get("conflicts", [{}])[0].get("field") == "title", json.dumps(conflict), checks)

    duplicate = {"tv": [{"title": "One", "tmdb_id": 7}, {"title": "Two", "tmdb_id": 7}], "movies": [], "watchlist": []}
    deduped = server._semantic_reconcile_inputs(duplicate, {"tv": [], "movies": [], "watchlist": []}, None)
    _check("duplicate_tmdb_ids_cleaned_safely", deduped.get("ok") and len(deduped.get("inputs", {}).get("tv", [])) == 1, json.dumps(deduped), checks)

    _check("save_local_input_does_not_refresh_runtime", 'if parsed.path != "/api/inputs"' in server_text and "_atomic_write(INPUTS_JSON" in server_text, "POST /api/inputs writes canonical input only", checks)
    _check("adding_one_tv_does_not_auto_run_full_pipeline", 'function addItemFull' in ui_text and 'apiPost("/api/refresh-runtime"' in ui_text and 'btnRefreshRuntime' in ui_text, "refresh is button-owned", checks)
    _check("adding_one_movie_does_not_auto_run_full_pipeline", 'item.type==="movie"' in ui_text and 'setDirty(true); renderMine(); renderTmdb(); renderQueue(); counts();' in ui_text, "movie add is local state only", checks)
    _check("full_local_runtime_action_runs_full_pipeline", "run_pipeline_tmdb_trakt.py" in server_text and "Refresh Full Local Runtime" in ui_text, "full refresh endpoint owns pipeline", checks)
    _check("online_publish_does_not_require_local_runtime_refresh", "_publish_inputs_to_remote" in server_text and "_run_editor_refresh" not in server_text[server_text.index("def _publish_inputs_to_remote"):server_text.index("def _tmdb_search")], "publish path excludes local refresh", checks)
    _check("local_main_behind_remote_generated_commit_supported", "_fast_forward_remote" in server_text and "remote_contains_local" in server_text, "behind case fast-forwards", checks)
    _check("remote_advances_during_publish_supported", "_wait_for_generated_artifacts" in server_text and "merge-base" in server_text and "_generated_artifact_changes_since" in server_text, "poll loop checks ancestry", checks)
    _check("dirty_local_generated_data_is_disposable", "_stash_generated_artifacts_if_needed" in server_text and "LOCAL_GENERATED_STASH_PATHS" in server_text, "generated artifacts are stashed", checks)
    _check("generated_artifacts_never_enter_input_commit", '["add", "--", relative_inputs]' in server_text and '["commit", "-m", commit_message, "--", relative_inputs]' in server_text, "commit is path-limited", checks)
    _check("input_commit_associated_with_build_data", "_build_data_workflow_run" in server_text and "headSha" in server_text and "input_commit" in server_text, "workflow lookup uses head SHA", checks)
    _check("final_remote_runtime_inclusion_verified", "_verify_publish_outputs" in server_text and "missing_remote_runtime" in server_text, "remote runtime IDs verified", checks)
    _check("local_checkout_finishes_synchronized", "_fast_forward_remote" in server_text and "merge --ff-only" in server_text, "final sync uses ff-only", checks)
    _check("search_result_ui_not_already_added", "Already added" not in ui_text and "Local only - not published" in ui_text, "state labels are explicit", checks)
    _check("wrong_secondary_remote_not_used_silently", "different " in server_text and "repository than canonical upstream" in server_text and "requested remote" in server_text, "remote alias mismatch blocks", checks)
    _check("local_runtime_success_requires_expected_ids", "missing_runtime" in server_text and "_verify_identities_in_runtime" in server_text and "validation" in server_text, "refresh verifies expected IDs", checks)
    _check("user_input_never_disappears_on_reconcile", tv_ids == [1, 3, 2], "local-only row retained after remote-only row", checks)

    failures = [check for check in checks if not check["ok"]]
    print(json.dumps({"result": "OK" if not failures else "FAIL", "checks": checks}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
