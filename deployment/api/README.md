# Server Mode API Scaffold

This folder now contains the first runnable API scaffold for the server-backed app design.

## Run

```bash
python deployment/api/server_mode_api.py
```

Default bind:

- host: `127.0.0.1`
- port: `8000`
- base path: `/api/v1`

Environment:

- `MYTV_REPO_ROOT`: optional repo/app root override; VM target is `/opt/mytv_movie`
- `MYTV_API_HOST`: optional bind host
- `MYTV_API_PORT`: optional bind port
- `MYTV_API_BASE_PATH`: optional base path
- `MYTV_POSTGRES_DSN` or `DATABASE_URL`: PostgreSQL DSN

X1 lab default DSN from `.env.example`:

```text
postgresql:///mytv_movie?host=/var/run/postgresql
```

Run the API as the local `mytv_movie` operating-system account so PostgreSQL peer authentication matches the `mytv_movie` database role.

No secret values are stored in this scaffold. Runtime config secret values must use external secret storage and `secret_ref` only.

Install the tracked server dependency into the VM runtime:

```bash
/opt/mytv_movie/.venv/bin/python -m pip install -r /opt/mytv_movie/deployment/api/requirements-server.txt
```

## Current Behavior

- `GET /api/v1/health` reports API, PostgreSQL, JSON fallback, and ffprobe/ffmpeg status.
- Catalog/provider/runtime reads fall back to generated JSON when PostgreSQL is unavailable.
- Catalog fallback reads the top-level generated `data/data.json` movie/show arrays so the API is useful before the database is populated.
- State-changing writes require configured PostgreSQL plus psycopg. If unavailable, the API reports the missing write path instead of pretending the write succeeded.
- Trakt and Media Library job endpoints support dry-run plans and queue records through PostgreSQL when configured.

## VM Service Template

`deployment/api/mytv-api.service.example` is a systemd template for the Lime Green lab foundation. It binds the API to `127.0.0.1:8000` under `/opt/mytv_movie` and leaves Nginx reverse-proxy ownership to the deployment/webserver layer.

## Validation

```bash
python deployment/api/validate_server_mode.py
python deployment/postgres/validate_schema.py
python deployment/postgres/apply_schema.py --dry-run
sudo runuser -u mytv_movie -- env MYTV_POSTGRES_DSN='postgresql:///mytv_movie?host=/var/run/postgresql' /opt/mytv_movie/.venv/bin/python deployment/postgres/live_validate_postgres.py
python deployment/postgres/json_migration.py
python deployment/trakt_sync/trakt_worker.py reconcile
python deployment/media_library/media_library_worker.py scan --profile home
```
