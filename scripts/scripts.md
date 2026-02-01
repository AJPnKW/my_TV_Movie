# my_TV_Movie — scripts reference (scripts.md)

## Pipeline entrypoints

| Script | Role | Called by | Typical use |
|---|---|---|---|
| `scripts/run_pipeline_full.py` | Orchestrates: parse → TMDB → Trakt IDs → QA | Manual (local) | One command to run the full pipeline locally |
| `scripts/fetch_trakt_primary.py` | Build `data/data.json` from Trakt (primary source of truth) | `run_pipeline_full.py` (TRAKT_PRIMARY=1) | Canonical Trakt dataset builder |
| `scripts/fetch_tmdb_assets.py` | Augment Trakt dataset with TMDB assets + metadata | `run_pipeline_full.py` (TRAKT_PRIMARY=1) | Image/logos/providers enrichment |
| `scripts/parse_txt_to_json.py` | Parse `inputs/*.txt` into `data/inputs_parsed.json` (now de-dupes per list) | `run_pipeline_full.py` and GitHub Actions | Converts your human-edited lists into structured IDs |
| `scripts/fetch_tmdb.py` | Build `data/data.json` from TMDB + `web/config.json` and compute image/link fields | `run_pipeline_full.py` and GitHub Actions | Generates the main dataset used by the UI |
| `scripts/fetch_trakt.py` | Resolve Trakt IDs (movie/show) for items in `data/data.json` | `run_pipeline_full.py` and GitHub Actions | Ensures `trakt_id` exists for sync mapping |
| `scripts/trakt_sync_watch_state.py` | Pull Trakt user watch-state into `data/data.json` (OAuth) | GitHub Actions (optional), manual | Populates watched/progress state (movies + episodes) |
| `scripts/qa_missing_trakt_ids.py` | QA: items missing `trakt_id` | `run_pipeline_full.py` and GitHub Actions | Validates Trakt ID coverage |
| `scripts/qa_pipeline_integrity.py` | QA: integrity checks for `data/data.json` | `run_pipeline_full.py` and GitHub Actions | Detect schema/field issues early |

---

## Keep / archive matrix

| Script | Keep? | Why |
|---|---:|---|
| `run_pipeline_full.py` | ✅ | canonical local runner |
| `parse_txt_to_json.py` | ✅ | canonical TXT → JSON input parser |
| `fetch_tmdb.py` | ✅ | canonical TMDB dataset builder |
| `fetch_trakt.py` | ✅ | canonical Trakt ID resolver |
| `fetch_trakt_primary.py` | ✅ | Trakt primary dataset builder |
| `fetch_tmdb_assets.py` | ✅ | TMDB asset augment (Trakt primary) |
| `trakt_sync_watch_state.py` | ✅ | canonical Trakt watched/progress pull (user state) |
| `qa_missing_trakt_ids.py` | ✅ | needed guardrail |
| `qa_pipeline_integrity.py` | ✅ | needed guardrail |
| `sync_trakt.py` | 🟨 archive | wrapper only; does **not** sync *to* Trakt |
| `fetch_tvmaze.py` | 🟨 optional | only needed when you start using TVMaze IDs in UI/data |

---

## How to run (manual)

| Goal | Command | Outputs |
|---|---|---|
| Full local pipeline | `python scripts/run_pipeline_full.py` | logs in `logs/`, `data/inputs_parsed.json`, `data/data.json` |
| Trakt-primary pipeline | `TRAKT_PRIMARY=1 python scripts/run_pipeline_full.py` | `data/data.json` (Trakt primary) + TMDB assets |
| Parse lists only | `python scripts/parse_txt_to_json.py` | `data/inputs_parsed.json` |
| TMDB build only | `python scripts/fetch_tmdb.py` | `data/data.json` |
| Trakt ID resolve only | `python scripts/fetch_trakt.py` | updates `data/data.json` |
| Pull watch-state | `python scripts/trakt_sync_watch_state.py` | updates `data/data.json` and may write `data/trakt_tokens_latest.json` |

---

## Inputs / outputs per script

### `parse_txt_to_json.py`
| Item | Value |
|---|---|
| Inputs | `inputs/tv_list.txt`, `inputs/movies_list.txt`, `inputs/watchlist.txt` |
| Output | `data/inputs_parsed.json` |
| De-dup | By `tmdb_id` within each list (tv / movies / watchlist) |
| Exit codes | `0` success, `>0` parse/write failure |

### `fetch_tmdb.py`
| Item | Value |
|---|---|
| Inputs | `data/inputs_parsed.json` (preferred), else TXT fallbacks; `web/config.json`; `API_TMDB_KEY` |
| Output | `data/data.json` |
| What it builds | Movies + shows dataset, image path fields, streaming link fields |
| Exit codes | non-zero on missing config/keys/network failures |

### `fetch_trakt.py`
| Item | Value |
|---|---|
| Inputs | `data/data.json`; Trakt client id/secret (public lookup) |
| Output | updates `data/data.json` with `trakt_id` where possible |
| What it does | **ID mapping** (TMDB→Trakt), not watched/progress state |
| Exit codes | `3` if `data/data.json` missing; otherwise non-zero on failures |

### `trakt_sync_watch_state.py`
| Item | Value |
|---|---|
| Inputs | `data/data.json`; Trakt OAuth tokens (secrets/env) |
| Output | updates `data/data.json` with watch-state; may write `data/trakt_tokens_latest.json` |
| What it does | Pulls watched/progress from Trakt (`/sync/watched/*`, `/sync/history` style endpoints) |
| Exit codes | non-zero on auth failures (401/403), network, schema issues |

### `sync_trakt.py` (legacy)
| Item | Value |
|---|---|
| Role | Wrapper runner around `fetch_trakt.py` |
| Important | Does **NOT** push local state *to* Trakt (no POST sync calls) |

---

## Data coverage checklist (requested vs implemented)
This is the **current** state of the pipeline (what `fetch_tmdb.py` actually builds today):

| Group | Requested by you | In `data/data.json` today |
|---|---|---|
| Movies: core fields (poster/backdrop/overview/status/popularity/votes/runtime/homepage/imdb_id/genres) | ✅ | ✅ |
| TV: core fields (poster/backdrop/overview/status/popularity/votes/networks/created_by/origin_country/etc.) | ✅ | ✅ |
| TV seasons + episodes (with traceable links) | ✅ | ✅ (after the deep-build fix is applied) |
| Collections (details + images) | ✅ | ❌ (not yet implemented) |
| Watch providers (per region) | ✅ | ❌ (not yet implemented) |
| Certifications / content ratings | ✅ | ❌ (not yet implemented) |
| Trakt IDs for movies/shows | ✅ | ✅ |
| Trakt watched/progress for movies + episodes | ✅ | ✅ (via `trakt_sync_watch_state.py`) |
### `fetch_trakt_primary.py`
| Item | Value |
|---|---|
| Inputs | Trakt OAuth tokens; Trakt API |
| Output | `data/data.json` (Trakt primary) |
| What it does | Pulls shows/movies/seasons/episodes + user data + trends |

### `fetch_tmdb_assets.py`
| Item | Value |
|---|---|
| Inputs | `data/data.json` (Trakt primary); TMDB API |
| Output | updates `data/data.json` with TMDB assets + metadata |
| What it does | Adds posters/backdrops/logos/stills + providers |
