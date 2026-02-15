#!/usr/bin/env python3
# ==============================================================================
# [FILE]    scripts/trakt_http.py
# [PROJECT] my_TV_Movie
# [ROLE]    Shared Trakt HTTP helpers (headers, UA, safe logging)
# [VERSION] v1.0.0
# [UPDATED] 2026-02-02
# ==============================================================================
from __future__ import annotations

from typing import Dict, Optional


TRAKT_API_VERSION = "2"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"


def build_headers(client_id: str, access_token: Optional[str] = None, include_auth: bool = True) -> Dict[str, str]:
    headers = {
        "trakt-api-version": TRAKT_API_VERSION,
        "trakt-api-key": client_id,
        "User-Agent": USER_AGENT,
    }
    if include_auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def header_names(headers: Dict[str, str]) -> str:
    return ", ".join(sorted(headers.keys()))
