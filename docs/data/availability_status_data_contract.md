# Availability Status Data Contract

## Source file
Recommended path:
`data/watch_source_availability.json`

## Source file structure
```json
{
  "version": "1.1.0",
  "generated_at": "2026-03-21T00:00:00Z",
  "defaults": {
    "validation_mode": "structural",
    "entities": {
      "movie": { "requires_url": true, "preferred_sources": ["videasy", "vidsrc", "local"] },
      "show": { "requires_url": true, "preferred_sources": ["videasy", "vidsrc"] },
      "season": { "requires_url": true, "preferred_sources": ["videasy", "vidsrc"] },
      "episode": { "requires_url": true, "preferred_sources": ["videasy", "vidsrc", "local"] }
    }
  },
  "records": [
    {
      "entity_type": "movie",
      "entity_key": "movie:1319951",
      "status_override": "available",
      "primary_watch_url": "https://player.videasy.net/movie/1319951",
      "requires_url": true,
      "url_test_result": "pass",
      "release_date_override": "2025-07-02",
      "reason": "manual or computed source note"
    }
  ]
}
```

## Required source fields
| Field | Required | Notes |
|---|---:|---|
| `entity_type` | Yes | `movie`, `show`, `season`, `episode` |
| `entity_key` | Yes | Stable key |
| `defaults` | Yes | Canonical per-entity source preference and validation mode |
| `status_override` | No | Optional manual override |
| `primary_watch_url` | No | Canonical primary URL |
| `requires_url` | No | Defaults by logic if needed |
| `url_test_result` | No | `pass`, `fail`, `skip`, `unknown` |
| `reason` | No | Traceability |

## Required target fields in `data.json`
| Field | Required |
|---|---:|
| `availability_status` | Yes |
| `availability_checked_at` | Yes |
| `availability_source` | Yes |
| `availability_reason` | Yes |

## Matching rules Codex must verify against the real repo
| Entity | Preferred matching order |
|---|---|
| Movie | `tmdb_id` → `id` |
| Show | `tmdb_id` → `id` |
| Season | `show.tmdb_id + season_number` |
| Episode | `show.tmdb_id + season_number + episode_number` |

## Composite key baseline
| Entity | Baseline composite key |
|---|---|
| Season | `show:{show_tmdb_id}:season:{season_number}` |
| Episode | `show:{show_tmdb_id}:season:{season_number}:episode:{episode_number}` |

## Live repo key note
In the current repo:
- movies and shows already expose both `tmdb_id` and `id`
- seasons expose `id` and `season_number`
- episodes expose `id`, `show_id`, `season_number`, and `episode_number`
- the enrichment layer matches seasons and episodes by the composite show/season/episode key above
