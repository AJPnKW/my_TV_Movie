# Availability Status Solution Design

## Outcome
Implement a normalized availability-status capability for movies, shows, seasons, and episodes without restructuring `inputs.json`.

## Primary decision
Use a separate source-of-truth file and a separate enrichment pass after the current `data.json` build.

## Live repo implementation note
The live repo now resolves availability by combining:
- `data/watch_source_availability.json` defaults and optional per-entity override records
- existing entity `links` data already present in `data/data.json`
- canonical streaming base URLs from `web/config.json`

Default URL validation mode is structural validation of the resolved primary watch URL. Manual record overrides can still force `status_override` and `url_test_result`.

## Final status enum
| Value | Meaning | Notes |
|---|---|---|
| `not_yet_released` | Release date is in the future | Must not be treated as unavailable |
| `available` | Released and primary watch source URL is confirmed working | Positive state |
| `unavailable` | Released and primary watch source URL is missing or failed validation | Negative state |
| `unknown` | No valid determination could be made | Safe fallback |

## Design rules
| Rule | Decision |
|---|---|
| `inputs.json` remains unchanged | Yes |
| `data.json` remains the web-consumption artifact | Yes |
| Source of truth stored outside `data.json` | Yes |
| Episode-level granularity supported | Yes |
| Separate workflow allowed | Yes |
| Separate script allowed | Yes |

## Why this design
| Option | Result | Reason |
|---|---|---|
| Store only in `data.json` | Reject | Rebuild overwrite risk |
| Expand `inputs.json` | Reject | Current structure is not episode-granular and would ripple into the editor |
| Separate source file + enrichment pass | Approve | Lowest disruption and full granularity |

## Mandatory write fields into `data.json`
| Field | Required | Purpose |
|---|---:|---|
| `availability_status` | Yes | UI display field |
| `availability_checked_at` | Yes | Audit/debug timestamp |
| `availability_source` | Yes | Traceability |
| `availability_reason` | Yes | Support/debug |
| `primary_watch_url_tested` | Optional | Traceability |

## Resolution logic
1. Match the entity against the availability source file.
2. If a valid manual override exists, use it.
3. Else resolve the primary watch URL from the source defaults plus the live entity links/config.
4. Future release date => `not_yet_released`
5. Released + URL required + structural/manual URL test pass => `available`
6. Released + URL required + structural/manual URL test fail or missing URL => `unavailable`
7. Missing inputs / failed lookup / non-determinable case => `unknown`

## Non-goals
| Item | Decision |
|---|---|
| Replacing the current build pipeline | No |
| Refactoring the input editor in this change | No |
| Inferring availability by inheritance only | No |

## Phase 2 design notes
- The validation model is now provider-aware against the live `web/config.json` streaming bases.
- Network verification support exists, with timeout/retry/cache controls, but remains disabled in the default repo workflow because third-party stream hosts are not stable enough for CI-grade required checks.
- Explicit overrides remain available at movie/show/season/episode granularity, but phase 2 intentionally did not seed synthetic live overrides where the catalog itself did not justify them.
