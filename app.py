#!/usr/bin/env python
# =============================================================================
# File: app.py
# Project: my_TV_Movie
# Version: v1.0.0 (2025-11-09)
#
# Purpose:
#   Minimal local development server for testing the static site.
#   - Serves files from the repository root.
#   - Lets you open /web/index.html in a browser.
#
# Usage:
#   python app.py
#   Then open: http://localhost:8811/web/index.html
#
# Notes:
#   This is NOT used by GitHub Pages in production.
# =============================================================================

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8811

# Serve from repo root (directory containing this file)
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

class Handler(http.server.SimpleHTTPRequestHandler):
    # Default behavior serves from current working directory (ROOT)
    # which includes:
    #   /web
    #   /data
    #   /image
    #   /scripts
    #
    # No override needed unless you want custom routing.
    pass

def main() -> None:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving my_TV_Movie at http://localhost:{PORT}/web/index.html")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")

if __name__ == "__main__":
    main()
