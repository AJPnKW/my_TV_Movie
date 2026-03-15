"""
FILE: tools/inputs_editor/inputs_editor_server.py
VERSION: 1.0.4
UPDATED: 2026-03-14T00:00:00Z
CHANGE NOTES:
- Restore live inputs editor server path used by web/inputs_editor.html.
- Serve the inputs editor UI and supporting /web assets from port 8787.
- Preserve frontend save/config/TMDB API contract for local testing.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import tempfile
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
INPUTS_JSON = DATA_DIR / "inputs.json"
WEB_DIR = REPO_ROOT / "web"
UI_FILE = WEB_DIR / "inputs_editor.html"
CONFIG_JSON = WEB_DIR / "config.json"

TMDB_KEY_ENV = "API_TMDB_KEY"
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/"


def _now_utc_iso() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(handler: BaseHTTPRequestHandler, code: int, obj: dict):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _text(
    handler: BaseHTTPRequestHandler,
    code: int,
    text: str,
    ctype: str = "text/plain; charset=utf-8",
):
    data = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _read_inputs() -> dict:
    if not INPUTS_JSON.exists():
        return {
            "tv": [],
            "movies": [],
            "watchlist": [],
            "generated_local": "",
            "generated_utc": "",
        }
    return json.loads(INPUTS_JSON.read_text(encoding="utf-8"))


def _atomic_write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


def _tmdb_search(query: str) -> dict:
    key = os.environ.get(TMDB_KEY_ENV, "").strip()
    if not key:
        return {"ok": False, "error": f"Missing env var {TMDB_KEY_ENV} (TMDB search disabled)"}

    qs = {
        "api_key": key,
        "query": query,
        "include_adult": "false",
        "language": "en-US",
        "region": "CA",
    }
    query_string = "&".join(
        [f"{name}={quote(str(value))}" for name, value in qs.items() if value is not None]
    )
    url = f"{TMDB_BASE}/search/multi?{query_string}"

    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read().decode("utf-8", errors="replace")
    data = json.loads(raw)

    results = []
    for result in data.get("results", []):
        media_type = result.get("media_type")
        if media_type not in ("tv", "movie"):
            continue
        title = result.get("name") if media_type == "tv" else result.get("title")
        year = (result.get("first_air_date") or result.get("release_date") or "")[:4]
        results.append(
            {
                "type": media_type,
                "tmdb_id": result.get("id"),
                "title": title or "",
                "year": year,
                "poster_path": result.get("poster_path") or "",
            }
        )
    return {"ok": True, "results": results, "img_base": TMDB_IMG_BASE}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/web/inputs_editor.html"):
            if not UI_FILE.exists():
                _text(self, 404, "Missing: web/inputs_editor.html")
                return
            _text(self, 200, UI_FILE.read_text(encoding="utf-8", errors="replace"), "text/html; charset=utf-8")
            return

        if path == "/api/health":
            _json(self, 200, {"ok": True, "utc": _now_utc_iso(), "repo_root": str(REPO_ROOT)})
            return

        if path == "/api/inputs":
            _json(self, 200, {"ok": True, "inputs": _read_inputs()})
            return

        if path == "/api/config":
            if not CONFIG_JSON.exists():
                _json(self, 200, {"ok": True, "config": {}})
                return
            try:
                config = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
            except Exception:
                config = {}
            _json(self, 200, {"ok": True, "config": config})
            return

        if path == "/api/tmdb/search":
            query = (parse_qs(parsed.query).get("q") or [""])[0].strip()
            if not query:
                _json(self, 400, {"ok": False, "error": "Missing q"})
                return
            result = _tmdb_search(query)
            _json(self, 200 if result.get("ok") else 400, result)
            return

        if path.startswith("/web/"):
            file_path = (REPO_ROOT / path.lstrip("/")).resolve()
            if not file_path.exists() or not file_path.is_file():
                _text(self, 404, "Not found")
                return
            suffix = file_path.suffix.lower()
            if suffix in {".html", ".htm"}:
                _text(self, 200, file_path.read_text(encoding="utf-8", errors="replace"), "text/html; charset=utf-8")
                return
            if suffix == ".css":
                _text(self, 200, file_path.read_text(encoding="utf-8", errors="replace"), "text/css; charset=utf-8")
                return
            if suffix == ".js":
                _text(
                    self,
                    200,
                    file_path.read_text(encoding="utf-8", errors="replace"),
                    "application/javascript; charset=utf-8",
                )
                return
            if suffix == ".json":
                _text(self, 200, file_path.read_text(encoding="utf-8", errors="replace"), "application/json; charset=utf-8")
                return
            data = file_path.read_bytes()
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        _text(self, 404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/config":
            body = self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode(
                "utf-8", errors="replace"
            )
            try:
                obj = json.loads(body)
            except Exception as exc:
                _json(self, 400, {"ok": False, "error": f"Invalid JSON: {exc}"})
                return
            try:
                CONFIG_JSON.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            except Exception as exc:
                _json(self, 500, {"ok": False, "error": str(exc)})
                return
            _json(self, 200, {"ok": True})
            return

        if parsed.path != "/api/inputs":
            _json(self, 404, {"ok": False, "error": "Not found"})
            return

        body = self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode(
            "utf-8", errors="replace"
        )
        try:
            obj = json.loads(body)
        except Exception as exc:
            _json(self, 400, {"ok": False, "error": f"Invalid JSON: {exc}"})
            return

        if not isinstance(obj.get("tv", []), list) or not isinstance(obj.get("movies", []), list):
            _json(self, 400, {"ok": False, "error": "inputs must contain lists: tv, movies"})
            return

        obj["generated_utc"] = _now_utc_iso()
        _atomic_write(INPUTS_JSON, obj)
        _json(self, 200, {"ok": True, "saved": str(INPUTS_JSON), "utc": obj["generated_utc"]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    host = "127.0.0.1"
    server = HTTPServer((host, args.port), Handler)

    print("------------------------------------------------------------")
    print("my_TV_Movie • Inputs Editor Server")
    print(f"Repo:  {REPO_ROOT}")
    print(f"File:  {INPUTS_JSON}")
    print(f"URL:   http://{host}:{args.port}/web/inputs_editor.html")
    print(f"TMDB:  env {TMDB_KEY_ENV} {'present' if os.environ.get(TMDB_KEY_ENV) else 'missing'}")
    print("------------------------------------------------------------")
    server.serve_forever()


if __name__ == "__main__":
    main()
