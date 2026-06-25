#!/usr/bin/env bash
set -Eeuo pipefail

LOG_FILE="/var/log/mytv-hp-bootstrap.log"
APP_ROOT="/opt/mytv_movie"
VENV_ROOT="${APP_ROOT}/.venv"
APP_USER="mytv_movie"
POSTGRES_DB="mytv_movie"
POSTGRES_USER="mytv_movie"
LOCAL_DSN="postgresql:///mytv_movie?host=/var/run/postgresql"
API_SERVICE="/etc/systemd/system/mytv-api.service"
NGINX_SITE="/etc/nginx/sites-available/mytv_movie"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run this script with sudo or as root." >&2
  exit 1
fi

mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"
chmod 0644 "${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

trap 'echo "ERROR: HP bootstrap failed at line ${LINENO}. See ${LOG_FILE}."' ERR

echo "my_TV_Movie HP media VM bootstrap started: $(date -Is)"

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
  iproute2 \
  jq \
  libpq-dev \
  nginx \
  postgresql \
  postgresql-contrib \
  python3 \
  python3-pip \
  python3-venv \
  rsync

if ! getent group "${APP_USER}" >/dev/null 2>&1; then
  groupadd --system "${APP_USER}"
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --gid "${APP_USER}" --home-dir "${APP_ROOT}" --shell /usr/sbin/nologin "${APP_USER}"
else
  usermod --gid "${APP_USER}" "${APP_USER}"
fi

mkdir -p "${APP_ROOT}"
rsync -a --exclude ".git" --exclude ".env" --exclude ".venv" "${REPO_ROOT}/" "${APP_ROOT}/"
install -m 0644 "${APP_ROOT}/deployment/vm_prod/.env.example" "${APP_ROOT}/.env.example"
chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"
chmod 0755 "${APP_ROOT}"

systemctl enable --now postgresql

if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" | grep -qx 1; then
  runuser -u postgres -- createuser --login "${POSTGRES_USER}"
fi

if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -qx 1; then
  runuser -u postgres -- createdb --owner "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

python3 -m venv "${VENV_ROOT}"
"${VENV_ROOT}/bin/python" -m pip install --upgrade pip
"${VENV_ROOT}/bin/python" -m pip install -r "${APP_ROOT}/deployment/api/requirements-server.txt"
chown -R "${APP_USER}:${APP_USER}" "${VENV_ROOT}"
chmod -R a+rX "${VENV_ROOT}"

runuser -u "${APP_USER}" -- env MYTV_POSTGRES_DSN="${LOCAL_DSN}" \
  "${VENV_ROOT}/bin/python" "${APP_ROOT}/deployment/postgres/apply_schema.py" --apply

runuser -u "${APP_USER}" -- env MYTV_REPO_ROOT="${APP_ROOT}" MYTV_POSTGRES_DSN="${LOCAL_DSN}" \
  "${VENV_ROOT}/bin/python" "${APP_ROOT}/deployment/postgres/json_migration.py" --apply

install -m 0644 "${APP_ROOT}/deployment/api/mytv-api.service.example" "${API_SERVICE}"

cat > "${NGINX_SITE}" <<'NGINXEOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root /opt/mytv_movie;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF

ln -sfn "${NGINX_SITE}" /etc/nginx/sites-enabled/mytv_movie
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  unlink /etc/nginx/sites-enabled/default
fi
nginx -t

systemctl daemon-reload
systemctl enable --now mytv-api.service
systemctl enable --now nginx
systemctl reload nginx

curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null
curl -fsS http://127.0.0.1/api/v1/health >/dev/null

echo "Installed versions:"
git --version
curl --version | head -n 1
python3 --version
"${VENV_ROOT}/bin/python" -c "import psycopg; print('psycopg', psycopg.__version__)"
psql --version
nginx -v
ffmpeg -version | head -n 1
ffprobe -version | head -n 1

echo "my_TV_Movie HP media VM bootstrap completed: $(date -Is)"
