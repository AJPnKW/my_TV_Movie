#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="/opt/mytv_movie"
VENV_ROOT="${APP_ROOT}/.venv"
APP_USER="mytv_movie"
POSTGRES_DB="mytv_movie"
POSTGRES_USER="mytv_movie"
LOCAL_DSN="postgresql:///mytv_movie?host=/var/run/postgresql"
FAILURES=0

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
  FAILURES=$((FAILURES + 1))
}

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
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${port}$"; then
      pass "${label} is listening on tcp/${port}"
    else
      fail "${label} is not listening on tcp/${port}"
    fi
  else
    fail "cannot validate tcp/${port}; ss command is missing"
  fi
}

require_port_free() {
  local port="$1"
  local label="$2"
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${port}$"; then
      fail "${label} tcp/${port} is already occupied"
    else
      pass "${label} tcp/${port} is available"
    fi
  else
    fail "cannot validate tcp/${port}; ss command is missing"
  fi
}

echo "my_TV_Movie X1 lab validation started: $(date -Is)"

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" == "ubuntu" ]]; then
    pass "OS is Ubuntu: ${PRETTY_NAME:-unknown version}"
    if [[ "${VERSION:-}" == *"LTS"* ]]; then
      pass "OS version is marked LTS"
    else
      fail "OS version is not marked LTS: ${VERSION:-unknown}"
    fi
  else
    fail "OS is not Ubuntu: ${ID:-unknown}"
  fi
else
  fail "/etc/os-release is missing"
fi

require_command git
require_command curl
require_command python3
require_command pip3
require_command psql
require_command nginx
require_command ffmpeg
require_command ffprobe
require_command runuser

require_service_active postgresql
require_service_active nginx

if [[ -d "${APP_ROOT}" ]]; then
  pass "app root exists: ${APP_ROOT}"
  if [[ -d "${APP_ROOT}/.git" ]]; then
    pass "repo checkout exists at ${APP_ROOT}"
  else
    fail "repo checkout is missing at ${APP_ROOT}; live schema validation is impossible"
  fi
else
  fail "app root is missing: ${APP_ROOT}"
fi

if [[ -f "${APP_ROOT}/.env.example" ]]; then
  pass ".env.example exists"
  if grep -Fq "MYTV_POSTGRES_DSN=${LOCAL_DSN}" "${APP_ROOT}/.env.example"; then
    pass ".env.example documents the local lab DSN"
  else
    fail ".env.example does not document MYTV_POSTGRES_DSN=${LOCAL_DSN}"
  fi
else
  fail ".env.example is missing"
fi

if [[ -f "${APP_ROOT}/.env" ]]; then
  fail ".env exists; this foundation should create .env.example only"
else
  pass ".env is not present"
fi

require_port_listening 80 "Nginx HTTP"
require_port_listening 5432 "PostgreSQL"
require_port_free 8000 "Reserved API"

if id "${APP_USER}" >/dev/null 2>&1; then
  pass "application operating-system user exists: ${APP_USER}"
else
  fail "application operating-system user is missing: ${APP_USER}"
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

if [[ -x "${VENV_ROOT}/bin/python" ]]; then
  pass "server-mode Python virtual environment exists"
  if "${VENV_ROOT}/bin/python" -c "import psycopg" >/dev/null 2>&1; then
    pass "psycopg runtime is installed"
  else
    fail "psycopg runtime is missing from ${VENV_ROOT}"
  fi
else
  fail "server-mode Python virtual environment is missing: ${VENV_ROOT}"
fi

LIVE_VALIDATOR="${APP_ROOT}/deployment/postgres/live_validate_postgres.py"
if [[ -f "${LIVE_VALIDATOR}" && -x "${VENV_ROOT}/bin/python" ]] && id "${APP_USER}" >/dev/null 2>&1; then
  if runuser -u "${APP_USER}" -- env \
    MYTV_REPO_ROOT="${APP_ROOT}" \
    MYTV_POSTGRES_DSN="${LOCAL_DSN}" \
    "${VENV_ROOT}/bin/python" "${LIVE_VALIDATOR}"; then
    pass "live PostgreSQL schema/write/read/rollback validation passed"
  else
    fail "live PostgreSQL schema/write/read/rollback validation failed"
  fi
else
  fail "live PostgreSQL validation is not possible; validator, venv, or app user is missing"
fi

if [[ "${FAILURES}" -eq 0 ]]; then
  echo "my_TV_Movie X1 lab validation passed."
else
  echo "my_TV_Movie X1 lab validation failed with ${FAILURES} issue(s)." >&2
  exit 1
fi
