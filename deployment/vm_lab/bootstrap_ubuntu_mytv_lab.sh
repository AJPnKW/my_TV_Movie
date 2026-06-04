#!/usr/bin/env bash
set -Eeuo pipefail

LOG_FILE="/var/log/mytv-lab-bootstrap.log"
APP_ROOT="/opt/mytv_movie"
ENV_EXAMPLE="${APP_ROOT}/.env.example"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TRACKED_ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
VENV_ROOT="${APP_ROOT}/.venv"
APP_USER="mytv_movie"
POSTGRES_DB="mytv_movie"
POSTGRES_USER="mytv_movie"
LOCAL_DSN="postgresql:///mytv_movie?host=/var/run/postgresql"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run this script with sudo or as root." >&2
  exit 1
fi

mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"
chmod 0644 "${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

trap 'echo "ERROR: bootstrap failed at line ${LINENO}. See ${LOG_FILE}."' ERR

echo "my_TV_Movie X1 lab bootstrap started: $(date -Is)"

if [[ ! -r /etc/os-release ]]; then
  echo "ERROR: /etc/os-release is missing; this bootstrap targets Ubuntu Server LTS." >&2
  exit 1
fi

# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "ERROR: unsupported OS '${ID:-unknown}'. Use Ubuntu Server LTS." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  ffmpeg \
  git \
  nginx \
  libpq-dev \
  postgresql \
  postgresql-contrib \
  python3 \
  python3-pip \
  python3-venv

if ! getent group "${APP_USER}" >/dev/null 2>&1; then
  groupadd --system "${APP_USER}"
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --gid "${APP_USER}" --home-dir "${APP_ROOT}" --shell /usr/sbin/nologin "${APP_USER}"
else
  usermod --gid "${APP_USER}" "${APP_USER}"
fi

mkdir -p "${APP_ROOT}"
chmod 0755 "${APP_ROOT}"

if [[ -f "${TRACKED_ENV_EXAMPLE}" ]]; then
  install -m 0644 "${TRACKED_ENV_EXAMPLE}" "${ENV_EXAMPLE}"
else
  cat > "${ENV_EXAMPLE}" <<'ENVEOF'
# my_TV_Movie X1 lab VM example environment.
# Copy this file to .env on the VM and fill values locally.
# Do not commit .env or real secrets.

MYTV_ENV=lab
MYTV_APP_ROOT=/opt/mytv_movie
MYTV_WEB_HOST=0.0.0.0
MYTV_WEB_PORT=80
MYTV_API_HOST=127.0.0.1
MYTV_API_PORT=8000
MYTV_POSTGRES_DSN=postgresql:///mytv_movie?host=/var/run/postgresql

POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=mytv_movie
POSTGRES_USER=mytv_movie

TRAKT_CLIENT_ID=replace_with_local_value
TRAKT_CLIENT_SECRET=replace_with_local_secret
ENVEOF
  chmod 0644 "${ENV_EXAMPLE}"
fi

systemctl enable --now postgresql
systemctl enable --now nginx

if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" | grep -qx 1; then
  runuser -u postgres -- createuser --login "${POSTGRES_USER}"
fi

if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -qx 1; then
  runuser -u postgres -- createdb --owner "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

python3 -m venv "${VENV_ROOT}"
"${VENV_ROOT}/bin/python" -m pip install --upgrade pip
if [[ -f "${APP_ROOT}/deployment/api/requirements-server.txt" ]]; then
  "${VENV_ROOT}/bin/python" -m pip install -r "${APP_ROOT}/deployment/api/requirements-server.txt"
else
  "${VENV_ROOT}/bin/python" -m pip install "psycopg[binary]>=3.2,<4"
fi
chmod -R a+rX "${VENV_ROOT}"

runuser -u "${APP_USER}" -- env MYTV_POSTGRES_DSN="${LOCAL_DSN}" \
  "${VENV_ROOT}/bin/python" -c "import psycopg; conn=psycopg.connect('${LOCAL_DSN}'); print(conn.execute('SELECT current_database(), current_user').fetchone()); conn.close()"

if [[ -f "${APP_ROOT}/deployment/postgres/live_validate_postgres.py" ]]; then
  runuser -u "${APP_USER}" -- env \
    MYTV_REPO_ROOT="${APP_ROOT}" \
    MYTV_POSTGRES_DSN="${LOCAL_DSN}" \
    "${VENV_ROOT}/bin/python" "${APP_ROOT}/deployment/postgres/live_validate_postgres.py"
else
  echo "Repo live validator is not present yet; run deployment/vm_lab/validate_mytv_lab.sh after the repo is checked out at ${APP_ROOT}."
fi

echo "Installed versions:"
git --version
curl --version | head -n 1
python3 --version
pip3 --version
"${VENV_ROOT}/bin/python" -c "import psycopg; print('psycopg', psycopg.__version__)"
psql --version
nginx -v
ffmpeg -version | head -n 1
ffprobe -version | head -n 1

echo "my_TV_Movie X1 lab bootstrap completed: $(date -Is)"
