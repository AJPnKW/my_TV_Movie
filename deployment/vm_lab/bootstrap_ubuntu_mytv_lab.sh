#!/usr/bin/env bash
set -Eeuo pipefail

LOG_FILE="/var/log/mytv-lab-bootstrap.log"
APP_ROOT="/opt/mytv_movie"
ENV_EXAMPLE="${APP_ROOT}/.env.example"

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
  postgresql \
  postgresql-contrib \
  python3 \
  python3-pip \
  python3-venv

mkdir -p "${APP_ROOT}"
chmod 0755 "${APP_ROOT}"

if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  chown "${SUDO_USER}:${SUDO_USER}" "${APP_ROOT}"
fi

if [[ ! -e "${ENV_EXAMPLE}" ]]; then
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

POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=mytv_movie
POSTGRES_USER=mytv_movie
POSTGRES_PASSWORD=replace_with_local_secret

TRAKT_CLIENT_ID=replace_with_local_value
TRAKT_CLIENT_SECRET=replace_with_local_secret
ENVEOF
  chmod 0640 "${ENV_EXAMPLE}"
else
  echo "Keeping existing ${ENV_EXAMPLE}; bootstrap does not overwrite environment examples."
fi

systemctl enable --now postgresql
systemctl enable --now nginx

echo "Installed versions:"
git --version
curl --version | head -n 1
python3 --version
pip3 --version
psql --version
nginx -v
ffmpeg -version | head -n 1
ffprobe -version | head -n 1

echo "my_TV_Movie X1 lab bootstrap completed: $(date -Is)"
