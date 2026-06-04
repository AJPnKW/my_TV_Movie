# X1 Lab VM Foundation

## Objective

`mytv-lab-vm01` is the first local lab VM for moving `my_TV_Movie` from GitHub Pages/static-only hosting to a server-backed local VM app. The lab VM validates the operating system, deployment layout, web server baseline, PostgreSQL availability, and media tooling before any HP production promotion work begins.

This foundation installs and validates the live PostgreSQL runtime required by the server-mode API. It creates the local app role/database, installs psycopg in the app virtual environment, and fails validation unless the v1 schema plus a write/read/rollback transaction pass.

## VM Target

- VM name: `mytv-lab-vm01`
- Operating system: Ubuntu Server LTS, with Ubuntu Server 24.04 LTS as the pinned lab baseline until the project explicitly upgrades.
- CPU: 2 vCPU minimum, 4 vCPU preferred for media validation.
- RAM: 4 GB minimum, 8 GB preferred.
- Disk: 40 GB minimum, 80 GB preferred for logs, packages, repo checkout, and temporary media QA work.
- App root: `/opt/mytv_movie`

## Network

- Preferred mode: bridged network, so other local devices can reach the lab app by VM IP.
- Acceptable bootstrap mode: NAT with explicit port forwarding while the VM is being tested from the host only.
- The VM should receive a stable DHCP reservation or static LAN address before app/API testing begins.

## Ports

| Port | Purpose | Lab expectation |
| --- | --- | --- |
| `22/tcp` | SSH administration | Reachable from the host/admin LAN when SSH is enabled |
| `80/tcp` | Nginx HTTP baseline | Listening after bootstrap |
| `443/tcp` | Future HTTPS endpoint | Reserved for later TLS/reverse proxy work |
| `5432/tcp` | PostgreSQL | Local VM service; do not expose beyond the VM/admin network |
| `8000/tcp` | Local API service upstream | Reserved for the server-mode API; remains free until the service is installed |

## Bootstrap

Place the repo at the canonical app root, then run the Ubuntu-side bootstrap:

```bash
sudo install -d -m 0755 -o "$USER" -g "$USER" /opt/mytv_movie
git clone https://github.com/AJPnKW/my_TV_Movie.git /opt/mytv_movie
cd /opt/mytv_movie
sudo bash deployment/vm_lab/bootstrap_ubuntu_mytv_lab.sh
```

The script installs base packages, creates `/opt/mytv_movie`, writes `/opt/mytv_movie/.env.example`, creates the local `mytv_movie` OS/PostgreSQL roles and database, creates `/opt/mytv_movie/.venv`, installs psycopg, and tests local peer-authenticated database access. It does not write `.env` and does not contain real secrets.

For an existing checkout:

```bash
cd /opt/mytv_movie
git pull origin main
sudo bash deployment/vm_lab/bootstrap_ubuntu_mytv_lab.sh
```

## Validation

Run the VM validation script after bootstrap:

```bash
bash deployment/vm_lab/validate_mytv_lab.sh
```

Validation checks:

- Ubuntu Server LTS identity.
- Required commands: `git`, `curl`, `python3`, `pip3`, `ffmpeg`, `ffprobe`.
- PostgreSQL service state and `5432/tcp` listener.
- PostgreSQL `mytv_movie` app role and database.
- psycopg installed in `/opt/mytv_movie/.venv`.
- Live v1 schema apply, test insert, test read, rollback, and cleanup.
- Nginx service state and `80/tcp` listener.
- `/opt/mytv_movie` exists.
- Reserved API port `8000/tcp` is not already occupied.

## Promotion Gate

The lab VM is ready for the next owner only after the repo exists at `/opt/mytv_movie`, bootstrap completes, and live PostgreSQL validation passes. A scaffold-only or static-only result does not pass this gate.
