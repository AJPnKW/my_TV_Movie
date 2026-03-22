#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/trakt_device_auth.py
# [PROJECT] my_TV_Movie
# [ROLE]    Trakt device-flow OAuth to obtain access + refresh tokens
# [VERSION] v1.0.0
# [UPDATED] 2026-02-01
#
# Usage:
#   python scripts/trakt_device_auth.py
#
# Requires env:
#   API_TRAKT_ID
#   API_TRAKT_SECRET   (preferred) or API_TRAKT_KEY
# Optional:
#   API_TRAKT_REDIRECT_URL (unused in device flow; canonical redirect secret name)
#
# Output:
#   data/trakt.json
# ==============================================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import time
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from trakt_http import USER_AGENT  # noqa: E402
DATA_DIR = REPO_ROOT / "data"
TOK_OUT = DATA_DIR / "trakt.json"

TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_DEVICE_CODE = f"{TRAKT_API_BASE}/oauth/device/code"
TRAKT_DEVICE_TOKEN = f"{TRAKT_API_BASE}/oauth/device/token"


def _utc() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_required(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return v.strip()


def _env_optional(*names: str) -> str:
    for name in names:
        v = os.getenv(name)
        if v and v.strip():
            return v.strip()
    return ""


def _warn_redirect_secret_drift() -> None:
    canonical = os.getenv("API_TRAKT_REDIRECT_URL")
    typo = os.getenv("API_TRAKT__REDIRECT_URL")
    if typo and not canonical:
        print("WARNING: API_TRAKT__REDIRECT_URL is deprecated. Rename it to API_TRAKT_REDIRECT_URL.", file=sys.stderr)
    elif typo and canonical and typo.strip() != canonical.strip():
        print("WARNING: Conflicting Trakt redirect env vars detected. Use only API_TRAKT_REDIRECT_URL.", file=sys.stderr)


def http_json(url: str, headers: dict, method: str = "GET", body_obj=None, timeout: int = 45) -> Dict[str, Any]:
    data = None
    if body_obj is not None:
        data = json.dumps(body_obj).encode("utf-8")
        headers = dict(headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        headers.setdefault("User-Agent", USER_AGENT)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw.strip() else {}

def _post_json(url: str, body: dict, headers: dict | None = None) -> Dict[str, Any]:
    hdrs = headers or {}
    try:
        return http_json(url, headers=hdrs, method="POST", body_obj=body)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) else ""
        try:
            return json.loads(raw) if raw.strip() else {"error": f"HTTP {e.code}"}
        except Exception:
            return {"error": f"HTTP {e.code}", "error_description": raw[:300]}


def main() -> int:
    _warn_redirect_secret_drift()
    client_id = _env_required("API_TRAKT_ID")
    client_secret = _env_optional("API_TRAKT_SECRET", "API_TRAKT_KEY")

    if not client_secret:
        raise RuntimeError("Missing API_TRAKT_SECRET (or API_TRAKT_KEY).")

    # Step 1: request device code
    scope = "public private watchlist history collection lists"
    code_resp = _post_json(
        TRAKT_DEVICE_CODE,
        {"client_id": client_id, "scope": scope},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    if not code_resp or "device_code" not in code_resp:
        raise RuntimeError(f"Failed to get device code: {code_resp}")

    device_code = code_resp.get("device_code")
    user_code = code_resp.get("user_code")
    verify_url = code_resp.get("verification_url") or code_resp.get("verification_url_complete")
    expires_in = int(code_resp.get("expires_in") or 600)
    interval = int(code_resp.get("interval") or 5)

    print("\n=== Trakt Device Authorization ===")
    print(f"Go to: {verify_url}")
    print(f"Enter code: {user_code}")
    print("Waiting for approval...\n")

    # Step 2: poll for token
    deadline = time.time() + expires_in
    while time.time() < deadline:
        token_resp = _post_json(
            TRAKT_DEVICE_TOKEN,
            {
                "code": device_code,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

        if "access_token" in token_resp:
            payload = {
                "generated_utc": _utc(),
                "access_token": token_resp.get("access_token"),
                "refresh_token": token_resp.get("refresh_token"),
                "expires_in": token_resp.get("expires_in"),
                "token_type": token_resp.get("token_type"),
                "scope": token_resp.get("scope"),
            }
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            TOK_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print("✅ Tokens saved to:")
            print(f" - {TOK_OUT}")
            print("\nYou can now run pipeline scripts that pull Trakt user data.")
            return 0

        err = token_resp.get("error")
        if err == "authorization_pending":
            time.sleep(interval)
            continue
        if err == "slow_down":
            interval = interval + 5
            time.sleep(interval)
            continue
        if err in ("access_denied", "expired_token"):
            raise RuntimeError(f"Authorization failed: {err}")

        # Unknown error; wait briefly then retry
        time.sleep(interval)

    raise RuntimeError("Device authorization timed out.")


if __name__ == "__main__":
    raise SystemExit(main())
