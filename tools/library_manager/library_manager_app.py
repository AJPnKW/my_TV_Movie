# >>> FILE: tools/library_manager/library_manager_app.py
# PATCH: fix invalid escape sequence warning by avoiding backslash escapes in docstring
# Version: v0.2.3 (2026-01-03)

# -*- coding: utf-8 -*-
"""
File: library_manager_app.py
Project: my_TV_Movie
Tool: Library Manager (Local Web UI)
Version: v0.2.3 (2026-01-03)
Path: tools/library_manager/library_manager_app.py

Purpose:
  Local web UI to manage inputs/*.txt:
    - tv_list.txt
    - movies_list.txt
    - watchlist.txt
    - livetv_list.txt (optional)

Run (recommended):
  powershell -ExecutionPolicy Bypass -File tools\library_manager\run_library_manager.ps1

Direct run (PowerShell) from tools/library_manager:
  & "..\..\..\.venv\Scripts\python.exe" ".\library_manager_app.py" --repo-root "..\..\.." --port 5177

Env:
  API_TMDB_KEY   (v3 api key)
  API_TMDB_TOKEN (v4 read token / bearer)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import os
import re
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, Response, jsonify, redirect, render_template_string, request, url_for

APP_NAME = "Library Manager"
SCHEMA_INPUTS = "inputs.v0.2"
SCHEMA_VALIDATION = "validation.v0.2"


def now_local_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text_utf8(path: Path, text: str) -> None:
    safe_mkdir(path.parent)
    path.write_text(text, encoding="utf-8", errors="replace", newline="\n")


def json_dump(path: Path, obj: Any) -> None:
    safe_mkdir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", errors="replace")


SEASON_SPEC_RE = re.compile(r"^\s*(\*|\d+\s*(?:-\s*\d+)?(?:\s*,\s*\d+\s*(?:-\s*\d+)?)*)\s*$")


def normalize_season_spec(spec: str) -> str:
    s = (spec or "").strip()
    if s == "":
        return "*"
    if s == "*":
        return "*"
    parts: List[str] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            parts.append(f"{int(a)}-{int(b)}")
        else:
            parts.append(str(int(part)))
    return ",".join(parts) if parts else "*"


def parse_season_spec(spec: str) -> Tuple[bool, List[int]]:
    s = (spec or "").strip()
    if s == "" or s == "*":
        return True, []
    if not SEASON_SPEC_RE.match(s):
        return False, []
    seasons: List[int] = []
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = [x.strip() for x in chunk.split("-", 1)]
            try:
                ia, ib = int(a), int(b)
            except Exception:
                return False, []
            if ia < 1 or ib < 1:
                return False, []
            if ib < ia:
                ia, ib = ib, ia
            seasons.extend(list(range(ia, ib + 1)))
        else:
            try:
                seasons.append(int(chunk))
            except Exception:
                return False, []
    seasons = sorted(set(seasons))
    return True, seasons


def safe_int(x: str) -> Optional[int]:
    try:
        x = (x or "").strip()
        if x == "":
            return None
        return int(x)
    except Exception:
        return None


def strip_comment_prefix(line: str) -> Tuple[bool, str]:
    s = line.lstrip()
    if s.startswith("#"):
        idx = line.find("#")
        return True, (line[idx + 1 :]).strip()
    return False, line.strip()


def with_comment(active: bool, raw: str) -> str:
    raw = raw.strip()
    return raw if active else f"# {raw}"


class TMDBClient:
    def __init__(self, session: requests.Session, api_key: Optional[str], bearer_token: Optional[str]) -> None:
        self.s = session
        self.api_key = api_key
        self.bearer = bearer_token
        self.base = "https://api.themoviedb.org/3"
        self.cache_tv: Dict[int, Dict[str, Any]] = {}
        self.cache_movie: Dict[int, Dict[str, Any]] = {}
        self.cache_search: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.lock = threading.Lock()

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.bearer:
            h["Authorization"] = f"Bearer {self.bearer}"
        return h

    def _params(self) -> Dict[str, str]:
        p: Dict[str, str] = {}
        if self.api_key and not self.bearer:
            p["api_key"] = self.api_key
        return p

    def search(self, kind: str, query: str) -> List[Dict[str, Any]]:
        kind = kind.lower().strip()
        if kind not in ("tv", "movie"):
            return []
        q = (query or "").strip()
        if not q:
            return []
        key = (kind, q.lower())
        with self.lock:
            if key in self.cache_search:
                return self.cache_search[key]
        url = f"{self.base}/search/{kind}"
        params = {"query": q, "include_adult": "false", "language": "en-US", **self._params()}
        r = self.s.get(url, params=params, headers=self._headers(), timeout=20)
        if r.status_code != 200:
            return []
        items = r.json().get("results", []) or []
        out: List[Dict[str, Any]] = []
        for it in items[:25]:
            out.append(
                {
                    "id": it.get("id"),
                    "name": it.get("name") or it.get("title") or "",
                    "original_name": it.get("original_name") or it.get("original_title") or "",
                    "first_air_date": it.get("first_air_date") or "",
                    "release_date": it.get("release_date") or "",
                    "overview": (it.get("overview") or "")[:220],
                    "vote_average": it.get("vote_average"),
                    "poster_path": it.get("poster_path") or "",
                }
            )
        with self.lock:
            self.cache_search[key] = out
        return out

    def get_tv(self, tmdb_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        with self.lock:
            if tmdb_id in self.cache_tv:
                return self.cache_tv[tmdb_id], None, 200
        url = f"{self.base}/tv/{tmdb_id}"
        params = {"language": "en-US", **self._params()}
        r = self.s.get(url, params=params, headers=self._headers(), timeout=20)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}", r.status_code
        data = r.json()
        with self.lock:
            self.cache_tv[tmdb_id] = data
        return data, None, 200

    def get_movie(self, tmdb_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
        with self.lock:
            if tmdb_id in self.cache_movie:
                return self.cache_movie[tmdb_id], None, 200
        url = f"{self.base}/movie/{tmdb_id}"
        params = {"language": "en-US", **self._params()}
        r = self.s.get(url, params=params, headers=self._headers(), timeout=20)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}", r.status_code
        data = r.json()
        with self.lock:
            self.cache_movie[tmdb_id] = data
        return data, None, 200


@dataclass
class Record:
    kind: str
    active: bool
    name: str
    tmdb_id: Optional[int] = None
    season_spec: Optional[str] = None
    tvmaze_id: Optional[int] = None
    source_file: str = ""
    line_no: int = 0
    raw_line: str = ""


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    source_file: str
    line_no: int
    raw_line: str


def split_header_and_body(text: str) -> Tuple[str, List[str]]:
    lines = text.splitlines()
    header_lines: List[str] = []
    body_lines: List[str] = []
    in_header = True
    for ln in lines:
        if in_header and (ln.strip() == "" or ln.lstrip().startswith("#")):
            header_lines.append(ln)
        else:
            in_header = False
            body_lines.append(ln)
    header = "\n".join(header_lines).rstrip("\n")
    return header, body_lines


def parse_file(kind: str, path: Path) -> Tuple[List[Record], List[Issue], str]:
    issues: List[Issue] = []
    text = read_text_utf8(path)
    header, body_lines = split_header_and_body(text)

    records: List[Record] = []
    for idx, raw in enumerate(body_lines, start=1):
        line_no = idx + (len(header.splitlines()) if header else 0)
        raw_line = raw.rstrip("\n")
        if raw_line.strip() == "":
            continue
        was_comment, content = strip_comment_prefix(raw_line)
        active = not was_comment
        if content.strip() == "":
            continue

        parts = [p.strip() for p in content.split("|")]

        if kind == "movie":
            if len(parts) < 2:
                issues.append(Issue("error", "FORMAT", "Expected 'name|tmdb_movie_id'.", path.name, line_no, raw_line))
                continue
            name = parts[0]
            tmdb_id = safe_int(parts[1])
            if not name:
                issues.append(Issue("error", "NAME_MISSING", "Name is missing.", path.name, line_no, raw_line))
            if tmdb_id is None:
                issues.append(
                    Issue("error", "TMDB_ID_MISSING_OR_INVALID", "TMDB id is missing or not an integer.", path.name, line_no, raw_line)
                )
            records.append(
                Record(kind="movie", active=active, name=name, tmdb_id=tmdb_id, source_file=path.name, line_no=line_no, raw_line=raw_line)
            )
        else:
            name = parts[0] if len(parts) >= 1 else ""
            tmdb_id = safe_int(parts[1]) if len(parts) >= 2 else None
            season_spec = parts[2].strip() if len(parts) >= 3 else ""
            tvmaze_id = safe_int(parts[3]) if len(parts) >= 4 else None

            if not name:
                issues.append(Issue("error", "NAME_MISSING", "Name is missing.", path.name, line_no, raw_line))
            if tmdb_id is None:
                issues.append(
                    Issue("error", "TMDB_ID_MISSING_OR_INVALID", "TMDB id is missing or not an integer.", path.name, line_no, raw_line)
                )

            if season_spec != "":
                ok, _ = parse_season_spec(season_spec)
                if not ok:
                    issues.append(
                        Issue("error", "SEASON_SPEC_INVALID", "Season spec must be '*' or '1,2,3' or '1-3,5'.", path.name, line_no, raw_line)
                    )

            records.append(
                Record(
                    kind=kind,
                    active=active,
                    name=name,
                    tmdb_id=tmdb_id,
                    season_spec=(season_spec if season_spec != "" else None),
                    tvmaze_id=tvmaze_id,
                    source_file=path.name,
                    line_no=line_no,
                    raw_line=raw_line,
                )
            )

    return records, issues, header


def serialize_records(records: List[Record]) -> List[Dict[str, Any]]:
    return [dataclasses.asdict(r) for r in records]


def format_line(kind: str, r: Record) -> str:
    name = (r.name or "").strip()
    if kind == "movie":
        tmdb = "" if r.tmdb_id is None else str(r.tmdb_id)
        raw = f"{name}|{tmdb}"
        return with_comment(r.active, raw)

    tmdb = "" if r.tmdb_id is None else str(r.tmdb_id)
    season = ""
    if r.season_spec is not None:
        season = normalize_season_spec(r.season_spec)
    tvmaze = "" if r.tvmaze_id is None else str(r.tvmaze_id)

    raw = f"{name}|{tmdb}|{season}"
    if r.tvmaze_id is not None:
        raw = f"{raw}|{tvmaze}"
    return with_comment(r.active, raw)


def write_file(path: Path, header: str, kind: str, records: List[Record]) -> None:
    body = "\n".join(format_line(kind, r) for r in records).rstrip("\n")
    text = header.rstrip("\n")
    if text:
        text += "\n"
    if body:
        text += body + "\n"
    write_text_utf8(path, text)


class AppState:
    def __init__(self, repo_root: Path, out_dir: Path, tmdb: TMDBClient) -> None:
        self.repo_root = repo_root
        self.inputs_dir = repo_root / "inputs"
        self.out_dir = out_dir
        self.tmdb = tmdb

        self.headers: Dict[str, str] = {}
        self.records: Dict[str, List[Record]] = {"tv": [], "movie": [], "watchlist": [], "livetv": []}
        self.issues_parse: List[Issue] = []
        self.issues_validate: List[Issue] = []

        self.load()

    def load(self) -> None:
        self.issues_parse = []
        self.issues_validate = []
        self.headers = {}
        self.records = {"tv": [], "movie": [], "watchlist": [], "livetv": []}

        mapping = {
            "tv": self.inputs_dir / "tv_list.txt",
            "movie": self.inputs_dir / "movies_list.txt",
            "watchlist": self.inputs_dir / "watchlist.txt",
            "livetv": self.inputs_dir / "livetv_list.txt",
        }
        for kind, path in mapping.items():
            if not path.exists():
                if kind == "livetv":
                    header = (
                        "# File: livetv_list.txt\n"
                        "# Project: my_TV_Movie\n"
                        f"# Version: auto-created ({now_local_iso()})\n"
                        "# format: name|tmdb_id|season_spec\n"
                    ).rstrip("\n")
                    self.headers[kind] = header
                    self.records[kind] = []
                    write_text_utf8(path, header + "\n")
                    continue
                self.issues_parse.append(Issue("error", "FILE_MISSING", f"Missing required file: {path}", path.name, 0, ""))
                continue

            recs, issues, header = parse_file(kind, path)
            self.headers[kind] = header
            self.records[kind] = recs
            self.issues_parse.extend(issues)

        self.export_json()

    def save(self) -> None:
        mapping = {
            "tv": self.inputs_dir / "tv_list.txt",
            "movie": self.inputs_dir / "movies_list.txt",
            "watchlist": self.inputs_dir / "watchlist.txt",
            "livetv": self.inputs_dir / "livetv_list.txt",
        }
        for kind, path in mapping.items():
            write_file(path, self.headers.get(kind, ""), kind, self.records.get(kind, []))
        self.export_json()

    def export_json(self) -> None:
        safe_mkdir(self.out_dir)
        out_inputs = self.out_dir / "library_inputs.json"
        out_validation = self.out_dir / "validation_report.json"

        payload = {
            "schema_version": SCHEMA_INPUTS,
            "generated_at": now_local_iso(),
            "records": serialize_records(self.all_records()),
            "by_kind": {k: len(v) for k, v in self.records.items()},
        }
        json_dump(out_inputs, payload)

        all_issues = self.issues_parse + self.issues_validate
        v_payload = {
            "schema_version": SCHEMA_VALIDATION,
            "generated_at": now_local_iso(),
            "counts": {
                "records_total": sum(len(v) for v in self.records.values()),
                "issues_total": len(all_issues),
                "issues_error": sum(1 for i in all_issues if i.severity == "error"),
                "issues_warning": sum(1 for i in all_issues if i.severity == "warning"),
            },
            "issues": [dataclasses.asdict(i) for i in all_issues],
        }
        json_dump(out_validation, v_payload)

        gen_dir = self.inputs_dir / "_generated"
        safe_mkdir(gen_dir)
        json_dump(gen_dir / "library_inputs.json", payload)
        json_dump(gen_dir / "validation_report.json", v_payload)

    def all_records(self) -> List[Record]:
        out: List[Record] = []
        for k in ("tv", "movie", "watchlist", "livetv"):
            out.extend(self.records.get(k, []))
        return out

    def validate(self) -> None:
        issues: List[Issue] = []

        for kind in ("tv", "watchlist", "livetv"):
            for r in self.records.get(kind, []):
                if r.tmdb_id is None:
                    continue
                tv, err, _ = self.tmdb.get_tv(r.tmdb_id)
                if tv is None:
                    issues.append(Issue("error", "TMDB_TV_NOT_FOUND", f"TMDB TV id not found ({err}).", r.source_file, r.line_no, r.raw_line))
                    continue
                seasons_total = int(tv.get("number_of_seasons") or 0)
                if r.season_spec and r.season_spec.strip() != "*" and seasons_total > 0:
                    ok, seasons = parse_season_spec(r.season_spec)
                    if ok:
                        bad = [s for s in seasons if s < 1 or s > seasons_total]
                        if bad:
                            issues.append(
                                Issue("error", "SEASON_OUT_OF_RANGE", f"Season(s) out of range (max={seasons_total}): {bad}", r.source_file, r.line_no, r.raw_line)
                            )

        for r in self.records.get("movie", []):
            if r.tmdb_id is None:
                continue
            mv, err, _ = self.tmdb.get_movie(r.tmdb_id)
            if mv is None:
                issues.append(Issue("error", "TMDB_MOVIE_NOT_FOUND", f"TMDB Movie id not found ({err}).", r.source_file, r.line_no, r.raw_line))

        self.issues_validate = issues
        self.export_json()


BASE_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{{ app_name }}</title>
  <style>
    :root{
      --bg:#0b0f14; --panel:#101826; --panel2:#0f1724; --text:#e7eef8; --muted:#9fb0c4;
      --line:#223147; --good:#40c4aa; --warn:#f7c948; --bad:#ff5c5c; --btn:#1a2a44; --btn2:#223a5f;
      --chip:#17243a;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    }
    body{ margin:0; font-family:var(--sans); background:var(--bg); color:var(--text); }
    .wrap{ max-width: 1320px; margin:0 auto; padding: 16px; }
    .topbar{ display:flex; gap:12px; align-items:center; justify-content:space-between; padding:12px 14px; background:var(--panel); border:1px solid var(--line); border-radius:12px; }
    .brand{ display:flex; flex-direction:column; gap:2px; }
    .brand h1{ margin:0; font-size:16px; letter-spacing:0.2px; }
    .brand .sub{ font-size:12px; color:var(--muted); }
    .actions{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:flex-end; }
    button,.btn{ background:var(--btn); color:var(--text); border:1px solid var(--line); border-radius:10px; padding:9px 12px; font-weight:600; cursor:pointer; }
    button:hover,.btn:hover{ background:var(--btn2); }
    button:disabled{ opacity:0.55; cursor:not-allowed; }
    .grid{ display:grid; grid-template-columns: 420px 1fr; gap: 14px; margin-top:14px; }
    .card{ background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:12px; }
    .card h2{ margin:0 0 8px 0; font-size:14px; color:var(--text); }
    .row{ display:flex; gap:8px; align-items:center; }
    .row + .row{ margin-top:8px; }
    label{ font-size:12px; color:var(--muted); }
    input, select{
      width:100%; padding:9px 10px; border-radius:10px; border:1px solid var(--line);
      background:#0c1422; color:var(--text);
    }
    input::placeholder{ color:#738aa3; }
    .tabs{ display:flex; gap:8px; flex-wrap:wrap; }
    .tab{ padding:9px 12px; border-radius:10px; border:1px solid var(--line); background:var(--chip); color:var(--text); text-decoration:none; font-weight:700; font-size:13px; }
    .tab.active{ background:#243a60; }
    .meta{ display:flex; gap:10px; flex-wrap:wrap; color:var(--muted); font-size:12px; }
    .pill{ padding:5px 8px; border-radius:999px; border:1px solid var(--line); background:var(--chip); }
    .pill.good{ border-color: rgba(64,196,170,.5); }
    .pill.warn{ border-color: rgba(247,201,72,.55); }
    .pill.bad{ border-color: rgba(255,92,92,.55); }

    table{ width:100%; border-collapse:collapse; }
    th,td{ border-bottom:1px solid var(--line); padding:8px 8px; font-size:13px; vertical-align:top; }
    th{ text-align:left; color:var(--muted); font-weight:800; font-size:12px; }
    td small{ color:var(--muted); }
    .mono{ font-family:var(--mono); }
    .right{ text-align:right; }
    .center{ text-align:center; }
    .muted{ color:var(--muted); }
    .tiny{ font-size:11px; }
    .split{ display:flex; gap:8px; }
    .split > *{ flex:1; }
    .list{ max-height: 360px; overflow:auto; border:1px solid var(--line); border-radius:12px; }
    .list table th{ position:sticky; top:0; background: #0f1b2d; }
    .toast{ margin-top:10px; padding:10px 12px; border-radius:12px; border:1px solid var(--line); background:#0c1526; color:var(--text); display:none; }
    .toast.good{ border-color: rgba(64,196,170,.55); }
    .toast.bad{ border-color: rgba(255,92,92,.55); }
    .issues{ max-height: 240px; overflow:auto; border:1px solid var(--line); border-radius:12px; }
    .issue{ padding:8px 10px; border-bottom:1px solid var(--line); }
    .issue:last-child{ border-bottom:none; }
    .sev{ font-weight:900; font-size:11px; padding:3px 8px; border-radius:999px; border:1px solid var(--line); display:inline-block; }
    .sev.error{ border-color: rgba(255,92,92,.55); }
    .sev.warning{ border-color: rgba(247,201,72,.55); }
    .kbd{ font-family:var(--mono); font-size:12px; color:var(--muted); }
    @media (max-width: 1100px){ .grid{ grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <h1>{{ app_name }}</h1>
        <div class="sub">Repo: <span class="mono">{{ repo_root }}</span> · Active file: <span class="mono">{{ active_file }}</span></div>
      </div>
      <div class="actions">
        <a class="tab {% if active_tab=='tv' %}active{% endif %}" href="/?tab=tv">TV</a>
        <a class="tab {% if active_tab=='movie' %}active{% endif %}" href="/?tab=movie">Movies</a>
        <a class="tab {% if active_tab=='watchlist' %}active{% endif %}" href="/?tab=watchlist">Watchlist</a>
        <a class="tab {% if active_tab=='livetv' %}active{% endif %}" href="/?tab=livetv">LiveTV</a>
        <button id="btnReload" title="Reload from disk">Reload</button>
        <button id="btnValidate" title="Validate TMDB IDs + season ranges">Validate</button>
        <button id="btnSave" title="Write changes to inputs/*.txt">Save</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>TMDB Lookup → Add to {{ active_tab }}</h2>

        <div class="row">
          <div style="flex:1">
            <label>Search</label>
            <input id="q" placeholder="Type a show or movie title…"/>
          </div>
        </div>

        <div class="row split">
          <div>
            <label>Search type</label>
            <select id="kind">
              <option value="tv">TV</option>
              <option value="movie">Movie</option>
            </select>
          </div>
          <div>
            <label>Target list</label>
            <select id="target">
              <option value="tv">tv_list</option>
              <option value="movie">movies_list</option>
              <option value="watchlist">watchlist</option>
              <option value="livetv">livetv_list</option>
            </select>
          </div>
        </div>

        <div class="row split">
          <div>
            <label>Season spec (TV/Watchlist/LiveTV only)</label>
            <input id="season" placeholder="* or 1 or 1-3,5"/>
          </div>
          <div class="row" style="align-items:flex-end">
            <button id="btnSearch" style="width:100%">Search</button>
          </div>
        </div>

        <div class="row">
          <div class="meta">
            <span class="pill good">Out: <span class="mono">{{ out_inputs }}</span></span>
            <span class="pill warn">Report: <span class="mono">{{ out_validation }}</span></span>
          </div>
        </div>

        <div class="row">
          <div class="list" style="width:100%">
            <table>
              <thead>
                <tr>
                  <th style="width:70px">TMDB</th>
                  <th>Title</th>
                  <th style="width:88px">Rating</th>
                  <th style="width:110px">Year</th>
                  <th class="right" style="width:92px">Action</th>
                </tr>
              </thead>
              <tbody id="results">
                <tr><td colspan="5" class="muted">Search results will appear here.</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div id="toast" class="toast"></div>
      </div>

      <div class="card">
        <div class="row" style="justify-content:space-between">
          <h2 style="margin:0">Inventory: {{ active_tab }}</h2>
          <div class="meta">
            <span class="pill">Records: <span class="mono">{{ counts.records_total }}</span></span>
            <span class="pill {% if counts.issues_total==0 %}good{% else %}bad{% endif %}">
              Issues: <span class="mono">{{ counts.issues_total }}</span>
            </span>
          </div>
        </div>

        <div class="row split">
          <div>
            <label>Filter</label>
            <input id="filter" placeholder="Type to filter rows…"/>
          </div>
          <div>
            <label>Show</label>
            <select id="showMode">
              <option value="all">All</option>
              <option value="active">Active only</option>
              <option value="inactive">Inactive only</option>
            </select>
          </div>
        </div>

        <div class="row">
          <div class="list" style="width:100%">
            <table id="invTable">
              <thead>
                <tr>
                  <th class="center" style="width:80px">Active</th>
                  <th>Title</th>
                  <th style="width:90px">TMDB</th>
                  <th style="width:140px">Seasons</th>
                  <th class="right" style="width:90px">Remove</th>
                </tr>
              </thead>
              <tbody id="invBody">
                {% for r in rows %}
                <tr data-idx="{{ loop.index0 }}">
                  <td class="center">
                    <input type="checkbox" class="chkActive" {% if r.active %}checked{% endif %}/>
                  </td>
                  <td>
                    <div>{{ r.name }}</div>
                    <div class="tiny muted mono">{{ r.source_file }}{% if r.line_no %}:{{ r.line_no }}{% endif %}</div>
                  </td>
                  <td class="mono">{{ r.tmdb_id if r.tmdb_id is not none else "" }}</td>
                  <td>
                    {% if active_tab == 'movie' %}
                      <span class="muted tiny">n/a</span>
                    {% else %}
                      <input class="seasonEdit" value="{{ r.season_spec if r.season_spec else '*' }}" />
                    {% endif %}
                  </td>
                  <td class="right">
                    <button class="btnRemove">Remove</button>
                  </td>
                </tr>
                {% endfor %}
                {% if rows|length == 0 %}
                <tr><td colspan="5" class="muted">No rows in this list.</td></tr>
                {% endif %}
              </tbody>
            </table>
          </div>
        </div>

        <div class="row">
          <h2 style="margin:0">Issues</h2>
        </div>
        <div class="issues" id="issues">
          {% if issues|length == 0 %}
            <div class="issue muted">No issues.</div>
          {% else %}
            {% for i in issues %}
              <div class="issue">
                <span class="sev {{ i.severity }}">{{ i.severity|upper }}</span>
                <span class="mono">{{ i.code }}</span>
                <div>{{ i.message }}</div>
                <div class="tiny muted mono">{{ i.source_file }}{% if i.line_no %}:{{ i.line_no }}{% endif %}</div>
              </div>
            {% endfor %}
          {% endif %}
        </div>

        <div class="row">
          <div class="muted tiny">
            Tips: toggle Active to comment/uncomment; seasons accepts <span class="kbd">*</span>, <span class="kbd">1</span>, <span class="kbd">1-3,5</span>.
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
  const activeTab = "{{ active_tab }}";

  function toast(msg, ok=true){
    const el = document.getElementById("toast");
    el.className = "toast " + (ok ? "good" : "bad");
    el.textContent = msg;
    el.style.display = "block";
    setTimeout(()=>{ el.style.display="none"; }, 4200);
  }

  async function postJSON(url, body){
    const r = await fetch(url, {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(body || {})
    });
    const j = await r.json().catch(()=> ({}));
    if(!r.ok){
      throw new Error(j.error || ("HTTP " + r.status));
    }
    return j;
  }

  function rowMatches(tr, text, mode){
    const idx = tr.getAttribute("data-idx");
    if(idx === null) return true;
    const active = tr.querySelector(".chkActive")?.checked ?? true;
    if(mode === "active" && !active) return false;
    if(mode === "inactive" && active) return false;
    if(!text) return true;
    const hay = tr.innerText.toLowerCase();
    return hay.includes(text.toLowerCase());
  }

  function applyFilter(){
    const text = document.getElementById("filter").value.trim();
    const mode = document.getElementById("showMode").value;
    document.querySelectorAll("#invBody tr").forEach(tr=>{
      tr.style.display = rowMatches(tr, text, mode) ? "" : "none";
    });
  }

  document.getElementById("filter").addEventListener("input", applyFilter);
  document.getElementById("showMode").addEventListener("change", applyFilter);

  document.getElementById("target").value = activeTab;

  document.getElementById("btnReload").addEventListener("click", ()=>{
    window.location = "/reload?tab=" + encodeURIComponent(activeTab);
  });

  document.getElementById("btnSave").addEventListener("click", async ()=>{
    try{
      await postJSON("/api/save", {});
      toast("Saved to inputs/*.txt");
      setTimeout(()=>window.location.reload(), 650);
    }catch(e){
      toast("Save failed: " + e.message, false);
    }
  });

  document.getElementById("btnValidate").addEventListener("click", async ()=>{
    try{
      await postJSON("/api/validate", {});
      toast("Validation complete (report updated)");
      setTimeout(()=>window.location.reload(), 650);
    }catch(e){
      toast("Validate failed: " + e.message, false);
    }
  });

  document.getElementById("btnSearch").addEventListener("click", async ()=>{
    const q = document.getElementById("q").value.trim();
    const kind = document.getElementById("kind").value;
    const tb = document.getElementById("results");
    if(!q){ toast("Type a search query", false); return; }
    tb.innerHTML = `<tr><td colspan="5" class="muted">Searching…</td></tr>`;
    try{
      const j = await postJSON("/api/search", { kind, query:q });
      const rows = (j.results || []);
      if(rows.length === 0){
        tb.innerHTML = `<tr><td colspan="5" class="muted">No matches.</td></tr>`;
        return;
      }
      tb.innerHTML = rows.map(r=>{
        const year = (kind==="tv" ? (r.first_air_date||"") : (r.release_date||"")).slice(0,4);
        const rating = (r.vote_average == null ? "" : r.vote_average.toFixed(1));
        const safeName = (r.name || "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
        return `
          <tr>
            <td class="mono">${r.id||""}</td>
            <td>
              <div>${safeName}</div>
              <div class="tiny muted">${(r.overview||"")}</div>
            </td>
            <td class="mono">${rating}</td>
            <td class="mono">${year}</td>
            <td class="right"><button class="btnAdd" data-id="${r.id||""}" data-name="${encodeURIComponent(r.name||"")}">Add</button></td>
          </tr>
        `;
      }).join("");
      document.querySelectorAll(".btnAdd").forEach(btn=>{
        btn.addEventListener("click", async ()=>{
          const target = document.getElementById("target").value;
          const season = document.getElementById("season").value.trim();
          const tmdb_id = btn.getAttribute("data-id");
          const name = decodeURIComponent(btn.getAttribute("data-name") || "");
          try{
            await postJSON("/api/add", { kind: target, tmdb_id, name, season_spec: season });
            toast(`Added to ${target}`);
            setTimeout(()=>window.location = "/?tab=" + encodeURIComponent(activeTab), 650);
          }catch(e){
            toast("Add failed: " + e.message, false);
          }
        });
      });
    }catch(e){
      tb.innerHTML = `<tr><td colspan="5" class="muted">Search failed: ${e.message}</td></tr>`;
      toast("Search failed: " + e.message, false);
    }
  });

  document.querySelectorAll("#invBody tr[data-idx]").forEach(tr=>{
    const idx = parseInt(tr.getAttribute("data-idx"), 10);

    const chk = tr.querySelector(".chkActive");
    if(chk){
      chk.addEventListener("change", async ()=>{
        try{
          await postJSON("/api/update", { tab: activeTab, idx, field:"active", value: chk.checked });
          toast("Updated active state");
          applyFilter();
        }catch(e){
          toast("Update failed: " + e.message, false);
          chk.checked = !chk.checked;
        }
      });
    }

    const se = tr.querySelector(".seasonEdit");
    if(se){
      let last = se.value;
      se.addEventListener("blur", async ()=>{
        const v = se.value.trim();
        if(v === last) return;
        try{
          await postJSON("/api/update", { tab: activeTab, idx, field:"season_spec", value: v });
          toast("Updated seasons");
          last = v;
        }catch(e){
          toast("Season update failed: " + e.message, false);
          se.value = last;
        }
      });
      se.addEventListener("keydown", (ev)=>{
        if(ev.key === "Enter"){ ev.preventDefault(); se.blur(); }
      });
    }

    const rm = tr.querySelector(".btnRemove");
    if(rm){
      rm.addEventListener("click", async ()=>{
        if(!confirm("Remove this row from the list?")) return;
        try{
          await postJSON("/api/remove", { tab: activeTab, idx });
          toast("Removed");
          setTimeout(()=>window.location.reload(), 350);
        }catch(e){
          toast("Remove failed: " + e.message, false);
        }
      });
    }
  });

  applyFilter();
</script>
</body>
</html>
"""


def build_counts(state: AppState) -> Dict[str, Any]:
    issues = state.issues_parse + state.issues_validate
    return {"records_total": sum(len(v) for v in state.records.values()), "issues_total": len(issues)}


def get_tabs() -> List[str]:
    return ["tv", "movie", "watchlist", "livetv"]


def active_file_for(tab: str) -> str:
    return {
        "tv": "inputs/tv_list.txt",
        "movie": "inputs/movies_list.txt",
        "watchlist": "inputs/watchlist.txt",
        "livetv": "inputs/livetv_list.txt",
    }.get(tab, "")


def create_app(state: AppState) -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    def render(tab: str) -> str:
        tab = (tab or "tv").lower().strip()
        if tab not in get_tabs():
            tab = "tv"
        rows = state.records.get(tab, [])
        issues = [dataclasses.asdict(i) for i in (state.issues_parse + state.issues_validate)]
        counts = build_counts(state)
        out_inputs = str((state.out_dir / "library_inputs.json").resolve())
        out_validation = str((state.out_dir / "validation_report.json").resolve())
        return render_template_string(
            BASE_HTML,
            app_name=APP_NAME,
            repo_root=str(state.repo_root),
            tabs=get_tabs(),
            active_tab=tab,
            active_file=active_file_for(tab),
            rows=rows,
            issues=issues,
            counts=counts,
            out_inputs=out_inputs,
            out_validation=out_validation,
        )

    @app.get("/")
    def index() -> str:
        tab = request.args.get("tab", "tv")
        return render(tab)

    @app.get("/reload")
    def reload() -> Response:
        state.load()
        return redirect(url_for("index", tab=request.args.get("tab", "tv")))

    @app.post("/api/search")
    def api_search() -> Response:
        data = request.get_json(force=True, silent=True) or {}
        kind = (data.get("kind") or "tv").lower().strip()
        query = (data.get("query") or "").strip()
        if kind not in ("tv", "movie"):
            return jsonify({"error": "Invalid kind"}), 400
        if not query:
            return jsonify({"error": "Query is empty"}), 400
        results = state.tmdb.search(kind, query)
        return jsonify({"results": results})

    @app.post("/api/add")
    def api_add() -> Response:
        data = request.get_json(force=True, silent=True) or {}
        kind = (data.get("kind") or "").lower().strip()
        tmdb_id = data.get("tmdb_id")
        name = (data.get("name") or "").strip()
        season_spec = (data.get("season_spec") or "").strip()

        if kind not in ("tv", "movie", "watchlist", "livetv"):
            return jsonify({"error": "Invalid kind"}), 400
        try:
            tmdb_id_int = int(tmdb_id)
        except Exception:
            return jsonify({"error": "TMDB id must be an integer"}), 400
        if not name:
            return jsonify({"error": "Name is required"}), 400

        if kind != "movie":
            season_spec = normalize_season_spec(season_spec)
            ok, _ = parse_season_spec(season_spec)
            if not ok:
                return jsonify({"error": "Season spec must be '*' or '1,2,3' or '1-3,5'."}), 400

        for r in state.records.get(kind, []):
            if r.tmdb_id == tmdb_id_int:
                return jsonify({"error": f"TMDB id already exists in {kind} list."}), 400

        state.records[kind].append(
            Record(
                kind=kind,
                active=True,
                name=name,
                tmdb_id=tmdb_id_int,
                season_spec=(season_spec if kind != "movie" else None),
                source_file=Path(active_file_for(kind)).name,
                line_no=0,
                raw_line="",
            )
        )
        state.records[kind] = sorted(state.records[kind], key=lambda x: (x.name or "").lower())
        state.export_json()
        return jsonify({"ok": True})

    @app.post("/api/update")
    def api_update() -> Response:
        data = request.get_json(force=True, silent=True) or {}
        tab = (data.get("tab") or "tv").lower().strip()
        idx = data.get("idx")
        field = (data.get("field") or "").strip()
        value = data.get("value")

        if tab not in get_tabs():
            return jsonify({"error": "Invalid tab"}), 400
        try:
            i = int(idx)
        except Exception:
            return jsonify({"error": "Invalid idx"}), 400

        try:
            r = state.records[tab][i]
        except Exception:
            return jsonify({"error": "Row not found"}), 404

        if field == "active":
            r.active = bool(value)
        elif field == "season_spec":
            if tab == "movie":
                return jsonify({"error": "Movie has no season spec"}), 400
            spec = normalize_season_spec(str(value or ""))
            ok, _ = parse_season_spec(spec)
            if not ok:
                return jsonify({"error": "Season spec must be '*' or '1,2,3' or '1-3,5'."}), 400
            r.season_spec = spec
        else:
            return jsonify({"error": "Invalid field"}), 400

        state.export_json()
        return jsonify({"ok": True})

    @app.post("/api/remove")
    def api_remove() -> Response:
        data = request.get_json(force=True, silent=True) or {}
        tab = (data.get("tab") or "tv").lower().strip()
        idx = data.get("idx")
        if tab not in get_tabs():
            return jsonify({"error": "Invalid tab"}), 400
        try:
            i = int(idx)
        except Exception:
            return jsonify({"error": "Invalid idx"}), 400
        try:
            state.records[tab].pop(i)
        except Exception:
            return jsonify({"error": "Row not found"}), 404
        state.export_json()
        return jsonify({"ok": True})

    @app.post("/api/validate")
    def api_validate() -> Response:
        state.validate()
        return jsonify({"ok": True})

    @app.post("/api/save")
    def api_save() -> Response:
        state.save()
        return jsonify({"ok": True})

    @app.errorhandler(Exception)
    def handle_exc(err: Exception):
        if request.path.startswith("/api/"):
            return jsonify({"error": str(err), "trace": traceback.format_exc()[:4000]}), 500
        return ("<pre>" + traceback.format_exc() + "</pre>", 500)

    return app


def read_tmdb_creds() -> Tuple[Optional[str], Optional[str]]:
    bearer = os.environ.get("API_TMDB_TOKEN") or os.environ.get("TMDB_BEARER_TOKEN") or os.environ.get("TMDB_API_READ_TOKEN")
    key = os.environ.get("API_TMDB_KEY") or os.environ.get("TMDB_API_KEY") or os.environ.get("TMDB_KEY")
    if bearer:
        bearer = bearer.strip()
    if key:
        key = key.strip()
    return key, bearer


def build_requests_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "my_TV_Movie-LibraryManager/0.2.2"})
    return s


def parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True, help="Path to my_TV_Movie repo root")
    ap.add_argument("--port", type=int, default=5177)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--out-dir", default="", help="Output dir (default: tools/library_manager/out)")
    return ap.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else (repo_root / "tools" / "library_manager" / "out")

    if not (repo_root / "inputs").exists():
        print(f"ERROR: inputs folder not found under repo root: {repo_root}", file=sys.stderr)
        return 2

    api_key, bearer = read_tmdb_creds()
    if not api_key and not bearer:
        print("ERROR: TMDB creds not found. Set API_TMDB_KEY or API_TMDB_TOKEN in environment.", file=sys.stderr)
        return 3

    s = build_requests_session()
    tmdb = TMDBClient(s, api_key=api_key, bearer_token=bearer)
    state = AppState(repo_root=repo_root, out_dir=out_dir, tmdb=tmdb)

    app = create_app(state)
    print(f"{APP_NAME} running at http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
# <<< END FILE
