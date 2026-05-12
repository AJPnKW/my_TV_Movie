# FILE: tools/media_renamer/generate_media_library_page.py
# VERSION: v0.6.4
# UPDATED: 2026-05-11
# PURPOSE: Generate compact Recorded Media Library HTML with playable HTTP/SMB/UNC media links.
from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

VERSION = "0.6.4"
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv"}
TMDB_RE = re.compile(r"\[(?P<id>\d+)\]")
EP_RE = re.compile(r"S(?P<s>\d{1,4})E(?P<e>\d{1,3})", re.IGNORECASE)
DEFAULT_REPO = Path(r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
DEFAULT_MEDIA = Path(r"C:\X1_Share\Recordings")
DEFAULT_HOST = "AJP-Laptop-X1CG10"
DEFAULT_SHARE = "X1_Share"
DEFAULT_PORT = 8010


@dataclass
class MediaLink:
    local_file: str
    unc: str
    smb: str
    http: str


@dataclass
class EpisodeRow:
    season_number: int
    episode_number: int
    title: str
    air_date: str
    runtime: str
    file_name: str
    file_size: str
    path: str
    links: MediaLink


@dataclass
class SeasonRow:
    season_number: int
    title: str
    episodes: list[EpisodeRow] = field(default_factory=list)


@dataclass
class ShowRow:
    title: str
    tmdb_id: int
    genres: str
    seasons: list[SeasonRow] = field(default_factory=list)
    episode_count: int = 0
    new_7d: int = 0
    new_14d: int = 0


@dataclass
class MovieRow:
    title: str
    tmdb_id: int
    release_date: str
    runtime: str
    genres: str
    file_name: str
    file_size: str
    path: str
    links: MediaLink


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_text(value: Any) -> str:
    return str(value or "").strip()


def fmt_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def fmt_runtime(value: Any) -> str:
    if value in (None, "", 0):
        return ""
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return ""
    return f"{minutes}m"


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def genre_text(detail: dict[str, Any]) -> str:
    genres = detail.get("genres") or []
    names = [safe_text(g.get("name")) for g in genres if isinstance(g, dict) and safe_text(g.get("name"))]
    return ", ".join(names[:3])


def tmdb_id_from_name(name: str) -> int | None:
    match = TMDB_RE.search(name)
    return int(match.group("id")) if match else None


def episode_identity(file_name: str) -> tuple[int | None, int | None]:
    match = EP_RE.search(file_name)
    if not match:
        return None, None
    return int(match.group("s")), int(match.group("e"))


def media_links(path: Path, media_root: Path, host: str, share: str, port: int) -> MediaLink:
    rel = path.relative_to(media_root)
    rel_posix = "/".join(quote(part) for part in rel.parts)
    unc = f"\\\\{host}\\{share}\\Recordings\\" + "\\".join(rel.parts)
    smb = f"smb://{host}/{share}/Recordings/{rel_posix}"
    http_url = f"http://{host}:{port}/{rel_posix}"
    file_url = "file:///" + quote(str(path).replace("\\", "/"), safe="/:()[]&'!,-._~% ").replace(" ", "%20")
    return MediaLink(local_file=file_url, unc=unc, smb=smb, http=http_url)


def episode_detail(detail: dict[str, Any], season_number: int, episode_number: int) -> dict[str, Any]:
    for season in detail.get("seasons") or []:
        if int(season.get("season_number") or -1) != season_number:
            continue
        for ep in season.get("episodes") or []:
            if int(ep.get("episode_number") or -1) == episode_number:
                return ep
    return {}


def scan_shows(repo_root: Path, media_root: Path, host: str, share: str, port: int) -> list[ShowRow]:
    shows_root = media_root / "TV"
    detail_root = repo_root / "data" / "catalog_detail"
    if not shows_root.exists():
        return []
    today = date.today()
    seven = today - timedelta(days=7)
    fourteen = today - timedelta(days=14)
    shows: list[ShowRow] = []
    for show_dir in sorted([p for p in shows_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        if show_dir.name.startswith("_"):
            continue
        tmdb_id = tmdb_id_from_name(show_dir.name)
        if not tmdb_id:
            continue
        detail = load_json(detail_root / f"{tmdb_id}.json")
        title = safe_text(detail.get("title") or detail.get("name") or TMDB_RE.sub("", show_dir.name).strip())
        show = ShowRow(title=title, tmdb_id=tmdb_id, genres=genre_text(detail))
        season_map: dict[int, SeasonRow] = {}
        for file in sorted(show_dir.rglob("*"), key=lambda p: str(p).lower()):
            if not file.is_file() or file.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            season_number, episode_number = episode_identity(file.name)
            if season_number is None or episode_number is None:
                continue
            ep_detail = episode_detail(detail, season_number, episode_number)
            ep_title = safe_text(ep_detail.get("name")) or EP_RE.sub("", file.stem).split(" - ")[-1].strip() or f"Episode {episode_number:02d}"
            air_date = safe_text(ep_detail.get("air_date"))
            runtime = fmt_runtime(ep_detail.get("runtime") or (detail.get("episode_run_time") or [""])[0] if detail.get("episode_run_time") else "")
            ep = EpisodeRow(
                season_number=season_number,
                episode_number=episode_number,
                title=ep_title,
                air_date=air_date,
                runtime=runtime,
                file_name=file.name,
                file_size=fmt_size(file.stat().st_size),
                path=str(file),
                links=media_links(file, media_root, host, share, port),
            )
            season_map.setdefault(season_number, SeasonRow(season_number=season_number, title=f"Season {season_number:02d}" if season_number < 100 else f"Season {season_number}"))
            season_map[season_number].episodes.append(ep)
            show.episode_count += 1
            d = parse_date(air_date)
            if d:
                if d >= seven:
                    show.new_7d += 1
                if d >= fourteen:
                    show.new_14d += 1
        show.seasons = [season_map[k] for k in sorted(season_map)]
        if show.episode_count:
            shows.append(show)
    return shows


def scan_movies(repo_root: Path, media_root: Path, host: str, share: str, port: int) -> list[MovieRow]:
    movies_root = media_root / "Movies"
    detail_root = repo_root / "data" / "catalog_detail"
    if not movies_root.exists():
        return []
    movies: list[MovieRow] = []
    for movie_dir in sorted([p for p in movies_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        tmdb_id = tmdb_id_from_name(movie_dir.name)
        if not tmdb_id:
            continue
        detail = load_json(detail_root / f"{tmdb_id}.json")
        title = safe_text(detail.get("title") or TMDB_RE.sub("", movie_dir.name).strip())
        files = [p for p in movie_dir.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS]
        for file in sorted(files, key=lambda p: p.name.lower()):
            movies.append(MovieRow(
                title=title,
                tmdb_id=tmdb_id,
                release_date=safe_text(detail.get("release_date")),
                runtime=fmt_runtime(detail.get("runtime")),
                genres=genre_text(detail),
                file_name=file.name,
                file_size=fmt_size(file.stat().st_size),
                path=str(file),
                links=media_links(file, media_root, host, share, port),
            ))
    return movies


def row_attrs(values: list[str]) -> str:
    return html.escape(" ".join(values).lower(), quote=True)


def ep_html(ep: EpisodeRow) -> str:
    ident = f"S{ep.season_number:02d}E{ep.episode_number:02d}"
    search = row_attrs([ident, ep.title, ep.air_date, ep.file_name, ep.path])
    return f"""
    <tr class="episode-row" data-search="{search}">
      <td class="ep-code">{html.escape(ident)}</td>
      <td class="ep-title">{html.escape(ep.title)}</td>
      <td>{html.escape(ep.air_date)}</td>
      <td>{html.escape(ep.runtime)}</td>
      <td>{html.escape(ep.file_size)}</td>
      <td class="links">
        <a href="{html.escape(ep.links.http, quote=True)}" target="_blank">HTTP</a>
        <button data-copy="{html.escape(ep.links.http, quote=True)}">Copy HTTP</button>
        <button data-copy="{html.escape(ep.links.unc, quote=True)}">Copy UNC</button>
        <button data-copy="{html.escape(ep.links.smb, quote=True)}">Copy SMB</button>
      </td>
    </tr>"""


def show_html(show: ShowRow) -> str:
    search = row_attrs([show.title, str(show.tmdb_id), show.genres] + [ep.title for s in show.seasons for ep in s.episodes])
    badges = []
    if show.new_7d:
        badges.append(f"<span class='badge green'>{show.new_7d} new 7d</span>")
    if show.new_14d:
        badges.append(f"<span class='badge blue'>{show.new_14d} new 14d</span>")
    badge_html = "".join(badges)
    seasons_html = []
    for season in show.seasons:
        episodes = "".join(ep_html(ep) for ep in season.episodes)
        seasons_html.append(f"""
        <div class="season-block">
          <div class="season-line">{html.escape(season.title)} <span>{len(season.episodes)} ep</span></div>
          <table><tbody>{episodes}</tbody></table>
        </div>""")
    return f"""
    <section class="show-node" data-search="{search}">
      <button class="show-line" type="button">
        <span class="twisty">▸</span>
        <span class="title">{html.escape(show.title)}</span>
        <span class="pill">TMDb {show.tmdb_id}</span>
        <span class="pill">{len(show.seasons)} seasons</span>
        <span class="pill">{show.episode_count} ep</span>
        {badge_html}
        <span class="genres">{html.escape(show.genres)}</span>
      </button>
      <div class="children">{''.join(seasons_html)}</div>
    </section>"""


def movie_html(movie: MovieRow) -> str:
    search = row_attrs([movie.title, str(movie.tmdb_id), movie.release_date, movie.genres, movie.file_name])
    return f"""
    <section class="movie-line" data-search="{search}">
      <span class="title">{html.escape(movie.title)}</span>
      <span class="pill">TMDb {movie.tmdb_id}</span>
      <span class="pill">{html.escape(movie.release_date)}</span>
      <span class="pill">{html.escape(movie.runtime)}</span>
      <span class="genres">{html.escape(movie.genres)}</span>
      <span class="links"><a href="{html.escape(movie.links.http, quote=True)}" target="_blank">HTTP</a><button data-copy="{html.escape(movie.links.http, quote=True)}">Copy HTTP</button><button data-copy="{html.escape(movie.links.unc, quote=True)}">Copy UNC</button><button data-copy="{html.escape(movie.links.smb, quote=True)}">Copy SMB</button></span>
    </section>"""


def render_html(shows: list[ShowRow], movies: list[MovieRow], media_root: Path, host: str, port: int) -> str:
    total_eps = sum(s.episode_count for s in shows)
    total_files = total_eps + len(movies)
    total_new7 = sum(s.new_7d for s in shows)
    show_blocks = "".join(show_html(show) for show in shows)
    movie_blocks = "".join(movie_html(movie) for movie in movies)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recorded Media Library</title>
<style>
:root{{--bg:#07101f;--panel:#0d1830;--line:#1e3157;--text:#eef5ff;--muted:#9fb0ce;--cyan:#68f0ff;--green:#30d158;--blue:#3b82f6;--button:#152947}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Segoe UI,Arial,sans-serif;font-size:13px;overflow-x:hidden}}
.top{{height:47px;display:grid;grid-template-columns:260px 1fr 64px 72px 58px 58px 70px 86px 92px;align-items:center;border-bottom:1px solid var(--line);background:#081126;position:sticky;top:0;z-index:5}}
.brand{{font-size:19px;font-weight:800;letter-spacing:.4px;padding-left:22px;white-space:nowrap}}.meta{{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.stat{{height:47px;border-left:1px solid var(--line);padding:5px 9px}}.stat b{{display:block;font-size:17px}}.stat span{{color:var(--muted);font-size:11px;font-weight:700}}
.top button{{margin:5px 6px;padding:8px 10px;border:0;border-radius:9px;background:var(--button);color:var(--text);font-weight:700;cursor:pointer}}
.toolbar{{height:44px;display:grid;grid-template-columns:100px 1fr;gap:10px;align-items:center;border-bottom:1px solid var(--line);background:#09152b;padding:7px 12px}}
.rail{{font-weight:800;font-size:16px}}#filter{{height:30px;background:#07101f;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:0 12px;width:100%}}
.main{{display:grid;grid-template-columns:100px 1fr;min-height:calc(100vh - 91px)}}.side{{background:#0b1731;border-right:1px solid var(--line);font-weight:800;padding:6px 9px;color:#cfe0ff}}
.content{{min-width:0}}.section-title{{height:24px;display:flex;align-items:center;justify-content:space-between;padding:0 10px;font-size:15px;font-weight:800;background:#0b1731}}
.show-node,.movie-line{{border-bottom:1px solid rgba(255,255,255,.045)}}.show-line,.movie-line{{width:100%;height:28px;display:flex;align-items:center;gap:8px;background:#0d1830;color:var(--text);border:0;padding:0 10px;text-align:left;white-space:nowrap;overflow:hidden}}
.show-line:hover,.movie-line:hover{{background:#132342}}.twisty{{color:var(--cyan);width:14px}}.title{{font-weight:800;min-width:150px;max-width:330px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pill,.badge{{border:1px solid var(--line);border-radius:999px;padding:2px 8px;font-size:12px;white-space:nowrap;color:#e8f2ff}}.badge.green{{background:rgba(48,209,88,.18);border-color:rgba(48,209,88,.6);color:#98ffb0}}.badge.blue{{background:rgba(59,130,246,.22);border-color:rgba(59,130,246,.7);color:#bbd4ff}}
.genres{{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}}.children{{display:none;background:#081226}}.show-node.open .children{{display:block}}.show-node.open .twisty{{transform:rotate(90deg)}}
.season-line{{height:24px;display:flex;align-items:center;gap:8px;padding-left:34px;background:#09172f;color:#d7e6ff;font-weight:700;border-top:1px solid rgba(255,255,255,.04)}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}td{{height:24px;border-top:1px solid rgba(255,255,255,.04);padding:2px 6px;color:#dce8ff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.ep-code{{width:75px;padding-left:48px;color:var(--cyan);font-weight:800}}.ep-title{{width:34%;font-weight:650}}
.links{{display:flex;gap:5px;justify-content:flex-end}}a,.links button{{border:1px solid var(--line);background:#10213d;color:#eaf4ff;border-radius:7px;padding:2px 7px;text-decoration:none;font-size:12px;cursor:pointer}}
.hidden{{display:none!important}}@media(max-width:900px){{.top{{grid-template-columns:1fr 50px 58px 45px 45px 56px 65px 72px}}.meta{{display:none}}.main,.toolbar{{grid-template-columns:75px 1fr}}.title{{max-width:180px}}.genres{{display:none}}}}
</style></head><body data-layout="compact-linked-tree-v0.6.4">
<header class="top"><div class="brand">Recorded Media Library</div><div class="meta">Generated {html.escape(generated)} · {html.escape(str(media_root))} · HTTP {html.escape(host)}:{port}</div><div class="stat"><span>Shows</span><b>{len(shows)}</b></div><div class="stat"><span>Episodes</span><b>{total_eps}</b></div><div class="stat"><span>Movies</span><b>{len(movies)}</b></div><div class="stat"><span>Files</span><b>{total_files}</b></div><div class="stat"><span>New 7d</span><b>{total_new7}</b></div><button id="expandAll">Expand all</button><button id="collapseAll">Collapse all</button></header>
<div class="toolbar"><div class="rail">TV Shows</div><input id="filter" placeholder="Filter title, episode, TMDb, date, genre, file..."></div>
<main class="main"><aside class="side"><div>TV Shows</div><div style="margin-top:16px">Movies</div></aside><section class="content"><div class="section-title"><span>TV Shows</span><span>{len(shows)} shows</span></div>{show_blocks}<div class="section-title"><span>Movies</span><span>{len(movies)} movies</span></div>{movie_blocks}</section></main>
<script>
function copyText(v){{navigator.clipboard.writeText(v).then(()=>{{}}).catch(()=>prompt('Copy this path:',v));}}
document.querySelectorAll('.show-line').forEach(btn=>btn.addEventListener('click',()=>btn.closest('.show-node').classList.toggle('open')));
document.querySelectorAll('[data-copy]').forEach(btn=>btn.addEventListener('click',e=>{{e.stopPropagation();copyText(btn.dataset.copy);}}));
document.getElementById('expandAll').onclick=()=>document.querySelectorAll('.show-node').forEach(n=>n.classList.add('open'));
document.getElementById('collapseAll').onclick=()=>document.querySelectorAll('.show-node').forEach(n=>n.classList.remove('open'));
document.getElementById('filter').addEventListener('input',e=>{{let q=e.target.value.toLowerCase().trim();document.querySelectorAll('[data-search]').forEach(n=>{{let hit=!q||n.dataset.search.includes(q);n.classList.toggle('hidden',!hit);if(hit&&q&&n.classList.contains('episode-row')){{let p=n.closest('.show-node');if(p)p.classList.add('open');}}}});}});
</script></body></html>"""


def generate(repo_root: Path, media_root: Path, host: str, share: str, port: int) -> dict[str, Any]:
    shows = scan_shows(repo_root, media_root, host, share, port)
    movies = scan_movies(repo_root, media_root, host, share, port)
    html_text = render_html(shows, movies, media_root, host, port)
    html_path = media_root / "Media_Library.html"
    json_path = media_root / "Media_Library.json"
    html_path.write_text(html_text, encoding="utf-8", newline="\n")
    payload = {"version": VERSION, "generated_at": datetime.now().isoformat(timespec="seconds"), "media_root": str(media_root), "shows": [asdict(s) for s in shows], "movies": [asdict(m) for m in movies]}
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    report_dir = repo_root / "reports" / "media_library" / datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "recordings_library.html").write_text(html_text, encoding="utf-8", newline="\n")
    (report_dir / "recordings_library.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    return {"html": str(html_path), "json": str(json_path), "shows": len(shows), "episodes": sum(s.episode_count for s in shows), "movies": len(movies), "report_dir": str(report_dir)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", "--repo-root", dest="repo", default=str(DEFAULT_REPO))
    parser.add_argument("--media-root", default=str(DEFAULT_MEDIA))
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--share", default=DEFAULT_SHARE)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    result = generate(Path(args.repo), Path(args.media_root), args.host, args.share, args.port)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
