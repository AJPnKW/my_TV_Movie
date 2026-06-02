# MYTV Incident 2026-06-02 — Bootstrap Path and Prompt Delivery Failures

## Summary

The VM migration bootstrap moved the project forward, but the delivery process had repeated script/path defects that should have been caught before the user ran commands.

## User impact

The user had to troubleshoot preventable failures during a copy/paste workflow that was supposed to be low-decision and low-friction.

## Evidence from console output

- `Copy-Item` failed because destination folder `codex_prompts` did not exist.
- `git add codex_prompts` warned that `codex_prompts` is ignored by `.gitignore`.
- `bootstrap_mytv_vm_migration_lab.ps1` later failed with `Run from repo root` even though the prompt showed the shell was in `C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie`.
- Earlier ZIP-driven flow failed when the expected zip was not present locally.
- `docs/_archive/...my_TV_Movies- authoritative spec.tws` showed as modified and was outside current work ownership.

## Root causes

| Defect | Root cause | Required prevention |
|---|---|---|
| ZIP dependency failed | Script assumed a ChatGPT artifact had been downloaded to Downloads | Do not depend on a local ZIP unless script first validates exact path and stops before copy/run steps |
| Missing destination folder | Copy commands did not create destination folder before copying | Every script must create destination folders before copying |
| Ignored `codex_prompts` | Prompt files were placed in a gitignored folder | Store durable prompts under a tracked path or use `git add -f` intentionally and document why |
| Repo-root false negative | Script only checked `.git` path and did not report diagnostics | Repo-root detection must print cwd, expected repo, `.git` status, git top-level, and fail with actionable detail |
| Cascading errors | Commands continued after failure in manually pasted sequence | User-facing command blocks must be fail-fast and not continue after a failed setup prerequisite |
| Unowned modified archive file | Existing modified binary/archive file was unrelated to VM work | Scripts and Codex sessions must report unrelated changes and avoid committing them unless explicitly assigned |

## New scripting standard

All generated PowerShell scripts and command blocks must:

1. Use fail-fast behavior.
2. Validate every expected input path before use.
3. Create destination folders before copy/write.
4. Avoid ZIP dependencies where GitHub direct-write is possible.
5. Detect repo root using `git rev-parse --show-toplevel` first, not only `.git` folder checks.
6. Print diagnostic values before throwing:
   - current directory
   - resolved repo root
   - expected repo root
   - script path
   - missing path
7. Stop before later steps if a prerequisite fails.
8. Never assume ignored folders can be committed.
9. Record unrelated working-tree changes separately.
10. Produce a run folder with `execution.log.txt`, `summary.txt`, and `environment_evidence.json`.

## Current project state after incident

Completed:

- VM deployment folders created locally and pushed.
- Deployment README created.
- API draft created.
- PostgreSQL schema draft created.
- VM migration bootstrap docs created.
- Lime Green Codex completed and pushed VM foundation.
- Forest Green Codex completed and pushed server-mode architecture alignment.

Known open clean-up:

- `codex_prompts` local folder is ignored and should not be relied on as durable tracked source unless policy changes.
- `scripts/bootstrap_mytv_vm_migration_lab.ps1` repo-root detection should be hardened.
- A clean tracked prompt location should be used for future prompts, such as `docs/codex_prompts/` or `deployment/docs/codex_prompts/`.
- Unrelated modified `.tws` archive file must be left alone or restored deliberately.

## Rule added

A generated script is not acceptable unless it validates paths, creates destination folders, stops on prerequisite failure, and logs enough evidence for the user to paste back without manual interpretation.
