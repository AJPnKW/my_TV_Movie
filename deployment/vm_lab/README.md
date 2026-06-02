# X1 Lab VM Foundation

## Objective

`mytv-lab-vm01` is the first local lab VM for moving `my_TV_Movie` from GitHub Pages/static-only hosting to a server-backed local VM app. The lab VM validates the operating system, deployment layout, web server baseline, PostgreSQL availability, and media tooling before any HP production promotion work begins.

This foundation does not implement the API, database schema, or application write paths. It prepares the VM base those later layers will run on.

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
| `8000/tcp` | Future local API service | Reserved; no service is installed by this foundation |

## Bootstrap

Run the Ubuntu-side bootstrap script on the VM:

```bash
sudo bash deployment/vm_lab/bootstrap_ubuntu_mytv_lab.sh
```

The script installs base packages, creates `/opt/mytv_movie`, and writes `/opt/mytv_movie/.env.example`. It does not write `.env` and does not contain secrets.

## Validation

Run the VM validation script after bootstrap:

```bash
bash deployment/vm_lab/validate_mytv_lab.sh
```

Validation checks:

- Ubuntu Server LTS identity.
- Required commands: `git`, `curl`, `python3`, `pip3`, `ffmpeg`, `ffprobe`.
- PostgreSQL service state and `5432/tcp` listener.
- Nginx service state and `80/tcp` listener.
- `/opt/mytv_movie` exists.
- Reserved API port `8000/tcp` is not already occupied.

## Promotion Gate

The lab VM is ready for the next owner only after the bootstrap script completes, validation passes, and the repo can be cloned or copied into `/opt/mytv_movie` without introducing secrets.
