"""
FILE: tools/inputs_editor/inputs_editor_server.py
VERSION: 1.0.3
DATE: 2026-01-24

PURPOSE
- Local utility server to manage canonical scope file: data/inputs.json
- UI:  http://127.0.0.1:8787/web/inputs_editor.html
- API:
    GET  /api/health
    GET  /api/inputs
    POST /api/inputs
    GET  /api/tmdb/search?q=...

REQUIREMENTS
- Python 3.12+
- Optional TMDB search: API_TMDB_KEY env var (if missing, TMDB search disabled cleanly)

RUN
  python tools/inputs_editor/inputs_editor_server.py --port 8787
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
import urllib.request

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
INPUTS_JSON = DATA_DIR / "inputs.json"
WEB_DIR = REPO_ROOT / "web"
UI_FILE = WEB_DIR / "inputs_editor.html"

TMDB_KEY_ENV = "API_TMDB_KEY"
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/"


def _now_utc_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(handler: BaseHTTPRequestHandler, code: int, obj: dict):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _text(handler: BaseHTTPRequestHandler, code: int, text: str, ctype="text/plain; charset=utf-8"):
    data = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _read_inputs() -> dict:
    if not INPUTS_JSON.exists():
        return {"tv": [], "movies": [], "watchlist": [], "generated_local": "", "generated_utc": ""}
    return json.loads(INPUTS_JSON.read_text(encoding="utf-8"))


def _atomic_write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
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
    q = "&".join([f"{k}={quote(str(v))}" for k, v in qs.items() if v is not None])
    url = f"{TMDB_BASE}/search/multi?{q}"

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw)

    results = []
    for r in data.get("results", []):
        mt = r.get("media_type")
        if mt not in ("tv", "movie"):
            continue
        title = r.get("name") if mt == "tv" else r.get("title")
        tmdb_id = r.get("id")
        year = (r.get("first_air_date") or r.get("release_date") or "")[:4]
        results.append({
            "type": mt,
            "tmdb_id": tmdb_id,
            "title": title or "",
            "year": year,
            "poster_path": r.get("poster_path") or ""
        })
    return {"ok": True, "results": results, "img_base": TMDB_IMG_BASE}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        p = urlparse(self.path)
        path = p.path

        if path == "/" or path == "/web/inputs_editor.html":
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

        if path == "/api/tmdb/search":
            q = parse_qs(p.query)
            query = (q.get("q") or [""])[0].strip()
            if not query:
                _json(self, 400, {"ok": False, "error": "Missing q"})
                return
            res = _tmdb_search(query)
            _json(self, 200 if res.get("ok") else 400, res)
            return

        if path.startswith("/web/"):
            f = (REPO_ROOT / path.lstrip("/")).resolve()
            if not f.exists() or not f.is_file():
                _text(self, 404, "Not found")
                return
            suf = f.suffix.lower()
            if suf == ".css":
                _text(self, 200, f.read_text(encoding="utf-8", errors="replace"), "text/css; charset=utf-8")
                return
            if suf == ".js":
                _text(self, 200, f.read_text(encoding="utf-8", errors="replace"), "application/javascript; charset=utf-8")
                return
            data = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        _text(self, 404, "Not found")

    def do_POST(self):
        p = urlparse(self.path)
        if p.path != "/api/inputs":
            _json(self, 404, {"ok": False, "error": "Not found"})
            return

        n = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(n).decode("utf-8", errors="replace")
        try:
            obj = json.loads(body)
        except Exception as e:
            _json(self, 400, {"ok": False, "error": f"Invalid JSON: {e}"})
            return

        tv = obj.get("tv", [])
        mv = obj.get("movies", [])
        if not isinstance(tv, list) or not isinstance(mv, list):
            _json(self, 400, {"ok": False, "error": "inputs must contain lists: tv, movies"})
            return

        obj["generated_utc"] = _now_utc_iso()
        _atomic_write(INPUTS_JSON, obj)
        _json(self, 200, {"ok": True, "saved": str(INPUTS_JSON), "utc": obj["generated_utc"]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    host = "127.0.0.1"
    httpd = HTTPServer((host, args.port), Handler)

    print("------------------------------------------------------------")
    print("my_TV_Movie • Inputs Editor Server")
    print(f"Repo:  {REPO_ROOT}")
    print(f"File:  {INPUTS_JSON}")
    print(f"URL:   http://{host}:{args.port}/web/inputs_editor.html")
    print(f"TMDB:  env {TMDB_KEY_ENV} {'present' if os.environ.get(TMDB_KEY_ENV) else 'missing'}")
    print("------------------------------------------------------------")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
