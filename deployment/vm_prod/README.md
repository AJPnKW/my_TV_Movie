# HP Media VM Deployment

This folder contains the production-oriented HP media VM bootstrap for the
server-mode app. It installs the supporting stack, promotes JSON runtime data
into PostgreSQL, and runs the app behind Nginx.

## Target

- Ubuntu Server LTS on the HP server media VM.
- Application root: `/opt/mytv_movie`.
- Static app and generated JSON fallback: served by Nginx on `80/tcp`.
- API: `mytv-api.service` on `127.0.0.1:8000`, reverse-proxied under `/api/`.
- Database: local PostgreSQL database/user `mytv_movie` through peer-authenticated
  Unix socket DSN `postgresql:///mytv_movie?host=/var/run/postgresql`.
- Media tools: `ffmpeg` and `ffprobe` installed for Media Library workflows.

## Run On The HP VM

From a checked-out copy of this repository on the VM:

```bash
sudo bash deployment/vm_prod/bootstrap_ubuntu_mytv_hp.sh
sudo bash deployment/vm_prod/validate_mytv_hp.sh
```

The bootstrap copies the current repository contents into `/opt/mytv_movie` if
it is launched from a different checkout path. It does not create `.env` or
write real secrets. Local-only settings can be added later in
`/opt/mytv_movie/.env`.

## What The Bootstrap Installs

- Ubuntu packages: Git, Python 3, pip, venv, PostgreSQL, Nginx, libpq,
  ffmpeg/ffprobe, curl, rsync, jq, ca-certificates.
- OS service account and group: `mytv_movie`.
- PostgreSQL login role/database: `mytv_movie`.
- Python virtual environment: `/opt/mytv_movie/.venv`.
- PostgreSQL schema: `deployment/postgres/schema_v1.sql`.
- JSON migration: `deployment/postgres/json_migration.py --apply`.
- systemd service: `mytv-api.service`.
- Nginx site: `/etc/nginx/sites-available/mytv_movie`.

## Validation

`validate_mytv_hp.sh` checks the installed packages, services, ports, app files,
Python dependencies, PostgreSQL schema, migrated catalog counts, API health, and
Nginx reverse proxy health.

## Secrets

No Trakt or production secrets belong in Git. Put local values in
`/opt/mytv_movie/.env` on the VM only. The tracked `.env.example` documents the
expected variable names.
