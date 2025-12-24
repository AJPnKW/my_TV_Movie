#!/usr/bin/env python3
# ==============================================================================
# scripts/trakt_get_tokens_from_pin.py
# Purpose: Exchange Trakt PIN for access_token + refresh_token
# Env:     API_TRAKT_ID, API_TRAKT_KEY, API_TRAKT_REDIRECT_URL
# Version: v1.0.0 (2025-12-24)
# ==============================================================================

import json
import os
import sys
import urllib.request
import urllib.error


TOKEN_URL = "https://trakt.tv/oauth/token"


def is_blank(s: str | None) -> bool:
    return s is None or str(s).strip() == ""


def main() -> int:
    client_id = os.getenv("API_TRAKT_ID")
    client_secret = os.getenv("API_TRAKT_KEY")
    redirect_url = os.getenv("API_TRAKT_REDIRECT_URL")

    # ---- PIN (edit this line) ----
    pin = "04a012b1"

    print("\n=== TRAKT OAUTH PIN EXCHANGE — PREFLIGHT ===")
    print("# --- REQUIRED ENV VARS ---")
    print(f"API_TRAKT_ID            = {client_id if not is_blank(client_id) else '<EMPTY>'}")
    print(f"API_TRAKT_KEY           = {'<SET>' if not is_blank(client_secret) else '<EMPTY>'}")
    print(f"API_TRAKT_REDIRECT_URL  = {redirect_url if not is_blank(redirect_url) else '<EMPTY>'}")
    print("# --- PIN ---")
    print(f"PIN                     = {pin if not is_blank(pin) and pin != 'PASTE_PIN_HERE' else '<EMPTY>'}")

    if is_blank(client_id):
        raise SystemExit("Missing env var: API_TRAKT_ID")
    if is_blank(client_secret):
        raise SystemExit("Missing env var: API_TRAKT_KEY")
    if is_blank(redirect_url):
        raise SystemExit("Missing env var: API_TRAKT_REDIRECT_URL")
    if is_blank(pin) or pin == "PASTE_PIN_HERE":
        raise SystemExit("Set pin to the Trakt PIN value.")

    payload = {
        "code": pin,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_url,
        "grant_type": "authorization_code",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    print("\n=== EXECUTING TOKEN EXCHANGE ===")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            obj = json.loads(body)

        print("\n=== SUCCESS ===")
        print(json.dumps(obj, indent=2, sort_keys=True))

        access_token = obj.get("access_token")
        refresh_token = obj.get("refresh_token")

        print("\nCOPY THESE VALUES:")
        print(f"API_TRAKT_ACCESS_TOKEN  = {access_token}")
        print(f"API_TRAKT_REFRESH_TOKEN = {refresh_token}")

        return 0

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print("\n=== ERROR DURING TOKEN EXCHANGE ===")
        print(f"HTTP {e.code}")
        print(body)
        return 2
    except Exception as e:
        print("\n=== ERROR DURING TOKEN EXCHANGE ===")
        print(str(e))
        return 3


if __name__ == "__main__":
    sys.exit(main())
