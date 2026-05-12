# FILE: tools/media_renamer/media_library_page.py
# VERSION: v0.6.8
# UPDATED: 2026-05-11
# CHANGE NOTES:
# - Generates compact Recorded Media Library HTML and JSON.
# - Links episodes/movies to HTTP, local file, UNC, and SMB paths.
# - Copies Media_Library.html into both C:\X1_Share\Recordings and repo web\Media_Library.html.
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

VERSION = "0.6.8"
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts", ".mpg", ".mpeg", ".wmv"}
DEFAULT_REPO = Path(r"C:\Users\andrew\PROJECTS\GitHub\my_TV_Movie")
DEFAULT_MEDIA = Path(r"C:\X1_Share\Recordings")
DEFAULT_HTTP_BASE = "http://AJP-Laptop-X1CG10:8010"
SMB_HOST = "AJP-Laptop-X1CG10"
SHARE_NAME = "X1_Share"

SHOW_FOLDER_RE = re.compile(r"^(?P<title>.+?)\s*\[(?P<id>\d+)\]$")
MOVIE_FOLDER_RE = re.compile(r"^(?P<title>.+?)(?:\s*\((?P<year>\d{4})\))?\s*\[(?P<id>\d+)\]$")
EPISODE_FILE_RE = re.compile(r"(?i)S(?P<s>\d{1,4})E(?P<e>\d{1,3})")


@dataclass
class MediaLinks:
    http: str
    local: str
    unc: str
    smb: str


@dataclass
class EpisodeItem:
    show_title: str
    show_tmdb_id: int
    season_number: int
    episode_number: int
    episode_code: str
    title: str
    air_date: str
    runtime: str
    size_mb: float
    filename: str
    relative_path: str
    links: MediaLinks


@dataclass
class SeasonItem:
    season_number: int
    title: str
    episodes: list[EpisodeItem]


@dataclass
class ShowItem:
    title: str
    tmdb_id: int
    seasons: list[SeasonItem]
    episode_count: int
    new_7d: int
    new_14d: int


@dataclass
class MovieItem:
    title: str
    tmdb_id: int
    release_date: str
    runtime: str
    size_mb: float
    filename: str
    relative_path: str
    links: MediaLinks


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def fmt_runtime(value: object) -> str:
    try:
        minutes = int(value or 0)
    except (TypeError, ValueError):
        minutes = 0
    return f"{minutes}m" if minutes > 0 else ""


def file_size_mb(path: Path) -> float:
    try:
        return round(path.stat().st_size / 1024 / 1024, 1)
    except OSError:
        return 0.0


def relative_media_path(path: Path, media_root: Path) -> str:
    return path.relative_to(media_root).as_posix()


def build_links(path: Path, media_root: Path, http_base: str) -> MediaLinks:
    rel = relative_media_path(path, media_root)
    encoded_segments = "/".join(quote(part) for part in rel.split("/"))
    local_path = path.as_posix()
    unc = f"\\\\{SMB_HOST}\\{SHARE_NAME}\\" + rel.replace("/", "\\")
    smb = f"smb://{SMB_HOST}/{SHARE_NAME}/" + encoded_segments
    return MediaLinks(
        http=f"{http_base.rstrip('/')}/{encoded_segments}",
        local="file:///" + quote(local_path, safe="/:"),
        unc=unc,
        smb=smb,
    )


def load_episode_lookup(detail: dict) -> dict[tuple[int, int], dict]:
    lookup: dict[tuple[int, int], dict] = {}
    for season in detail.get("seasons", []) or []:
        try:
            season_number = int(season.get("season_number") or 0)
        except (TypeError, ValueError):
            continue
        for episode in season.get("episodes", []) or []:
            try:
                episode_number = int(episode.get("episode_number") or 0)
            except (TypeError, ValueError):
                continue
            lookup[(season_number, episode_number)] = episode
    return lookup


def scan_shows(repo_root: Path, media_root: Path, http_base: str) -> list[ShowItem]:
    tv_root = media_root / "TV"
    detail_dir = repo_root / "data" / "catalog_detail"
    shows: list[ShowItem] = []
    today = date.today()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)

    if not tv_root.exists():
        return shows

    for show_dir in sorted([p for p in tv_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        match = SHOW_FOLDER_RE.match(show_dir.name)
        if not match:
            continue
        title = match.group("title").strip()
        tmdb_id = int(match.group("id"))
        detail = load_json(detail_dir / f"{tmdb_id}.json")
        episode_lookup = load_episode_lookup(detail)
        seasons: list[SeasonItem] = []
        episode_total = 0
        new_7d = 0
        new_14d = 0

        for season_dir in sorted([p for p in show_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            season_num_match = re.search(r"(\d+)", season_dir.name)
            season_number = int(season_num_match.group(1)) if season_num_match else 0
            episodes: list[EpisodeItem] = []
            for media_file in sorted(season_dir.iterdir(), key=lambda p: p.name.lower()):
                if not media_file.is_file() or media_file.suffix.lower() not in MEDIA_EXTENSIONS:
                    continue
                ep_match = EPISODE_FILE_RE.search(media_file.name)
                if not ep_match:
                    continue
                parsed_season = int(ep_match.group("s"))
                episode_number = int(ep_match.group("e"))
                season_number = parsed_season or season_number
                meta = episode_lookup.get((season_number, episode_number), {})
                ep_title = str(meta.get("name") or media_file.stem).strip()
                air_date = str(meta.get("air_date") or "").strip()
                air_dt = parse_date(air_date)
                if air_dt and air_dt >= week_ago:
                    new_7d += 1
                if air_dt and air_dt >= two_weeks_ago:
                    new_14d += 1
                episodes.append(EpisodeItem(
                    show_title=title,
                    show_tmdb_id=tmdb_id,
                    season_number=season_number,
                    episode_number=episode_number,
                    episode_code=f"S{season_number:02d}E{episode_number:02d}",
                    title=ep_title,
                    air_date=air_date,
                    runtime=fmt_runtime(meta.get("runtime")),
                    size_mb=file_size_mb(media_file),
                    filename=media_file.name,
                    relative_path=relative_media_path(media_file, media_root),
                    links=build_links(media_file, media_root, http_base),
                ))
            if episodes:
                episode_total += len(episodes)
                seasons.append(SeasonItem(season_number=season_number, title=season_dir.name, episodes=episodes))

        if seasons:
            shows.append(ShowItem(title=title, tmdb_id=tmdb_id, seasons=seasons, episode_count=episode_total, new_7d=new_7d, new_14d=new_14d))
    return shows


def scan_movies(repo_root: Path, media_root: Path, http_base: str) -> list[MovieItem]:
    movies_root = media_root / "Movies"
    detail_dir = repo_root / "data" / "catalog_detail"
    movies: list[MovieItem] = []
    if not movies_root.exists():
        return movies
    for movie_dir in sorted([p for p in movies_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        match = MOVIE_FOLDER_RE.match(movie_dir.name)
        if not match:
            continue
        title = match.group("title").strip()
        tmdb_id = int(match.group("id"))
        detail = load_json(detail_dir / f"{tmdb_id}.json")
        media_files = [p for p in movie_dir.iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS]
        for media_file in sorted(media_files, key=lambda p: p.name.lower()):
            movies.append(MovieItem(
                title=str(detail.get("title") or title),
                tmdb_id=tmdb_id,
                release_date=str(detail.get("release_date") or ""),
                runtime=fmt_runtime(detail.get("runtime")),
                size_mb=file_size_mb(media_file),
                filename=media_file.name,
                relative_path=relative_media_path(media_file, media_root),
                links=build_links(media_file, media_root, http_base),
            ))
    return movies


def render_link_buttons(links: MediaLinks) -> str:
    return (
        f'<a class="linkbtn primary" href="{esc(links.http)}">HTTP</a>'
        f'<a class="linkbtn" href="{esc(links.local)}">Local</a>'
        f'<a class="linkbtn" href="{esc(links.smb)}">SMB</a>'
        f'<button class="linkbtn" data-copy="{esc(links.http)}">Copy HTTP</button>'
        f'<button class="linkbtn" data-copy="{esc(links.unc)}">Copy UNC</button>'
        f'<button class="linkbtn" data-copy="{esc(links.smb)}">Copy SMB</button>'
    )


def render_show(show: ShowItem) -> str:
    seasons_html = []
    for season in show.seasons:
        rows = []
        for ep in season.episodes:
            rows.append(
                '<tr class="episode-row">'
                f'<td class="code">{esc(ep.episode_code)}</td>'
                f'<td class="ep-title">{esc(ep.title)}</td>'
                f'<td>{esc(ep.air_date)}</td>'
                f'<td>{esc(ep.runtime)}</td>'
                f'<td>{ep.size_mb:.1f} MB</td>'
                f'<td class="file">{esc(ep.filename)}</td>'
                f'<td class="links">{render_link_buttons(ep.links)}</td>'
                '</tr>'
            )
        seasons_html.append(
            '<div class="season-block">'
            f'<div class="season-line">Season {season.season_number:02d} <span>{len(season.episodes)} ep</span></div>'
            '<table><tbody>' + ''.join(rows) + '</tbody></table></div>'
        )
    return (
        '<section class="show-block" data-filter="' + esc(f"{show.title} {show.tmdb_id}") + '">'
        '<button class="show-line" type="button">'
        '<span class="arrow">▸</span>'
        f'<span class="title">{esc(show.title)}</span>'
        f'<span class="pill">TMDb {show.tmdb_id}</span>'
        f'<span class="pill">{len(show.seasons)} seasons</span>'
        f'<span class="pill">{show.episode_count} ep</span>'
        f'<span class="pill green">{show.new_7d} new 7d</span>'
        f'<span class="pill blue">{show.new_14d} new 14d</span>'
        '</button>'
        '<div class="show-content">' + ''.join(seasons_html) + '</div>'
        '</section>'
    )


def render_movie(movie: MovieItem) -> str:
    return (
        '<section class="movie-line" data-filter="' + esc(f"{movie.title} {movie.tmdb_id} {movie.release_date}") + '">'
        f'<span class="title">{esc(movie.title)}</span>'
        f'<span class="pill">TMDb {movie.tmdb_id}</span>'
        f'<span class="pill">{esc(movie.release_date)}</span>'
        f'<span class="pill">{esc(movie.runtime)}</span>'
        f'<span class="file">{esc(movie.filename)}</span>'
        f'<span class="links">{render_link_buttons(movie.links)}</span>'
        '</section>'
    )


def render_html(shows: list[ShowItem], movies: list[MovieItem], media_root: Path) -> str:
    total_eps = sum(show.episode_count for show in shows)
    total_files = total_eps + len(movies)
    total_new_7 = sum(show.new_7d for show in shows)
    total_new_14 = sum(show.new_14d for show in shows)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="en" data-layout="compact-tree-v0.6.8">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recorded Media Library</title>
<style>
:root{{--bg:#06101f;--panel:#0d1830;--line:#1f3156;--text:#f4f7ff;--muted:#9fb0ca;--accent:#78e8ff;--green:#2bd576;--blue:#5aa2ff;--btn:#14284c}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:13px/1.25 Segoe UI,Arial,sans-serif;overflow-x:hidden}}
.top{{position:sticky;top:0;z-index:20;background:#081226;border-bottom:1px solid var(--line);display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:16px;padding:5px 10px}}
h1{{font-size:20px;margin:0;letter-spacing:.02em}} .gen{{color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.stats{{display:flex;align-items:stretch}} .stat{{min-width:72px;border-left:1px solid var(--line);padding:2px 8px;background:#0b1730}} .stat b{{display:block;font-size:18px}} .stat span{{color:var(--muted);font-size:11px;font-weight:700}}
.controls{{display:flex;gap:8px;padding:6px 10px;border-bottom:1px solid var(--line);background:#081226}} input{{flex:1;background:#071125;color:var(--text);border:1px solid var(--line);border-radius:7px;padding:7px 9px}} button,.linkbtn{{background:var(--btn);border:1px solid #24436f;border-radius:8px;color:var(--text);padding:5px 8px;text-decoration:none;cursor:pointer;font-weight:650;white-space:nowrap}} button:hover,.linkbtn:hover{{border-color:var(--accent)}}
.shell{{display:grid;grid-template-columns:94px minmax(0,1fr);min-height:calc(100vh - 72px)}} nav{{background:#0a1833;border-right:1px solid var(--line);padding:6px}} nav a{{display:block;color:var(--text);font-weight:800;text-decoration:none;padding:7px 6px;border-radius:6px}} nav a:hover{{background:#14284c}}
main{{min-width:0;padding:5px 8px}} .section-head{{font-size:16px;font-weight:900;margin:2px 0 6px;display:flex;justify-content:space-between;align-items:center}} .count{{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:2px 8px;color:#dbe8ff}}
.show-block,.movie-line{{border-bottom:1px solid #10284e}} .show-line{{width:100%;height:28px;display:grid;grid-template-columns:18px minmax(180px,1fr) auto auto auto auto auto;gap:7px;align-items:center;background:#0b1730;border:0;border-radius:0;text-align:left;padding:0 7px}}
.show-line .title,.movie-line .title{{font-size:15px;font-weight:850;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}} .arrow{{color:var(--accent)}} .show-block.open .arrow{{transform:rotate(90deg)}} .pill{{border:1px solid var(--line);border-radius:999px;padding:1px 7px;color:#d5e5ff;background:#071226;white-space:nowrap}} .green{{color:#071a10;background:var(--green);border-color:var(--green);font-weight:900}} .blue{{color:#061225;background:var(--blue);border-color:var(--blue);font-weight:900}}
.show-content{{display:none;margin:0 0 4px 24px}} .show-block.open .show-content{{display:block}} .season-line{{height:24px;display:flex;gap:8px;align-items:center;color:#d8e8ff;font-weight:800;background:#081426;padding:0 6px;border-left:2px solid var(--line)}} .season-line span{{color:var(--muted);font-weight:700}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}} td{{border-bottom:1px solid #12274b;padding:3px 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .code{{width:70px;color:var(--accent);font-weight:800}} .ep-title{{width:26%;font-weight:700}} .file{{color:var(--muted)}} .links{{width:360px;text-align:right;overflow:visible}} .linkbtn{{font-size:11px;padding:2px 5px;margin-left:3px}} .primary{{background:#145238;border-color:#238a55}}
.movie-line{{min-height:30px;display:grid;grid-template-columns:minmax(180px,1fr) auto auto auto minmax(180px,1fr) 360px;gap:7px;align-items:center;padding:3px 7px;background:#0b1730}}
.hidden{{display:none!important}} @media(max-width:1000px){{.top{{grid-template-columns:1fr}}.stats{{overflow:auto}}.shell{{grid-template-columns:1fr}}nav{{display:flex;gap:6px}}.show-line{{grid-template-columns:18px minmax(120px,1fr) auto auto auto}}.links{{width:260px}}.movie-line{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="top"><h1>Recorded Media Library</h1><div class="gen">Generated {esc(generated)} · {esc(media_root)}</div><div class="stats"><div class="stat"><span>Shows</span><b>{len(shows)}</b></div><div class="stat"><span>Episodes</span><b>{total_eps}</b></div><div class="stat"><span>Movies</span><b>{len(movies)}</b></div><div class="stat"><span>Files</span><b>{total_files}</b></div><div class="stat"><span>New 7d</span><b>{total_new_7}</b></div><div class="stat"><span>New 14d</span><b>{total_new_14}</b></div></div></header>
<div class="controls"><input id="filter" placeholder="Filter title, episode, TMDb, date, file..."><button id="expandAll">Expand all</button><button id="collapseAll">Collapse all</button></div>
<div class="shell"><nav><a href="#shows">TV Shows</a><a href="#movies">Movies</a></nav><main>
<section id="shows"><div class="section-head">TV Shows <span class="count">{len(shows)} shows</span></div>{''.join(render_show(s) for s in shows)}</section>
<section id="movies"><div class="section-head">Movies <span class="count">{len(movies)} movies</span></div>{''.join(render_movie(m) for m in movies)}</section>
</main></div>
<script>
const q=s=>document.querySelector(s), qa=s=>Array.from(document.querySelectorAll(s));
qa('.show-line').forEach(b=>b.addEventListener('click',()=>b.closest('.show-block').classList.toggle('open')));
q('#expandAll').onclick=()=>qa('.show-block').forEach(x=>x.classList.add('open'));
q('#collapseAll').onclick=()=>qa('.show-block').forEach(x=>x.classList.remove('open'));
q('#filter').addEventListener('input',e=>{{const v=e.target.value.toLowerCase();qa('[data-filter]').forEach(x=>x.classList.toggle('hidden',v && !x.dataset.filter.toLowerCase().includes(v) && !x.textContent.toLowerCase().includes(v)));}});
document.addEventListener('click',async e=>{{const b=e.target.closest('[data-copy]'); if(!b)return; await navigator.clipboard.writeText(b.dataset.copy); const old=b.textContent; b.textContent='Copied'; setTimeout(()=>b.textContent=old,900);}});
</script>
</body></html>"""


def write_outputs(repo_root: Path, media_root: Path, html_text: str, data: dict) -> None:
    media_root.mkdir(parents=True, exist_ok=True)
    (media_root / "Media_Library.html").write_text(html_text, encoding="utf-8", newline="\n")
    (media_root / "Media_Library.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    web_dir = repo_root / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    (web_dir / "Media_Library.html").write_text(html_text, encoding="utf-8", newline="\n")
    (web_dir / "Media_Library.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    report_dir = repo_root / "reports" / "media_library" / datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "recordings_library.html").write_text(html_text, encoding="utf-8", newline="\n")
    (report_dir / "recordings_library.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def generate(repo_root: Path, media_root: Path, http_base: str) -> dict:
    shows = scan_shows(repo_root, media_root, http_base)
    movies = scan_movies(repo_root, media_root, http_base)
    data = {"version": VERSION, "generated_at": datetime.now().isoformat(timespec="seconds"), "media_root": str(media_root), "shows": [asdict(s) for s in shows], "movies": [asdict(m) for m in movies]}
    write_outputs(repo_root, media_root, render_html(shows, movies, media_root), data)
    return {"shows": len(shows), "episodes": sum(s.episode_count for s in shows), "movies": len(movies), "html": str(media_root / "Media_Library.html")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Recorded Media Library HTML.")
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument("--media-root", default=str(DEFAULT_MEDIA))
    parser.add_argument("--http-base", default=DEFAULT_HTTP_BASE)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo)
    media_root = Path(args.media_root)
    if args.self_test:
        _ = render_html([], [], media_root)
        return 0
    result = generate(repo_root, media_root, args.http_base)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
