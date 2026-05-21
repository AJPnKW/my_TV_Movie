from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "web" / "config.json"
APP_RUNTIME_PATH = ROOT / "web" / "js" / "app_runtime.js"
CARD_RENDERER_PATH = ROOT / "web" / "js" / "card_renderer.js"
MAIN_CSS_PATH = ROOT / "web" / "css" / "main_app.css"
DATA_PATH = ROOT / "data" / "data.json"

DEFAULT_PROVIDERS = [
    "VidSrc",
    "VidEasy",
    "SuperEmbed",
    "MultiEmbed",
    "SmashyStream",
    "FlixHQ",
    "SFlix",
    "2Embed CC",
    "2Embed Org",
]

CANDIDATE_PROVIDERS = [
    "VidSrc.me",
    "VidSrc.to",
    "VidLink",
    "Nunflix",
    "vidsrc-embed.ru",
]

BLOCKED_PROVIDERS = [
    "Goojara",
    "Cineb",
    "freeintertv.com",
]

EPISODE_TEST_CASES = [
    {"tmdb_id": "226285", "season": "3", "episode": "17"},
    {"tmdb_id": "289560", "season": "1", "episode": "12"},
]


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostics only
        fail(f"JSON parse failed for {path.relative_to(ROOT)}: {exc}")


def fill_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def visible_provider_names(config: dict, *, include_candidates: bool = False) -> list[str]:
    names: list[str] = []
    for provider in config["streaming"]["embed_providers"]:
        status = str(provider.get("status") or "ok").lower()
        if status == "blocked":
            continue
        if status == "candidate" and not include_candidates:
            continue
        if status not in {"ok", "warn", "candidate"}:
            continue
        if not provider.get("tv_template") or not provider.get("movie_template"):
            continue
        names.append(str(provider.get("name") or provider.get("key")))
    return names


def function_body(source: str, function_name: str) -> str:
    marker = f"function {function_name}"
    start = source.find(marker)
    assert_true(start >= 0, f"{function_name} missing")
    brace = source.find("{", start)
    assert_true(brace >= 0, f"{function_name} missing opening brace")
    next_function = re.search(r"\n  function\s+\w+", source[brace + 1 :])
    if next_function:
        return source[brace + 1 : brace + 1 + next_function.start()]
    return source[brace + 1 :]


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)


def validate_provider_registry(config: dict) -> None:
    streaming = config.get("streaming") or {}
    providers = streaming.get("embed_providers")
    assert_true(isinstance(providers, list), "streaming.embed_providers must be a list")
    assert_true(streaming.get("show_candidate_providers") is False, "streaming.show_candidate_providers must default to false")

    by_name = {provider.get("name"): provider for provider in providers if isinstance(provider, dict)}
    for name in DEFAULT_PROVIDERS:
        provider = by_name.get(name)
        assert_true(provider is not None, f"default provider missing from config: {name}")
        assert_true(str(provider.get("status")).lower() in {"ok", "warn"}, f"default provider must be ok/warn: {name}")
        assert_true(bool(provider.get("tv_template")) and bool(provider.get("movie_template")), f"default provider missing templates: {name}")

    for name in CANDIDATE_PROVIDERS:
        provider = by_name.get(name)
        assert_true(provider is not None, f"candidate provider missing from config: {name}")
        assert_true(str(provider.get("status")).lower() == "candidate", f"candidate provider has wrong status: {name}")
        assert_true(bool(provider.get("tv_template")) and bool(provider.get("movie_template")), f"candidate provider missing verified templates: {name}")

    for name in BLOCKED_PROVIDERS:
        provider = by_name.get(name)
        assert_true(provider is not None, f"blocked provider missing from config: {name}")
        assert_true(str(provider.get("status")).lower() == "blocked", f"blocked provider has wrong status: {name}")

    assert_true(visible_provider_names(config) == DEFAULT_PROVIDERS, "default visible provider names/order drifted")
    visible_with_candidates = visible_provider_names(config, include_candidates=True)
    for name in CANDIDATE_PROVIDERS:
        assert_true(name in visible_with_candidates, f"candidate provider not shown when explicitly enabled: {name}")
        assert_true(name not in visible_provider_names(config), f"candidate provider visible by default: {name}")
    for name in BLOCKED_PROVIDERS:
        assert_true(name not in visible_with_candidates, f"blocked provider would render: {name}")

    for case in EPISODE_TEST_CASES:
        for provider in providers:
            status = str(provider.get("status") or "ok").lower()
            if status not in {"ok", "warn"}:
                continue
            href = fill_template(str(provider["tv_template"]), case)
            assert_true(case["tmdb_id"] in href and case["season"] in href and case["episode"] in href, f"provider template failed test case {case}: {provider.get('name')}")


def validate_runtime_source(app_text: str, renderer_text: str, css_text: str) -> None:
    collect_body = function_body(app_text, "collectConfiguredWatchSources")
    assert_true("state.cfg?.streaming?.embed_providers" in app_text and "function collectConfiguredWatchSources(kind, item, context = {})" in app_text, "collectConfiguredWatchSources must read config streaming.embed_providers")
    assert_true("item?.watch?.embed" not in collect_body, "collectConfiguredWatchSources must not source provider buttons from per-item watch.embed")
    assert_true("show_candidate_providers" in collect_body, "candidate provider flag missing from collectConfiguredWatchSources")
    assert_true("status === \"blocked\"" in collect_body, "blocked providers must be filtered")
    assert_true("status === \"candidate\" && !showCandidates" in collect_body, "candidate providers must be hidden unless enabled")

    assert_true("function pickImage(obj, ...keys)" in app_text, "pickImage must accept ordered fallback keys")
    assert_true("function episodeStillImageForCard" in app_text, "episodeStillImageForCard resolver missing")
    assert_true("still_local" in function_body(app_text, "episodeStillImageForCard"), "episode image resolver must try still_local first")
    assert_true("backdrop_local" in function_body(app_text, "episodeStillImageForCard"), "episode image resolver must fall back to show backdrop")
    assert_true("poster_local" in function_body(app_text, "episodeStillImageForCard"), "episode image resolver must fall back to show poster")

    shared_body = function_body(app_text, "buildSharedEpisodeCard")
    assert_true("renderEpisodeCardHtml" in shared_body, "buildSharedEpisodeCard must call canonical renderEpisodeCardHtml")
    assert_true("data-episode-card-renderer" in shared_body, "shared episode card renderer marker missing")
    assert_true("data-episode-card-density" in shared_body, "episode card density marker missing")
    assert_true("data-image-resolver" in shared_body, "episode card image resolver marker missing")
    assert_true("episodeStillImageForCard" in shared_body, "shared episode card must use shared image resolver")

    calendar_body = function_body(app_text, "renderCalendar")
    dashboard_body = function_body(app_text, "renderDashboard")
    assert_true("buildSharedEpisodeCard" in calendar_body, "calendar must use buildSharedEpisodeCard")
    assert_true("buildSharedEpisodeCard" in dashboard_body, "dashboard must use buildSharedEpisodeCard")
    assert_true("renderCompactEpisodeCardHtml" not in calendar_body, "calendar must not call renderer directly")
    assert_true("renderCompactEpisodeCardHtml" not in dashboard_body, "dashboard must not call renderer directly")
    assert_true("media-card--episode" not in calendar_body, "calendar must not define independent episode card markup")
    assert_true("media-card--episode" not in dashboard_body, "dashboard must not define independent episode card markup")

    assert_true("renderEpisodeCardHtml" in renderer_text, "card_renderer must export renderEpisodeCardHtml")
    assert_true("renderCompactEpisodeCardHtml" in renderer_text, "card_renderer must retain compact episode renderer")
    assert_true("media-card--density-" in renderer_text, "card renderer must stamp density class")
    assert_true("onerror=" in renderer_text and "data-fallback-html" in renderer_text, "card images must have broken-image fallback")

    assert_true("media-card--density-standard" in css_text, "standard density CSS missing")
    assert_true("media-card--density-compact" in css_text, "compact density CSS missing")


def validate_sample_images() -> None:
    data = load_json(DATA_PATH)
    episodes_with_stills = []
    for obj in walk(data):
        if not isinstance(obj, dict):
            continue
        if obj.get("still_local") or obj.get("episode_still_local") or obj.get("still_path") or obj.get("episode_still_path"):
            episodes_with_stills.append(obj)
        if len(episodes_with_stills) >= 5:
            break
    assert_true(bool(episodes_with_stills), "sample data contains no episode still candidates")
    for episode in episodes_with_stills:
        still = str(episode.get("still_local") or episode.get("episode_still_local") or episode.get("still_path") or episode.get("episode_still_path") or "")
        assert_true(still.strip(), "sample still path is empty")
        assert_true("/image/" not in still and "/images/" not in still, f"deprecated image folder referenced: {still}")
        if still.startswith("/assets/"):
            assert_true((ROOT / still.lstrip("/").replace("/", "\\")).exists(), f"local still asset missing: {still}")


def main() -> int:
    config = load_json(CONFIG_PATH)
    app_text = APP_RUNTIME_PATH.read_text(encoding="utf-8")
    renderer_text = CARD_RENDERER_PATH.read_text(encoding="utf-8")
    css_text = MAIN_CSS_PATH.read_text(encoding="utf-8")

    validate_provider_registry(config)
    validate_runtime_source(app_text, renderer_text, css_text)
    validate_sample_images()

    print(
        json.dumps(
            {
                "streaming_episode_card_validation": "passed",
                "default_providers": DEFAULT_PROVIDERS,
                "candidate_hidden_by_default": CANDIDATE_PROVIDERS,
                "blocked_hidden": BLOCKED_PROVIDERS,
                "episode_test_cases": EPISODE_TEST_CASES,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
