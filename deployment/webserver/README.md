# Web Server Baseline

The baseline web server for the VM deployment path is Nginx.

## Decision

Use Nginx on both the X1 lab VM and later HP production VM.

## Why Nginx

- Serves the existing `web/`, `assets/`, and generated static runtime files efficiently.
- Provides a simple reverse proxy path for the later local API service without changing the static UI foundation.
- Has standard Ubuntu packages, service management, logging, and TLS integration.
- Keeps deployment concerns separate from the future application/API implementation.

## Baseline Ports

- `80/tcp`: HTTP static app entrypoint and later reverse-proxy baseline.
- `443/tcp`: reserved for HTTPS/TLS after lab validation.
- `8000/tcp`: reserved local API upstream, not exposed directly by this foundation.

## Current Scope

The lab bootstrap installs and starts Nginx only. It does not add a production virtual host, TLS certificate, API upstream, or app-specific Nginx site file. Those changes belong after the API/database owner defines the server runtime contract.
