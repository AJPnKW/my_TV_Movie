#!/usr/bin/env python3
# ==============================================================================
# scripts/trakt_test_tokens.py
# Purpose: Validate Trakt OAuth tokens locally (and auto-refresh if needed)
#
# Env vars expected (your naming):
#   API_TRAKT_ID            = Trakt Client ID
#   API_TRAKT_KEY           = Trakt Client Secret
#   API_TRAKT_ACCESS_TOKEN  = OAuth access token
#   API_TRAKT_REFRESH_TOKEN = OAuth refresh token
#   API_TRAKT_REDIRECT_URL  = redirect uri (not required for refresh, but echoed)
#
# Output:
#   - Calls GET https://api.trakt.tv/users/me
#   - If 401, refreshes token and retries once
# ==============================================================================

import json
import os
import sys
import urllib.request
import urllib.error


TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_TOKEN_URL = "https://trakt.tv/oauth/token"
TRAKT_API_VERSION = "2"


def blank(s: str | None) -> bool:
    return s is None or str(s).strip() == ""


def mask(s: str | None, keep: int = 6) -> str:
    if blank(s):
        return "<EMPTY>"
    s = str(s)
    if len(s) <= keep * 2:
        return "<SET>"
    return f"{s[:keep]}...{s[-keep:]}"


def http_json(url: str, headers: dict, method: str = "GET", body_obj=None, timeout: int = 30):
    data = None
    if body_obj is not None:
        data = json.dumps(body_obj).encode("utf-8")
        headers = dict(headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}


def trakt_headers(client_id: str, access_token: str | None = None) -> dict:
    h = {
        "trakt-api-version": TRAKT_API_VERSION,
        "trakt-api-key": client_id,
    }
    if access_token and not blank(access_token):
        h["Authorization"] = f"Bearer {access_token}"
    return h


def refresh_tokens(client_id: str, client_secret: str, refresh_token: str) -> dict:
    payload = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    return http_json(TRAKT_TOKEN_URL, headers={}, method="POST", body_obj=payload)


def main() -> int:
    client_id = os.getenv("API_TRAKT_ID")
    client_secret = os.getenv("API_TRAKT_KEY")
    redirect_url = os.getenv("API_TRAKT_REDIRECT_URL")
    access_token = os.getenv("API_TRAKT_ACCESS_TOKEN")
    refresh_token = os.getenv("API_TRAKT_REFRESH_TOKEN")

    print("\n=== TRAKT TOKEN TEST — PREFLIGHT ===")
    print(f"API_TRAKT_ID            = {client_id if not blank(client_id) else '<EMPTY>'}")
    print(f"API_TRAKT_KEY           = {'<SET>' if not blank(client_secret) else '<EMPTY>'}")
    print(f"API_TRAKT_REDIRECT_URL  = {redirect_url if not blank(redirect_url) else '<EMPTY>'}")
    print(f"API_TRAKT_ACCESS_TOKEN  = {mask(access_token)}")
    print(f"API_TRAKT_REFRESH_TOKEN = {mask(refresh_token)}")

    if blank(client_id):
        print("ERROR: Missing API_TRAKT_ID", file=sys.stderr)
        return 2
    if blank(access_token):
        print("ERROR: Missing API_TRAKT_ACCESS_TOKEN", file=sys.stderr)
        return 2

    me_url = f"{TRAKT_API_BASE}/users/me"

    # Attempt 1: use access token
    print("\n=== CALL 1: GET /users/me ===")
    try:
        me = http_json(me_url, trakt_headers(client_id, access_token))
        print("SUCCESS:")
        print(json.dumps({"username": me.get("username"), "name": me.get("name"), "private": me.get("private")}, indent=2))
        return 0

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(f"HTTP {e.code}")
        print(body)

        if e.code != 401:
            print("FAIL: Not an auth error (expected 401 if token expired).", file=sys.stderr)
            return 3

        # Attempt refresh if we have what we need
        if blank(client_secret) or blank(refresh_token):
            print("FAIL: 401 and missing API_TRAKT_KEY or API_TRAKT_REFRESH_TOKEN for refresh.", file=sys.stderr)
            return 4

        print("\n=== REFRESH: POST /oauth/token (grant_type=refresh_token) ===")
        try:
            tok = refresh_tokens(client_id, client_secret, refresh_token)  # returns new access/refresh
            new_access = tok.get("access_token")
            new_refresh = tok.get("refresh_token")

            print("REFRESH SUCCESS:")
            print(json.dumps({"access_token": mask(new_access), "refresh_token": mask(new_refresh)}, indent=2))

            print("\n=== CALL 2: GET /users/me (with refreshed access token) ===")
            me2 = http_json(me_url, trakt_headers(client_id, new_access))
            print("SUCCESS:")
            print(json.dumps({"username": me2.get("username"), "name": me2.get("name"), "private": me2.get("private")}, indent=2))

            print("\nIMPORTANT: Update your env + GitHub secrets with the NEW tokens just issued.")
            return 0

        except urllib.error.HTTPError as e2:
            body2 = e2.read().decode("utf-8", errors="replace") if e2.fp else ""
            print(f"HTTP {e2.code}")
            print(body2)
            return 5
        except Exception as ex2:
            print(str(ex2), file=sys.stderr)
            return 6

    except Exception as ex:
        print(str(ex), file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())
