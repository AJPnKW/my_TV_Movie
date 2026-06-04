# PostgreSQL Runtime Setup and Live Validation

PostgreSQL is the primary writable store in server mode. JSON remains import/export/static fallback. Image and media binaries remain files/assets by default.

## X1 Lab Runtime

The Lime Green bootstrap creates:

- local operating-system service account: `mytv_movie`
- local PostgreSQL login role: `mytv_movie`
- local PostgreSQL database owned by that role: `mytv_movie`
- API/runtime virtual environment: `/opt/mytv_movie/.venv`
- psycopg v3 runtime in that virtual environment
- example peer-auth DSN in `/opt/mytv_movie/.env.example`

Default local lab DSN:

```text
postgresql:///mytv_movie?host=/var/run/postgresql
```

This DSN uses PostgreSQL local Unix-socket peer authentication when commands run as the `mytv_movie` operating-system account. It does not require a committed password or expose PostgreSQL beyond the VM.

## Bootstrap and Live Validation

From the repo checkout on the Ubuntu X1 lab VM:

```bash
sudo bash deployment/vm_lab/bootstrap_ubuntu_mytv_lab.sh
sudo bash deployment/vm_lab/validate_mytv_lab.sh
```

Run the live validation directly:

```bash
sudo runuser -u mytv_movie -- env \
  MYTV_REPO_ROOT=/opt/mytv_movie \
  MYTV_POSTGRES_DSN='postgresql:///mytv_movie?host=/var/run/postgresql' \
  /opt/mytv_movie/.venv/bin/python \
  /opt/mytv_movie/deployment/postgres/live_validate_postgres.py
```

The live validator:

1. connects to PostgreSQL
2. verifies the current database and app user
3. applies `schema_v1.sql`
4. verifies required tables
5. inserts a temporary `runtime_config` row
6. reads the row back
7. rolls the transaction back
8. confirms the temporary row no longer exists

Any failed check exits non-zero.

## Static Validation

These checks do not require a live database:

```bash
python deployment/postgres/validate_schema.py
python deployment/postgres/apply_schema.py --dry-run
```

Live database completion is not established by static validation alone.
