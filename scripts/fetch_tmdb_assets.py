#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/fetch_tmdb_assets.py
# [PROJECT] my_TV_Movie
# [ROLE]    Asset-only TMDB augmentation + local image caching
# [VERSION] v1.1.0
# [UPDATED] 2026-02-02
#
# Requires:
#   API_TMDB_KEY or API_TMDB_TOKEN
#   web/config.json (image_cache + image_sizes + streaming)
#
# Input:
#   data/data.json (Trakt metadata + user state)
# Output:
#   data/data.json (assets + filtered providers + local paths)
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception as ex:
    raise SystemExit("Missing dependency: requests. Run: python -m pip install -r requirements.txt") from ex

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "data" / "data.json"
CONFIG_JSON = REPO_ROOT / "web" / "config.json"

TMDB_API_BASE = "https://api.themoviedb.org/3"
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
POSTER_SIZES = [92, 154, 185, 342, 500, 780]
BACKDROP_SIZES = [300, 780, 1280]
STILL_SIZES = [92, 185, 300, 500]
LOGO_SIZES = [45, 92, 154, 185, 300, 500]


def _utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_jsonc(s: str) -> str:
    lines = []
    for line in s.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        out = []
        in_str = False
        esc = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                out.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == "\"":
                    in_str = False
                i += 1
                continue
            if ch == "\"":
                in_str = True
                out.append(ch)
                i += 1
                continue
            if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            out.append(ch)
            i += 1
        lines.append("".join(out).rstrip())
    cleaned = "\n".join(lines)
    if not cleaned.lstrip().startswith("{"):
        brace = cleaned.find("{")
        if brace != -1:
            cleaned = cleaned[brace:]
    return cleaned


def load_jsonc(path: Path) -> Dict[str, Any]:
    raw = read_text(path)
    return json.loads(strip_jsonc(raw))


def tmdb_headers(token: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def tmdb_get(path: str, key: Optional[str], token: Optional[str], params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{TMDB_API_BASE}{path}"
    p = params or {}
    if key and not token:
        p["api_key"] = key
    r = requests.get(url, headers=tmdb_headers(token), params=p, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"TMDB {path} failed: {r.status_code} {r.text[:200]}")
    return r.json()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def cfg_folder(cfg: Dict[str, Any], key: str) -> str:
    folders = (cfg.get("image_cache") or {}).get("folders") or {}
    return folders.get(key) or ""


def local_web_path(folder: str, filename: str) -> str:
    if not folder:
        return ""
    folder = folder if folder.startswith("/") else f"/{folder}"
    return f"{folder.rstrip('/')}/{filename}"


def local_file_path(web_path: str) -> Path:
    return REPO_ROOT / web_path.lstrip("/")


def is_assets_web_path(web_path: str) -> bool:
    return web_path.startswith("/assets/") or web_path.startswith("assets/")


def normalize_assets_web_path(web_path: str) -> str:
    if web_path.startswith("assets/"):
        return f"/{web_path}"
    return web_path


def file_exists(file_path: Path) -> bool:
    return file_path.exists() and file_path.stat().st_size > 0


def provider_logo_mirror_path(filename: str) -> Path:
    return REPO_ROOT / "web" / "assets" / "logos" / "services" / filename


def mirror_provider_logo(src: Path, filename: str) -> None:
    if not file_exists(src):
        return
    dst = provider_logo_mirror_path(filename)
    if file_exists(dst):
        return
    ensure_dir(dst.parent)
    try:
        shutil.copyfile(src, dst)
    except Exception:
        return


def nearest_size(width: int, sizes: List[int]) -> int:
    for s in sizes:
        if s >= width:
            return s
    return sizes[-1]


def size_code(cfg: Dict[str, Any], kind: str, key: str, path: str = "") -> str:
    sizes = cfg.get("image_sizes") or {}
    if "still" in key:
        w = int(sizes.get("episode_still_w") or 300)
        return f"w{nearest_size(w, STILL_SIZES)}"
    if "backdrop" in key:
        w = int(sizes.get("backdrop_w") or 780)
        return f"w{nearest_size(w, BACKDROP_SIZES)}"
    if "poster" in key:
        if kind == "season":
            w = int(sizes.get("season_width") or sizes.get("show_width") or 300)
        elif kind == "movie":
            w = int(sizes.get("movie_width") or 300)
        else:
            w = int(sizes.get("show_width") or 300)
        return f"w{nearest_size(w, POSTER_SIZES)}"
    if "logo" in key or "clearlogo" in key or "banner" in key or "thumb" in key:
        if "watch_providers" in path:
            w = int(sizes.get("provider_logo_max_w") or sizes.get("network_logo_max_w") or 45)
        else:
            w = int(sizes.get("show_width") or 300)
        return f"w{nearest_size(w, LOGO_SIZES)}"
    w = int(sizes.get("show_width") or 300)
    return f"w{nearest_size(w, POSTER_SIZES)}"


def folder_for(cfg: Dict[str, Any], kind: str, key: str, path: str = "") -> str:
    if "watch_providers" in path and "logo" in key:
        return cfg_folder(cfg, "providers_logo")
    if "still" in key:
        return cfg_folder(cfg, "episodes_stills")
    if "backdrop" in key:
        if kind == "season":
            return cfg_folder(cfg, "seasons_backdrop")
        return cfg_folder(cfg, "movies_backdrop") if kind == "movie" else cfg_folder(cfg, "shows_backdrop")
    if "poster" in key:
        if kind == "season":
            return cfg_folder(cfg, "seasons_poster")
        return cfg_folder(cfg, "movies_poster") if kind == "movie" else cfg_folder(cfg, "shows_poster")
    if "logo" in key or "clearlogo" in key or "banner" in key or "thumb" in key:
        return cfg_folder(cfg, "shows_poster")
    return cfg_folder(cfg, "shows_poster")


def build_tmdb_image_url(cfg: Dict[str, Any], size_code: str, path: str) -> str:
    base = (cfg.get("image_cache") or {}).get("tmdb_image_base") or "https://image.tmdb.org/t/p"
    return f"{base}/{size_code}{path}"


def download_asset(url: str, file_path: Path) -> bool:
    try:
        ensure_dir(file_path.parent)
        r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": UA_BROWSER, "Accept": "image/*"})
        if r.status_code != 200:
            return False
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)
        return file_path.exists() and file_path.stat().st_size > 0
    except Exception:
        return False


def filter_watch_providers(raw: Any, allowed_regions: List[str]) -> Tuple[Any, int]:
    if not isinstance(raw, dict):
        return raw, 0
    results = raw.get("results")
    if not isinstance(results, dict):
        return raw, 0
    filtered = {}
    removed = 0
    for region, payload in results.items():
        if region not in allowed_regions:
            removed += 1
            continue
        if not isinstance(payload, dict):
            continue
        flatrate = payload.get("flatrate")
        if isinstance(flatrate, list) and flatrate:
            keep = [p for p in flatrate if isinstance(p, dict) and p.get("logo_path")]
            if keep:
                filtered[region] = {"flatrate": keep}
            else:
                removed += 1
        else:
            removed += 1
    return {"results": filtered}, removed


def prune_watch_providers(obj: Any, errors: List[Dict[str, Any]], counters: Dict[str, int], path: str = "") -> None:
    if not isinstance(obj, dict):
        return
    providers = obj.get("watch_providers")
    if not isinstance(providers, dict):
        return
    results = providers.get("results")
    if not isinstance(results, dict):
        return
    removed_regions = 0
    for region in list(results.keys()):
        payload = results.get(region)
        if not isinstance(payload, dict):
            results.pop(region, None)
            removed_regions += 1
            continue
        flatrate = payload.get("flatrate")
        if not isinstance(flatrate, list):
            results.pop(region, None)
            removed_regions += 1
            continue
        kept = []
        for provider in flatrate:
            if not isinstance(provider, dict):
                continue
            local = provider.get("logo_path_local")
            if isinstance(local, str) and local.strip():
                web_path = normalize_assets_web_path(local.strip())
                if is_assets_web_path(web_path) and file_exists(local_file_path(web_path)):
                    kept.append(provider)
                    continue
            provider["logo_path_local"] = None
        if kept:
            payload["flatrate"] = kept
        else:
            results.pop(region, None)
            removed_regions += 1
    if removed_regions:
        counters["provider_items_filtered"] += removed_regions


def scan_assets(obj: Any, cfg: Dict[str, Any], kind: str, errors: List[Dict[str, Any]], counters: Dict[str, int], path: str = "") -> None:
    if isinstance(obj, list):
        for idx, item in enumerate(obj):
            scan_assets(item, cfg, kind, errors, counters, f"{path}[{idx}]")
        return
    if not isinstance(obj, dict):
        return

    tmdb_base = (cfg.get("image_cache") or {}).get("tmdb_image_base") or "https://image.tmdb.org/t/p"

    special_keys = {"poster_path", "backdrop_path", "still_path", "logo_path", "clearlogo_path", "banner_path", "thumb_path", "show_logo_tmdb"}
    for key, val in list(obj.items()):
        key_l = key.lower()
        if key_l.endswith("_local"):
            if isinstance(val, str) and val.strip():
                web_path = normalize_assets_web_path(val.strip())
                if not is_assets_web_path(web_path):
                    obj[key] = None
                else:
                    file_path = local_file_path(web_path)
                    if not file_exists(file_path):
                        obj[key] = None
            else:
                obj[key] = None
            continue

        is_candidate = key_l.endswith("_path") or key_l.endswith("_url") or key in special_keys
        if not is_candidate:
            continue
        if not isinstance(val, str) or not val.strip():
            local_key = f"{key}_local" if (key_l.endswith("_path") or key_l.endswith("_url")) else f"{key}_local"
            if local_key in obj:
                obj[local_key] = None
            continue

        local_key = f"{key}_local" if (key_l.endswith("_path") or key_l.endswith("_url")) else f"{key}_local"
        remote = val.strip()
        size = size_code(cfg, kind, key_l, path)

        if remote.startswith("http"):
            if not remote.startswith(tmdb_base):
                continue
            remote_url = remote
        elif remote.startswith("/"):
            remote_url = build_tmdb_image_url(cfg, size, remote)
        else:
            remote_url = ""

        if not remote_url:
            continue

        folder = folder_for(cfg, kind, key_l, path)
        if not folder:
            obj[local_key] = None
            continue
        filename = Path(remote).name
        web_path = local_web_path(folder, filename)
        obj[local_key] = web_path
        counters["assets_expected"] += 1

        file_path = local_file_path(web_path)
        enabled = (cfg.get("image_cache") or {}).get("enabled", True)
        is_provider_logo = "watch_providers" in path and "logo" in key_l
        if file_exists(file_path):
            if is_provider_logo:
                mirror_provider_logo(file_path, filename)
            counters["assets_skipped"] += 1
            continue
        if not enabled:
            errors.append(
                {
                    "type": "asset_missing",
                    "path": f"{path}.{key}".strip("."),
                    "remote": remote_url,
                    "local": web_path,
                    "reason": "image_cache_disabled",
                    "utc": _utc(),
                }
            )
            counters["assets_missing"] += 1
            obj[local_key] = None
            continue

        ok = download_asset(remote_url, file_path)
        if ok:
            counters["assets_downloaded"] += 1
            if is_provider_logo:
                mirror_provider_logo(file_path, filename)
        else:
            errors.append(
                {
                    "type": "asset_missing",
                    "path": f"{path}.{key}".strip("."),
                    "remote": remote_url,
                    "local": web_path,
                    "reason": "download_failed",
                    "utc": _utc(),
                }
            )
            counters["assets_missing"] += 1
            obj[local_key] = None

    for k, v in obj.items():
        next_kind = kind
        if isinstance(v, dict) and "season_number" in v:
            next_kind = "season"
        if isinstance(v, dict) and "episode_number" in v:
            next_kind = "episode"
        scan_assets(v, cfg, next_kind, errors, counters, f"{path}.{k}".strip("."))


def count_asset_missing(errors: List[Dict[str, Any]]) -> int:
    return sum(1 for e in errors if e.get("type") == "asset_missing")


def main() -> int:
    tmdb_key = (os.getenv("API_TMDB_KEY") or "").strip()
    tmdb_token = (os.getenv("API_TMDB_TOKEN") or "").strip()
    if not tmdb_key and not tmdb_token:
        print("ERROR: Missing TMDB creds. Set API_TMDB_KEY or API_TMDB_TOKEN.")
        return 2

    if not DATA_JSON.exists():
        print("ERROR: Missing data/data.json (run fetch_trakt_primary.py first).")
        return 3

    cfg = load_jsonc(CONFIG_JSON)
    data = json.loads(read_text(DATA_JSON))

    shows = data.get("shows") or []
    movies = data.get("movies") or []
    ensure_dir(provider_logo_mirror_path("placeholder").parent)
    errors = data.setdefault("errors", [])
    errors[:] = [e for e in errors if e.get("type") != "asset_missing"]

    counters = {
        "assets_expected": 0,
        "assets_downloaded": 0,
        "assets_missing": 0,
        "assets_skipped": 0,
        "provider_items_filtered": 0,
    }

    allowed_regions = ["CA", "US", "UK", "AU"]

    # Movies: fetch poster/backdrop + providers only
    for m in movies:
        tmdb_id = m.get("tmdb_id")
        if not isinstance(tmdb_id, int):
            continue
        try:
            details = tmdb_get(f"/movie/{tmdb_id}", tmdb_key, tmdb_token, params={"language": "en-US"})
            providers = tmdb_get(f"/movie/{tmdb_id}/watch/providers", tmdb_key, tmdb_token)

            m["poster_path"] = details.get("poster_path") or m.get("poster_path")
            m["backdrop_path"] = details.get("backdrop_path") or m.get("backdrop_path")
            filtered, removed = filter_watch_providers(providers, allowed_regions)
            m["watch_providers"] = filtered
            if removed:
                counters["provider_items_filtered"] += 1
        except Exception as ex:
            errors.append({"type": "tmdb_movie", "tmdb_id": tmdb_id, "message": str(ex)[:200], "utc": _utc()})

    fetch_season_details = bool((cfg.get("image_cache") or {}).get("fetch_season_details", False))

    # Shows: fetch poster/backdrop + logo + providers + optional season/episode stills
    for s in shows:
        tmdb_id = s.get("tmdb_id")
        if not isinstance(tmdb_id, int):
            continue
        try:
            details = tmdb_get(f"/tv/{tmdb_id}", tmdb_key, tmdb_token, params={"language": "en-US"})
            providers = tmdb_get(f"/tv/{tmdb_id}/watch/providers", tmdb_key, tmdb_token)
            images = tmdb_get(f"/tv/{tmdb_id}/images", tmdb_key, tmdb_token, params={"include_image_language": "en,null"})
            logos = (images or {}).get("logos") or []
            logo_path = logos[0].get("file_path") if logos else None

            s["poster_path"] = details.get("poster_path") or s.get("poster_path")
            s["backdrop_path"] = details.get("backdrop_path") or s.get("backdrop_path")
            if logo_path:
                s["show_logo_tmdb"] = logo_path
            filtered, removed = filter_watch_providers(providers, allowed_regions)
            s["watch_providers"] = filtered
            if removed:
                counters["provider_items_filtered"] += 1
            if "created_by" in s:
                s.pop("created_by", None)

            if fetch_season_details:
                seasons = s.get("seasons") or []
                for season in seasons:
                    season_num = season.get("season_number")
                    if not isinstance(season_num, int):
                        continue
                    try:
                        season_details = tmdb_get(f"/tv/{tmdb_id}/season/{season_num}", tmdb_key, tmdb_token, params={"language": "en-US"})
                        season["poster_path"] = season_details.get("poster_path") or season.get("poster_path")
                        eps_by_num = {
                            int(e.get("episode_number")): e
                            for e in (season_details.get("episodes") or [])
                            if isinstance(e.get("episode_number"), int)
                        }
                        for ep in season.get("episodes") or []:
                            ep_num = ep.get("episode_number")
                            if not isinstance(ep_num, int) or ep_num not in eps_by_num:
                                continue
                            tmdb_ep = eps_by_num[ep_num]
                            still_path = tmdb_ep.get("still_path")
                            if still_path:
                                ep["still_path"] = still_path
                    except Exception:
                        continue
        except Exception as ex:
            errors.append({"type": "tmdb_show", "tmdb_id": tmdb_id, "message": str(ex)[:200], "utc": _utc()})

    # Asset scan + download for all remote image keys
    scan_assets(shows, cfg, "show", errors, counters, "shows")
    scan_assets(movies, cfg, "movie", errors, counters, "movies")
    for s in shows:
        prune_watch_providers(s, errors, counters, "shows")
    for m in movies:
        prune_watch_providers(m, errors, counters, "movies")

    asset_missing_count = count_asset_missing(errors)
    counters["assets_missing"] = asset_missing_count
    data["meta"]["tmdb_assets_utc"] = _utc()
    data["meta"]["assets_expected"] = counters["assets_expected"]
    data["meta"]["assets_downloaded"] = counters["assets_downloaded"]
    data["meta"]["assets_skipped"] = counters["assets_skipped"]
    data["meta"]["assets_missing"] = asset_missing_count
    data["meta"]["provider_items_filtered"] = counters["provider_items_filtered"]

    DATA_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[fetch_tmdb_assets] updated {DATA_JSON} (shows={len(shows)} movies={len(movies)})")
    print(
        "[fetch_tmdb_assets] assets expected=%s downloaded=%s skipped=%s missing=%s"
        % (counters["assets_expected"], counters["assets_downloaded"], counters["assets_skipped"], counters["assets_missing"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
