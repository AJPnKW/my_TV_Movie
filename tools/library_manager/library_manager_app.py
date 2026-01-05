# -*- coding: utf-8 -*-
r"""
File: library_manager_app.py
Project: my_TV_Movie
Tool: Library Manager (Local Web UI)
Version: v0.2.6 (2026-01-04)
Path: tools/library_manager/library_manager_app.py

Fixes:
- Do NOT exit if TMDB creds are missing. UI still starts; TMDB features show clear warnings.
- Do NOT exit if inputs folder missing. It will be created.

Env (optional but recommended for full functionality):
  API_TMDB_KEY
  API_TMDB_TOKEN
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, jsonify, redirect, render_template_string, request, url_for


APP_NAME = "my_TV_Movie — Library Manager"
APP_VERSION = "v0.2.6"

FILE_TV = "tv_list.txt"
FILE_MOVIES = "movies_list.txt"
FILE_WATCHLIST = "watchlist.txt"
FILE_LIVETV = "livetv_list.txt"
SUPPORTED_FILES = [FILE_TV, FILE_MOVIES, FILE_WATCHLIST, FILE_LIVETV]

UA = f"my_TV_Movie-LibraryManager/{APP_VERSION}"


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8", errors="replace")


def is_commented(line: str) -> bool:
    return line.lstrip().startswith("#")


def uncomment_line(line: str) -> str:
    m = re.match(r"^(\s*)#\s?(.*)$", line)
    if not m:
        return line
    return f"{m.group(1)}{m.group(2)}"


def comment_line(line: str) -> str:
    if is_commented(line):
        return line
    m = re.match(r"^(\s*)(.*)$", line)
    if not m:
        return "# " + line
    return f"{m.group(1)}# {m.group(2)}"


def split_pipe_line(line: str) -> List[str]:
    return [p.strip() for p in line.split("|")]


def parse_int(s: str) -> Optional[int]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


SEASON_SPEC_RE = re.compile(r"^\*$|^\d+(\s*,\s*\d+)*$")


def validate_season_spec(spec: str) -> Tuple[bool, str]:
    spec = (spec or "").strip()
    if spec == "":
        return True, "ok"
    if not SEASON_SPEC_RE.match(spec):
        return False, "Invalid season spec. Use '*' or comma-separated numbers (e.g., 1,2,3)."
    return True, "ok"


@dataclass
class LibraryEntry:
    file_name: str
    line_index: int
    raw: str
    active: bool
    name: str
    tmdb_id: Optional[int] = None
    season_spec: str = ""
    tvmaze_id: Optional[int] = None
    parse_ok: bool = True
    parse_error: str = ""


def parse_entry_from_line(fn: str, idx: int, line: str) -> LibraryEntry:
    raw = line.rstrip("\n")
    stripped = raw.strip()

    if stripped == "" or stripped.startswith("# File:") or stripped.startswith("# Project:") or stripped.startswith("# Version:") or stripped.startswith("# format:"):
        return LibraryEntry(fn, idx, raw, not is_commented(raw), "", None, "", None, True, "")

    active = not is_commented(raw)
    content = uncomment_line(raw).strip()
    parts = split_pipe_line(content)

    if fn == FILE_MOVIES:
        if len(parts) < 2:
            return LibraryEntry(fn, idx, raw, active, "", None, "", None, False, "Expected: name|tmdb_movie_id")
        name = normalize_spaces(parts[0])
        tmdb_id = parse_int(parts[1])
        if not name:
            return LibraryEntry(fn, idx, raw, active, "", tmdb_id, "", None, False, "Missing movie name")
        if tmdb_id is None:
            return LibraryEntry(fn, idx, raw, active, name, None, "", None, False, "Invalid TMDB movie ID")
        return LibraryEntry(fn, idx, raw, active, name, tmdb_id, "", None, True, "")

    if fn in (FILE_TV, FILE_WATCHLIST):
        if len(parts) < 2:
            exp = "name|tmdb_show_id|season_spec|tvmaze_id" if fn == FILE_TV else "title|tmdb_id|seasons"
            return LibraryEntry(fn, idx, raw, active, "", None, "", None, False, f"Expected: {exp}")
        name = normalize_spaces(parts[0])
        tmdb_id = parse_int(parts[1])
        season_spec = normalize_spaces(parts[2]) if len(parts) >= 3 else ""
        tvmaze_id = parse_int(parts[3]) if (fn == FILE_TV and len(parts) >= 4) else None
        if not name:
            return LibraryEntry(fn, idx, raw, active, "", tmdb_id, season_spec, tvmaze_id, False, "Missing title")
        if tmdb_id is None:
            return LibraryEntry(fn, idx, raw, active, name, None, season_spec, tvmaze_id, False, "Invalid TMDB ID")
        ok, msg = validate_season_spec(season_spec) if season_spec else (True, "ok")
        if not ok:
            return LibraryEntry(fn, idx, raw, active, name, tmdb_id, season_spec, tvmaze_id, False, msg)
        return LibraryEntry(fn, idx, raw, active, name, tmdb_id, season_spec, tvmaze_id, True, "")

    if fn == FILE_LIVETV:
        name = normalize_spaces(parts[0]) if parts else ""
        return LibraryEntry(fn, idx, raw, active, name, None, "", None, True, "")

    return LibraryEntry(fn, idx, raw, active, "", None, "", None, True, "")


def load_entries(file_path: Path) -> List[LibraryEntry]:
    if not file_path.exists():
        return []
    lines = safe_read_text(file_path).splitlines()
    return [parse_entry_from_line(file_path.name, i, ln) for i, ln in enumerate(lines)]


def rewrite_file(file_path: Path, entries: List[LibraryEntry]) -> None:
    safe_write_text(file_path, "\n".join([e.raw for e in entries]).rstrip() + "\n")


def append_entry(file_path: Path, line: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        hdr = [
            f"# File: {file_path.name}",
            "# Project: my_TV_Movie",
            f"# Version: v1.0.0 ({dt.datetime.now().strftime('%Y-%m-%d')})",
        ]
        if file_path.name == FILE_MOVIES:
            hdr.append("# format: name|tmdb_movie_id")
        elif file_path.name == FILE_TV:
            hdr.append("# format: name|tmdb_show_id|season_spec|tvmaze_id")
        elif file_path.name == FILE_WATCHLIST:
            hdr.append("# format: title|tmdb_id|seasons")
        safe_write_text(file_path, "\n".join(hdr).rstrip() + "\n")
    with file_path.open("a", encoding="utf-8", errors="replace") as f:
        f.write((line.rstrip("\n") + "\n"))


def read_tmdb_creds() -> Tuple[str, str]:
    return os.getenv("API_TMDB_KEY", "") or "", os.getenv("API_TMDB_TOKEN", "") or ""


def build_requests_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


class TMDBClient:
    def __init__(self, session: requests.Session, api_key: str, bearer_token: str) -> None:
        self.s = session
        self.api_key = api_key or ""
        self.bearer = bearer_token or ""
        if self.bearer:
            self.s.headers.update({"Authorization": f"Bearer {self.bearer}"})

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        params = params or {}
        if self.api_key:
            params.setdefault("api_key", self.api_key)
        return self.s.get(url, params=params, timeout=20)

    def search(self, media_type: str, query: str) -> Tuple[bool, Any]:
        url = f"https://api.themoviedb.org/3/search/{media_type}"
        r = self._get(url, params={"query": query, "include_adult": "false", "language": "en-US"})
        if r.status_code != 200:
            return False, {"error": f"TMDB search failed: HTTP {r.status_code}", "body": r.text[:1000]}
        return True, r.json()

    def validate_tv(self, tmdb_id: int) -> Tuple[bool, str]:
        r = self._get(f"https://api.themoviedb.org/3/tv/{tmdb_id}", params={"language": "en-US"})
        return (r.status_code == 200, f"HTTP {r.status_code}")

    def validate_movie(self, tmdb_id: int) -> Tuple[bool, str]:
        r = self._get(f"https://api.themoviedb.org/3/movie/{tmdb_id}", params={"language": "en-US"})
        return (r.status_code == 200, f"HTTP {r.status_code}")


@dataclass
class AppState:
    repo_root: Path
    inputs_dir: Path
    out_dir: Path
    tmdb_enabled: bool
    tmdb: Optional[TMDBClient]


BASE_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{{title}}</title>
<style>
  body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;background:#0b0f14;color:#e7eef8}
  header{position:sticky;top:0;background:rgba(11,15,20,.85);backdrop-filter:blur(10px);border-bottom:1px solid rgba(255,255,255,.08)}
  .wrap{max-width:1260px;margin:0 auto;padding:14px 18px}
  .grid{display:grid;grid-template-columns:420px 1fr;gap:14px;align-items:start}
  @media(max-width:1100px){.grid{grid-template-columns:1fr}}
  .card{background:#101722;border:1px solid rgba(255,255,255,.08);border-radius:14px;overflow:hidden}
  .card h2{margin:0;padding:12px 14px;font-size:14px;border-bottom:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between}
  .body{padding:12px 14px}
  label{display:block;font-size:12px;color:#98a6b7;margin-bottom:6px}
  input,select{width:100%;padding:10px;border-radius:12px;border:1px solid rgba(255,255,255,.10);background:rgba(0,0,0,.25);color:#e7eef8}
  .btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:#1b2a3f;color:#e7eef8;cursor:pointer;text-decoration:none;font-weight:600;font-size:13px}
  .btn:hover{background:#22334c}
  .btn.primary{background:rgba(90,167,255,.18);border-color:rgba(90,167,255,.35)}
  .btn.ok{background:rgba(91,255,182,.13);border-color:rgba(91,255,182,.30)}
  .btn.danger{background:rgba(255,107,107,.14);border-color:rgba(255,107,107,.30)}
  .muted{color:#98a6b7}
  .k{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;color:#cfe5ff;font-size:12px}
  .actions{display:flex;gap:8px;flex-wrap:wrap}
  .sep{height:1px;background:rgba(255,255,255,.08);margin:12px 0}
  table{width:100%;border-collapse:collapse}
  th,td{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.08);vertical-align:top}
  th{text-align:left;font-size:12px;color:#98a6b7}
  .pill{padding:3px 8px;border-radius:999px;font-size:12px;border:1px solid rgba(255,255,255,.10);color:#98a6b7}
  .pill.ok{color:#d3ffe9;border-color:rgba(91,255,182,.35);background:rgba(91,255,182,.10)}
  .pill.bad{color:#ffd2d2;border-color:rgba(255,107,107,.35);background:rgba(255,107,107,.10)}
  .pill.warn{color:#ffe8c2;border-color:rgba(255,204,102,.35);background:rgba(255,204,102,.10)}
  .notice{padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.10);background:rgba(0,0,0,.22)}
  .notice.bad{border-color:rgba(255,107,107,.35);background:rgba(255,107,107,.08)}
  .notice.warn{border-color:rgba(255,204,102,.35);background:rgba(255,204,102,.08)}
</style></head>
<body>
<header><div class="wrap">
  <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
    <div style="font-weight:800">{{title}}</div>
    <span class="pill">{{now}}</span>
    <span class="pill">Repo: <span class="k">{{repo_root}}</span></span>
    <span class="pill">Inputs: <span class="k">{{inputs_dir}}</span></span>
    <span class="pill">Out: <span class="k">{{out_dir}}</span></span>
    {% if not tmdb_enabled %}
      <span class="pill warn">TMDB disabled — set API_TMDB_KEY or API_TMDB_TOKEN</span>
    {% else %}
      <span class="pill ok">TMDB enabled</span>
    {% endif %}
  </div>
</div></header>

<div class="wrap" style="padding-top:14px">
  <div class="grid">
    <div class="card">
      <h2><span>Search TMDB → Add</span><span class="pill">{{ 'enabled' if tmdb_enabled else 'disabled' }}</span></h2>
      <div class="body">
        {% if not tmdb_enabled %}
          <div class="notice warn">TMDB features are disabled. Add/search/ID-validation will show errors until you set env vars.</div>
          <div class="sep"></div>
        {% endif %}

        <form method="post" action="{{ url_for('search') }}">
          <label>Media type</label>
          <select name="media_type">
            <option value="tv" {{ 'selected' if media_type=='tv' else '' }}>TV</option>
            <option value="movie" {{ 'selected' if media_type=='movie' else '' }}>Movie</option>
          </select>

          <div style="margin-top:10px">
            <label>Target list</label>
            <select name="target_file">
              <option value="tv_list.txt" {{ 'selected' if target_file=='tv_list.txt' else '' }}>tv_list.txt</option>
              <option value="movies_list.txt" {{ 'selected' if target_file=='movies_list.txt' else '' }}>movies_list.txt</option>
              <option value="watchlist.txt" {{ 'selected' if target_file=='watchlist.txt' else '' }}>watchlist.txt</option>
            </select>
          </div>

          <div style="margin-top:10px">
            <label>Search text</label>
            <input name="q" value="{{q}}" placeholder="Type a title..." />
          </div>

          <div style="margin-top:10px">
            <label>Seasons (TV/watchlist)</label>
            <input name="season_spec" value="{{season_spec}}" placeholder="* or 1,2,3" />
          </div>

          <div style="margin-top:10px">
            <label>TVMaze ID (optional)</label>
            <input name="tvmaze_id" value="{{tvmaze_id}}" placeholder="optional integer" />
          </div>

          <div class="actions" style="margin-top:12px">
            <button class="btn primary" type="submit">Search</button>
            <a class="btn" href="{{ url_for('index') }}">Refresh</a>
            <a class="btn ok" href="{{ url_for('export_json') }}">Export JSON</a>
            <a class="btn" href="{{ url_for('validate') }}">Validate</a>
          </div>
        </form>

        {% if search_error %}
          <div class="sep"></div>
          <div class="notice bad">{{search_error}}</div>
        {% endif %}

        {% if results %}
          <div class="sep"></div>
          <table>
            <thead><tr><th style="width:70px">Add</th><th>Title</th><th style="width:90px">Year</th><th style="width:90px">TMDB</th></tr></thead>
            <tbody>
              {% for r in results %}
              <tr>
                <td>
                  <form method="post" action="{{ url_for('add') }}">
                    <input type="hidden" name="target_file" value="{{target_file}}" />
                    <input type="hidden" name="media_type" value="{{media_type}}" />
                    <input type="hidden" name="name" value="{{r.title}}" />
                    <input type="hidden" name="tmdb_id" value="{{r.id}}" />
                    <input type="hidden" name="season_spec" value="{{season_spec}}" />
                    <input type="hidden" name="tvmaze_id" value="{{tvmaze_id}}" />
                    <button class="btn ok" type="submit">Add</button>
                  </form>
                </td>
                <td><div style="font-weight:800">{{r.title}}</div><div class="muted" style="font-size:12px">{{r.overview}}</div></td>
                <td class="muted" style="font-size:12px">{{r.year}}</td>
                <td class="k">{{r.id}}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        {% endif %}
      </div>
    </div>

    <div class="card">
      <h2><span>Inventory</span><span class="pill">Filter</span></h2>
      <div class="body">
        <form method="get" action="{{ url_for('index') }}">
          <label>File</label>
          <select name="file">
            <option value="all" {{ 'selected' if filter_file=='all' else '' }}>All</option>
            <option value="tv_list.txt" {{ 'selected' if filter_file=='tv_list.txt' else '' }}>tv_list.txt</option>
            <option value="movies_list.txt" {{ 'selected' if filter_file=='movies_list.txt' else '' }}>movies_list.txt</option>
            <option value="watchlist.txt" {{ 'selected' if filter_file=='watchlist.txt' else '' }}>watchlist.txt</option>
            <option value="livetv_list.txt" {{ 'selected' if filter_file=='livetv_list.txt' else '' }}>livetv_list.txt</option>
          </select>

          <div style="margin-top:10px">
            <label>Search</label>
            <input name="q" value="{{filter_q}}" placeholder="contains..." />
          </div>

          <div class="actions" style="margin-top:12px">
            <button class="btn primary" type="submit">Apply</button>
            <a class="btn" href="{{ url_for('index') }}">Clear</a>
            <a class="btn" href="{{ url_for('validate') }}">Validate</a>
            <a class="btn ok" href="{{ url_for('export_json') }}">Export JSON</a>
          </div>
        </form>

        <div class="sep"></div>

        <table>
          <thead>
            <tr>
              <th style="width:120px">Status</th><th>Title</th><th style="width:120px">List</th>
              <th style="width:90px">TMDB</th><th style="width:110px">Seasons</th><th style="width:120px">TVMaze</th>
              <th style="width:280px;text-align:right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {% for e in entries %}
              {% if e.name %}
              <tr>
                <td>
                  {% if e.parse_ok %}<span class="pill ok">ok</span>{% else %}<span class="pill bad">bad</span>{% endif %}
                  {% if e.active %}<span class="pill ok" style="margin-left:6px">active</span>{% else %}<span class="pill warn" style="margin-left:6px">inactive</span>{% endif %}
                </td>
                <td>
                  <div style="font-weight:800">{{e.name}}</div>
                  {% if not e.parse_ok %}<div class="muted" style="font-size:12px;color:#ffd2d2;margin-top:6px">{{e.parse_error}}</div>{% endif %}
                </td>
                <td class="muted" style="font-size:12px">{{e.file_name}}</td>
                <td class="k">{{e.tmdb_id or ''}}</td>
                <td class="k">{{e.season_spec or ''}}</td>
                <td class="k">{{e.tvmaze_id or ''}}</td>
                <td style="text-align:right">
                  <div class="actions" style="justify-content:flex-end">
                    <form method="post" action="{{ url_for('toggle') }}">
                      <input type="hidden" name="file_name" value="{{e.file_name}}" />
                      <input type="hidden" name="line_index" value="{{e.line_index}}" />
                      <button class="btn" type="submit">{{ 'Deactivate' if e.active else 'Activate' }}</button>
                    </form>
                    {% if e.file_name in ['tv_list.txt','watchlist.txt'] %}
                    <form method="post" action="{{ url_for('set_seasons') }}">
                      <input type="hidden" name="file_name" value="{{e.file_name}}" />
                      <input type="hidden" name="line_index" value="{{e.line_index}}" />
                      <input type="hidden" name="season_spec" value="*" />
                      <button class="btn" type="submit">All seasons</button>
                    </form>
                    {% endif %}
                    <form method="post" action="{{ url_for('remove') }}" onsubmit="return confirm('Remove this line from file?');">
                      <input type="hidden" name="file_name" value="{{e.file_name}}" />
                      <input type="hidden" name="line_index" value="{{e.line_index}}" />
                      <button class="btn danger" type="submit">Remove</button>
                    </form>
                  </div>
                </td>
              </tr>
              {% endif %}
            {% endfor %}
          </tbody>
        </table>

        <div class="sep"></div>

        <div class="notice">
          <div style="font-weight:800">Edit seasons</div>
          <div class="muted" style="font-size:12px;margin-top:6px">Enter the file + line # (0-based) shown in the table.</div>
          <form method="post" action="{{ url_for('set_seasons') }}" style="margin-top:10px">
            <label>File</label>
            <select name="file_name">
              <option value="tv_list.txt">tv_list.txt</option>
              <option value="watchlist.txt">watchlist.txt</option>
            </select>
            <div style="margin-top:10px">
              <label>Line # (0-based)</label>
              <input name="line_index" placeholder="e.g., 12" />
            </div>
            <div style="margin-top:10px">
              <label>Season spec</label>
              <input name="season_spec" placeholder="* or 1,2,3" />
            </div>
            <div class="actions" style="margin-top:12px">
              <button class="btn primary" type="submit">Update seasons</button>
            </div>
          </form>
        </div>

      </div>
    </div>

  </div>
</div>
</body></html>
"""


def create_app(state: AppState) -> Flask:
    app = Flask(__name__)

    def read_all_entries() -> List[LibraryEntry]:
        out: List[LibraryEntry] = []
        for fn in SUPPORTED_FILES:
            fp = state.inputs_dir / fn
            if fp.exists():
                out.extend(load_entries(fp))
        return out

    def filter_entries(entries: List[LibraryEntry], file_filter: str, q: str) -> List[LibraryEntry]:
        qn = normalize_spaces(q).lower()
        out: List[LibraryEntry] = []
        for e in entries:
            if not e.name:
                continue
            if file_filter != "all" and e.file_name != file_filter:
                continue
            if qn and qn not in (e.name or "").lower():
                continue
            out.append(e)
        return out

    def export_snapshot() -> Tuple[Path, Path]:
        entries = read_all_entries()
        items: List[Dict[str, Any]] = []
        issues: List[Dict[str, Any]] = []
        for e in entries:
            if not e.name:
                continue
            items.append(
                {
                    "file": e.file_name,
                    "active": e.active,
                    "name": e.name,
                    "tmdb_id": e.tmdb_id,
                    "season_spec": e.season_spec,
                    "tvmaze_id": e.tvmaze_id,
                    "parse_ok": e.parse_ok,
                    "parse_error": e.parse_error,
                    "line_index": e.line_index,
                }
            )
            if not e.parse_ok:
                issues.append({"file": e.file_name, "line_index": e.line_index, "raw": e.raw, "error": e.parse_error})

        lib_path = state.out_dir / "library_inputs.json"
        rep_path = state.out_dir / "validation_report.json"
        json_dump(lib_path, {"generated_at": now_stamp(), "items": items})
        json_dump(rep_path, {"generated_at": now_stamp(), "issues": issues})
        return lib_path, rep_path

    def update_line(file_name: str, line_index: int, transform) -> None:
        fp = state.inputs_dir / file_name
        entries = load_entries(fp)
        e = entries[line_index]
        new_raw = transform(e.raw)
        entries[line_index] = parse_entry_from_line(file_name, line_index, new_raw)
        rewrite_file(fp, entries)

    def remove_line(file_name: str, line_index: int) -> None:
        fp = state.inputs_dir / file_name
        lines = safe_read_text(fp).splitlines()
        del lines[line_index]
        safe_write_text(fp, "\n".join(lines).rstrip() + "\n")

    @app.get("/")
    def index() -> str:
        file_filter = request.args.get("file", "all")
        q = request.args.get("q", "")
        entries = filter_entries(read_all_entries(), file_filter, q)
        return render_template_string(
            BASE_HTML,
            title=APP_NAME,
            now=now_stamp(),
            repo_root=str(state.repo_root),
            inputs_dir=str(state.inputs_dir),
            out_dir=str(state.out_dir),
            tmdb_enabled=state.tmdb_enabled,
            media_type="tv",
            target_file="tv_list.txt",
            q="",
            season_spec="*",
            tvmaze_id="",
            results=None,
            search_error="",
            filter_file=file_filter,
            filter_q=q,
            entries=entries,
        )

    @app.post("/search")
    def search() -> str:
        media_type = request.form.get("media_type", "tv").strip()
        target_file = request.form.get("target_file", "tv_list.txt").strip()
        q = request.form.get("q", "").strip()
        season_spec = request.form.get("season_spec", "*").strip()
        tvmaze_id = request.form.get("tvmaze_id", "").strip()

        results = []
        search_error = ""

        if not state.tmdb_enabled or not state.tmdb:
            search_error = "TMDB disabled (missing API_TMDB_KEY or API_TMDB_TOKEN)."
        else:
            if media_type == "tv" and target_file == "movies_list.txt":
                search_error = "Target file is movies_list.txt but media type is TV."
            elif media_type == "movie" and target_file != "movies_list.txt":
                search_error = "Media type is Movie but target file is not movies_list.txt."
            else:
                ok, msg = validate_season_spec(season_spec) if media_type == "tv" else (True, "ok")
                if not ok:
                    search_error = msg
                else:
                    ok, data = state.tmdb.search(media_type, q)
                    if not ok:
                        search_error = data.get("error", "Search failed")
                    else:
                        raw = data.get("results", [])[:12]
                        for r in raw:
                            title = r.get("name") if media_type == "tv" else r.get("title")
                            title = title or ""
                            d = (r.get("first_air_date") if media_type == "tv" else r.get("release_date")) or ""
                            year = d.split("-")[0] if d else ""
                            overview = (r.get("overview") or "").strip()
                            if len(overview) > 210:
                                overview = overview[:210].rstrip() + "…"
                            results.append(
                                {
                                    "id": r.get("id"),
                                    "title": html.escape(title),
                                    "year": html.escape(year),
                                    "overview": html.escape(overview),
                                }
                            )

        entries = filter_entries(read_all_entries(), request.args.get("file", "all"), request.args.get("q", ""))
        return render_template_string(
            BASE_HTML,
            title=APP_NAME,
            now=now_stamp(),
            repo_root=str(state.repo_root),
            inputs_dir=str(state.inputs_dir),
            out_dir=str(state.out_dir),
            tmdb_enabled=state.tmdb_enabled,
            media_type=media_type,
            target_file=target_file,
            q=q,
            season_spec=season_spec or "*",
            tvmaze_id=tvmaze_id,
            results=results,
            search_error=search_error,
            filter_file=request.args.get("file", "all"),
            filter_q=request.args.get("q", ""),
            entries=entries,
        )

    @app.post("/add")
    def add() -> Any:
        target_file = request.form.get("target_file", "").strip()
        media_type = request.form.get("media_type", "").strip()
        name = request.form.get("name", "").strip()
        tmdb_id = parse_int(request.form.get("tmdb_id", ""))
        season_spec = request.form.get("season_spec", "*").strip()
        tvmaze_id = request.form.get("tvmaze_id", "").strip()

        if not name or tmdb_id is None:
            return redirect(url_for("index", _n=int(time.time())))

        if target_file not in (FILE_TV, FILE_MOVIES, FILE_WATCHLIST):
            return redirect(url_for("index", _n=int(time.time())))

        if media_type == "tv":
            ok, _ = validate_season_spec(season_spec)
            if not ok:
                return redirect(url_for("index", _n=int(time.time())))

        tvmaze_int = parse_int(tvmaze_id) if tvmaze_id.strip() else None

        fp = state.inputs_dir / target_file
        if target_file == FILE_MOVIES:
            line = f"{name}|{tmdb_id}"
        elif target_file == FILE_TV:
            line = f"{name}|{tmdb_id}|{season_spec or '*'}|{tvmaze_int or ''}".rstrip("|")
        else:
            line = f"{name}|{tmdb_id}|{season_spec or '*'}"

        append_entry(fp, line)
        return redirect(url_for("index", _n=int(time.time())))

    @app.post("/toggle")
    def toggle() -> Any:
        file_name = request.form.get("file_name", "").strip()
        line_index = parse_int(request.form.get("line_index", ""))
        if file_name not in SUPPORTED_FILES or line_index is None:
            return redirect(url_for("index", _n=int(time.time())))

        def _t(line: str) -> str:
            return comment_line(line) if not is_commented(line) else uncomment_line(line)

        update_line(file_name, line_index, _t)
        return redirect(url_for("index", _n=int(time.time())))

    @app.post("/set_seasons")
    def set_seasons() -> Any:
        file_name = request.form.get("file_name", "").strip()
        line_index = parse_int(request.form.get("line_index", ""))
        season_spec = request.form.get("season_spec", "").strip()
        if file_name not in (FILE_TV, FILE_WATCHLIST) or line_index is None:
            return redirect(url_for("index", _n=int(time.time())))

        ok, _ = validate_season_spec(season_spec)
        if not ok:
            return redirect(url_for("index", _n=int(time.time())))

        def _set(line: str) -> str:
            was_comment = is_commented(line)
            content = uncomment_line(line).strip()
            parts = split_pipe_line(content)
            while len(parts) < 3:
                parts.append("")
            parts[2] = season_spec
            new_line = "|".join(parts).rstrip("|")
            return comment_line(new_line) if was_comment else new_line

        update_line(file_name, line_index, _set)
        return redirect(url_for("index", _n=int(time.time())))

    @app.post("/remove")
    def remove() -> Any:
        file_name = request.form.get("file_name", "").strip()
        line_index = parse_int(request.form.get("line_index", ""))
        if file_name not in SUPPORTED_FILES or line_index is None:
            return redirect(url_for("index", _n=int(time.time())))
        remove_line(file_name, line_index)
        return redirect(url_for("index", _n=int(time.time())))

    @app.get("/validate")
    def validate() -> Any:
        _, report_path = export_snapshot()
        return jsonify(json.loads(safe_read_text(report_path)))

    @app.get("/export_json")
    def export_json_route() -> Any:
        inputs_path, report_path = export_snapshot()
        return jsonify({"generated_at": now_stamp(), "library_inputs": str(inputs_path), "validation_report": str(report_path)})

    return app


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5177)
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    inputs_dir = repo_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (repo_root / "tools" / "library_manager" / "out")
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key, bearer = read_tmdb_creds()
    tmdb_enabled = bool(api_key or bearer)
    tmdb = TMDBClient(build_requests_session(), api_key=api_key, bearer_token=bearer) if tmdb_enabled else None

    state = AppState(repo_root=repo_root, inputs_dir=inputs_dir, out_dir=out_dir, tmdb_enabled=tmdb_enabled, tmdb=tmdb)
    app = create_app(state)

    print(f"{APP_NAME} {APP_VERSION} running at http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
