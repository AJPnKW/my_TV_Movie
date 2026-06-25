#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="/opt/mytv_movie"
VENV_ROOT="${APP_ROOT}/.venv"
APP_USER="mytv_movie"
POSTGRES_DB="mytv_movie"
POSTGRES_USER="mytv_movie"
LOCAL_DSN="postgresql:///mytv_movie?host=/var/run/postgresql"
FAILURES=0

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*" >&2; FAILURES=$((FAILURES + 1)); }

require_command() {
  local command_name="$1"
  if command -v "${command_name}" >/dev/null 2>&1; then
    pass "${command_name} found: $(command -v "${command_name}")"
  else
    fail "${command_name} is missing"
  fi
}

require_service_active() {
  local service_name="$1"
  if systemctl is-active --quiet "${service_name}"; then
    pass "${service_name} service is active"
  else
    fail "${service_name} service is not active"
  fi
}

require_port_listening() {
  local port="$1"
  local label="$2"
  if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${port}$"; then
    pass "${label} is listening on tcp/${port}"
  else
    fail "${label} is not listening on tcp/${port}"
  fi
}

echo "my_TV_Movie HP media VM validation started: $(date -Is)"

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "ubuntu" ]] && pass "OS is Ubuntu: ${PRETTY_NAME:-unknown}" || fail "OS is not Ubuntu: ${ID:-unknown}"
  [[ "${VERSION:-}" == *"LTS"* ]] && pass "OS version is marked LTS" || fail "OS version is not marked LTS: ${VERSION:-unknown}"
else
  fail "/etc/os-release is missing"
fi

require_command git
require_command curl
require_command jq
require_command python3
require_command psql
require_command nginx
require_command ffmpeg
require_command ffprobe
require_command rsync
require_command ss

require_service_active postgresql
require_service_active nginx
require_service_active mytv-api.service

require_port_listening 80 "Nginx HTTP"
require_port_listening 5432 "PostgreSQL"
require_port_listening 8000 "mytv-api"

[[ -d "${APP_ROOT}" ]] && pass "app root exists: ${APP_ROOT}" || fail "app root is missing: ${APP_ROOT}"
[[ -f "${APP_ROOT}/index.html" ]] && pass "root redirect exists" || fail "root redirect is missing"
[[ -f "${APP_ROOT}/web/index.html" ]] && pass "web app shell exists" || fail "web app shell is missing"
[[ -f "${APP_ROOT}/data/data.json" ]] && pass "generated data JSON exists" || fail "generated data JSON is missing"
[[ -f "${APP_ROOT}/.env.example" ]] && pass ".env.example exists" || fail ".env.example is missing"
[[ ! -f "${APP_ROOT}/.env" ]] && pass ".env is not created by bootstrap" || pass ".env exists as local VM configuration"

if id "${APP_USER}" >/dev/null 2>&1; then
  pass "application OS user exists: ${APP_USER}"
else
  fail "application OS user is missing: ${APP_USER}"
fi

if runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" | grep -qx 1; then
  pass "PostgreSQL app role exists: ${POSTGRES_USER}"
else
  fail "PostgreSQL app role is missing: ${POSTGRES_USER}"
fi

if runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -qx 1; then
  pass "PostgreSQL app database exists: ${POSTGRES_DB}"
else
  fail "PostgreSQL app database is missing: ${POSTGRES_DB}"
fi

if [[ -x "${VENV_ROOT}/bin/python" ]] && "${VENV_ROOT}/bin/python" -c "import psycopg" >/dev/null 2>&1; then
  pass "server-mode venv and psycopg are installed"
else
  fail "server-mode venv or psycopg is missing"
fi

if [[ -x "${VENV_ROOT}/bin/python" ]]; then
  if runuser -u "${APP_USER}" -- env MYTV_REPO_ROOT="${APP_ROOT}" MYTV_POSTGRES_DSN="${LOCAL_DSN}" \
    "${VENV_ROOT}/bin/python" "${APP_ROOT}/deployment/postgres/live_validate_postgres.py"; then
    pass "live PostgreSQL schema/write/read/rollback validation passed"
  else
    fail "live PostgreSQL validation failed"
  fi
fi

if runuser -u "${APP_USER}" -- psql "${LOCAL_DSN}" -tAc "SELECT COUNT(*) > 0 FROM media_items" | grep -qx t; then
  pass "PostgreSQL media_items contains migrated catalog rows"
else
  fail "PostgreSQL media_items has no migrated catalog rows"
fi

if curl -fsS http://127.0.0.1:8000/api/v1/health | jq -e '.status == "ok" and .postgres == "ok"' >/dev/null; then
  pass "direct API health is ok"
else
  fail "direct API health failed"
fi

if curl -fsS http://127.0.0.1/api/v1/health | jq -e '.status == "ok" and .postgres == "ok"' >/dev/null; then
  pass "Nginx reverse-proxied API health is ok"
else
  fail "Nginx reverse-proxied API health failed"
fi

if curl -fsS http://127.0.0.1/ | grep -Eq 'web/index.html|my_TV_Movie'; then
  pass "Nginx serves the app root"
else
  fail "Nginx app root check failed"
fi

if [[ "${FAILURES}" -eq 0 ]]; then
  echo "my_TV_Movie HP media VM validation passed."
else
  echo "my_TV_Movie HP media VM validation failed with ${FAILURES} issue(s)." >&2
  exit 1
fi
