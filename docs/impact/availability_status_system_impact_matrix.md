# Availability Status System Impact Matrix

## System-wide impact
| Area | Impact | Required change | Notes |
|---|---:|---|---|
| `inputs.json` | None | None | Keep stable |
| Input editor | None | None | No structural ripple |
| `data.json` schema | Low | Additive fields | No destructive change |
| Existing build scripts | Low | Chain availability validation/enrichment after TMDB/OMDB/Trakt | Keep baseline intact |
| New enrichment script | High | New script | Main logic location |
| Validation | Medium | New validator/tests | Prevent bad merges |
| Workflows | Medium | Add or chain workflow | Run after current data build |
| Index/listing pages | Low | Render status | Shared helper recommended |
| Detail/popup views | Low | Render status | Same field |
| Episode rows | Low | Render status | Same field |
| Filtering/sorting | Low | Reuse existing availability filters with normalized enum | Implemented in shows/movies |

## Existing repo risks Codex must assess against live repo
| Risk | Why it matters |
|---|---|
| Actual `data.json` location may differ | Paths must match current repo |
| Actual entity key fields may differ | Matching must use real repo fields |
| Actual page/component helpers may already exist | Reuse instead of rebuilding |
| Existing workflows may already have a post-build stage | Integrate there if present |
| Existing CSS/icon system may already define status patterns | Reuse consistent design tokens |
