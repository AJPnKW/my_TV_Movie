# HP Production Promotion Plan

This folder is reserved for the later HP production VM promotion path. No production bootstrap is defined in this foundation pass.

## Promotion Sequence

1. Validate `mytv-lab-vm01` on Ubuntu Server LTS with the lab bootstrap and validation scripts.
2. Confirm the application, API, PostgreSQL, media tooling, and backup/restore workflow in the X1 lab VM.
3. Capture lab configuration that is safe to promote, excluding secrets and machine-local paths.
4. Build the HP production VM from the lab-proven package and production-specific environment values.
5. Run production validation before moving any user workflow to the HP VM.

## Production Requirements Before Promotion

- Stable HP VM hostname and network address.
- Confirmed CPU, RAM, disk, and media storage allocation.
- PostgreSQL backup and restore procedure.
- Nginx reverse proxy and TLS plan.
- Local secrets management outside Git.
- Rollback path to the static GitHub Pages/runtime fallback.

## Non-Goals For This Pass

- No HP VM creation.
- No production secrets.
- No database schema implementation.
- No API service implementation.
- No media library runtime changes.
