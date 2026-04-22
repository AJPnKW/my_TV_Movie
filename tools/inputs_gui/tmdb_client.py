# ==============================================================================
# [FILE]    tmdb_client.py
# [PROJECT] my_TV_Movie
# [ROLE]    Minimal TMDB client for GUI search + details
# [VERSION] v0.1.0
# [UPDATED] 2026-02-24
# ==============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

TMDB_BASE = "https://api.themoviedb.org/3"


@dataclass
class TmdbSearchResult:
    kind: str  # "tv" | "movie"
    tmdb_id: int
    title: str
    year: Optional[str] = None

    def preview_text(self) -> str:
        y = self.year or "—"
        return f"{self.title}\n\nType: {self.kind}\nYear: {y}\nTMDB ID: {self.tmdb_id}"


class TmdbClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = (api_key or "").strip()

    def search(self, kind: str, query: str, limit: int = 30) -> List[TmdbSearchResult]:
        kind = "tv" if kind == "tv" else "movie"
        url = f"{TMDB_BASE}/search/{kind}?api_key={urllib.parse.quote(self.api_key)}&query={urllib.parse.quote(query)}&include_adult=false"
        data = self._get_json(url)
        out: List[TmdbSearchResult] = []
        for x in (data.get("results") or [])[:limit]:
            tid = int(x.get("id"))
            if kind == "tv":
                title = str(x.get("name") or x.get("original_name") or "")
                year = (x.get("first_air_date") or "")[:4] or None
            else:
                title = str(x.get("title") or x.get("original_title") or "")
                year = (x.get("release_date") or "")[:4] or None
            out.append(TmdbSearchResult(kind=kind, tmdb_id=tid, title=title, year=year))
        return out

    def tv_details(self, tmdb_id: int) -> Dict[str, Any]:
        url = f"{TMDB_BASE}/tv/{int(tmdb_id)}?api_key={urllib.parse.quote(self.api_key)}"
        return self._get_json(url)

    def _get_json(self, url: str) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)
