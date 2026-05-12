from __future__ import annotations
import argparse, html, json, re, tempfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
VERSION='0.6.6'; MEDIA_EXT={'.mp4','.mkv','.avi','.mov','.m4v','.ts','.mpg','.mpeg','.wmv'}; ID_RE=re.compile(r'\[(\d{2,})\]\s*$'); EP_RE=re.compile(r'S(\d{1,4})E(\d{1,3})',re.I)
@dataclass
class Ep: show:str; show_id:int; season:int; episode:int; title:str; air_date:str; runtime:str; file_name:str; rel:str; size:float; http:str; local:str; unc:str; smb:str
@dataclass
class Season: number:int; name:str; episodes:list[Ep]=field(default_factory=list)
@dataclass
class Show: title:str; tmdb_id:int; season_count:int; episode_count:int; new7:int; new14:int; genres:str; seasons:list[Season]=field(default_factory=list)
@dataclass
class Movie: title:str; tmdb_id:int; release_date:str; runtime:str; genres:str; file_name:str; rel:str; size:float; http:str; local:str; unc:str; smb:str
def e(v): return html.escape('' if v is None else str(v),quote=True)
def load(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def title_id(name):
    m=ID_RE.search(name); return (ID_RE.sub('',name).strip(), int(m.group(1)) if m else 0)
def genres(d): return ', '.join([str(g.get('name')) for g in d.get('genres',[]) if isinstance(g,dict) and g.get('name')][:3])
def runtime(v):
    try: n=int(v or 0)
    except Exception: n=0
    return f'{n}m' if n else ''
def season_no(name):
    m=re.search(r'Season\s+(\d{1,4})',name,re.I); return int(m.group(1)) if m else 0
def parse_ep(p):
    m=EP_RE.search(p.stem); return (int(m.group(1)),int(m.group(2)),p.stem[m.end():].strip(' -_.') or p.stem) if m else (0,0,p.stem)
def ep_detail(d,s,e):
    for sea in d.get('seasons',[]) or []:
        if int(sea.get('season_number') or -1)==s:
            for ep in sea.get('episodes',[]) or []:
                if int(ep.get('episode_number') or -1)==e: return ep
    return {}
def sea_name(d,s,f):
    for sea in d.get('seasons',[]) or []:
        if int(sea.get('season_number') or -1)==s: return str(sea.get('name') or f)
    return f
def last_days(v,days,today):
    try: dt=date.fromisoformat((v or '')[:10])
    except Exception: return False
    return today-timedelta(days=days)<=dt<=today
def urls(root,p,host,port):
    rel=p.relative_to(root).as_posix(); enc=quote(rel,safe="/()[]-_. '"); local='file:///'+quote(str(p).replace('\\','/'),safe='/:()[]-_. '); unc='\\\\'+host+'\\X1_Share\\Recordings\\'+str(p.relative_to(root)).replace('/','\\'); smb='smb://'+host+'/X1_Share/Recordings/'+enc; http=f'http://{host}:{port}/'+enc; return rel,http,local,unc,smb
def collect(root,repo,host,port):
    detail=repo/'data'/'catalog_detail'; today=date.today(); shows=[]; movies=[]; tv=root/'TV'
    if tv.exists():
        for sf in sorted([x for x in tv.iterdir() if x.is_dir()],key=lambda x:x.name.lower()):
            ft,id=title_id(sf.name); d=load(detail/f'{id}.json') if id else {}; title=str(d.get('title') or d.get('name') or ft); seas=[]; all=[]
            for sdir in sorted([x for x in sf.iterdir() if x.is_dir()],key=lambda x:x.name.lower()):
                sn=season_no(sdir.name); season=Season(sn,sea_name(d,sn,sdir.name))
                for mf in sorted([x for x in sdir.iterdir() if x.is_file() and x.suffix.lower() in MEDIA_EXT],key=lambda x:x.name.lower()):
                    ps,pe,pt=parse_ep(mf); sn2=sn or ps; ed=ep_detail(d,sn2,pe); rel,http,local,unc,smb=urls(root,mf,host,port); ep=Ep(title,id,sn2,pe,str(ed.get('name') or pt),str(ed.get('air_date') or ''),runtime(ed.get('runtime') or (d.get('episode_run_time') or [None])[0]),mf.name,rel,round(mf.stat().st_size/1048576,1),http,local,unc,smb); season.episodes.append(ep); all.append(ep)
                if season.episodes: seas.append(season)
            if all: shows.append(Show(title,id,len(seas),len(all),sum(last_days(x.air_date,7,today) for x in all),sum(last_days(x.air_date,14,today) for x in all),genres(d),seas))
    mr=root/'Movies'
    if mr.exists():
        for fd in sorted([x for x in mr.iterdir() if x.is_dir()],key=lambda x:x.name.lower()):
            ft,id=title_id(fd.name); d=load(detail/f'{id}.json') if id else {}; title=str(d.get('title') or ft)
            for mf in sorted([x for x in fd.iterdir() if x.is_file() and x.suffix.lower() in MEDIA_EXT],key=lambda x:x.name.lower()):
                rel,http,local,unc,smb=urls(root,mf,host,port); movies.append(Movie(title,id,str(d.get('release_date') or ''),runtime(d.get('runtime')),genres(d),mf.name,rel,round(mf.stat().st_size/1048576,1),http,local,unc,smb))
    return shows,movies
def buttons(i): return f'<a class="mini play" href="{e(i.http)}">HTTP</a><a class="mini" href="{e(i.local)}">Local</a><button class="mini" data-copy="{e(i.http)}">Copy HTTP</button><button class="mini" data-copy="{e(i.unc)}">Copy UNC</button><button class="mini" data-copy="{e(i.smb)}">Copy SMB</button>'
def render(root,shows,movies):
    eps=sum(s.episode_count for s in shows); new7=sum(s.new7 for s in shows); new14=sum(s.new14 for s in shows); files=eps+len(movies); sr=[]
    for n,s in enumerate(shows,1):
        head=f'<div class="row show" data-target="show{n}" data-search="{e(s.title)} {s.tmdb_id} {e(s.genres)}"><span class="caret">▸</span><span class="title clip">{e(s.title)}</span><span class="pill">TMDb {s.tmdb_id}</span><span class="pill">{s.season_count} seasons</span><span class="pill">{s.episode_count} ep</span><span class="pill green">{s.new7} new 7d</span><span class="pill blue">{s.new14} new 14d</span><span class="muted clip">{e(s.genres)}</span></div>'
        blocks=[]
        for sea in s.seasons:
            trs=[]
            for ep in sea.episodes: trs.append(f'<tr data-search="{e(s.title)} {e(ep.title)} {s.tmdb_id} {e(ep.file_name)}"><td>S{ep.season:02d}E{ep.episode:02d}</td><td class="clip">{e(ep.title)}</td><td>{e(ep.air_date)}</td><td>{e(ep.runtime)}</td><td>{ep.size:.1f} MB</td><td class="clip">{e(ep.file_name)}</td><td class="links">{buttons(ep)}</td></tr>')
            blocks.append(f'<div class="season"><b>Season {sea.number:02d}</b><span class="pill">{len(sea.episodes)} ep</span><span class="muted clip">{e(sea.name)}</span></div><table>{"".join(trs)}</table>')
        sr.append(head+f'<div id="show{n}" class="detail">{"".join(blocks)}</div>')
    mr=[f'<div class="row movie" data-search="{e(m.title)} {m.tmdb_id} {e(m.file_name)}"><span>•</span><span class="title clip">{e(m.title)}</span><span class="pill">TMDb {m.tmdb_id}</span><span class="pill">{e(m.release_date)}</span><span class="pill">{e(m.runtime)}</span><span class="muted clip">{e(m.genres)}</span><span class="links">{buttons(m)}</span></div>' for m in movies]
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recorded Media Library</title><style>:root{{--bg:#050914;--p:#0b1426;--r:#0b142b;--l:#1c2c4e;--t:#edf4ff;--m:#91a5c6;--g:#1fbf75;--b:#3b82f6}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--t);font-family:Segoe UI,Arial,sans-serif;font-size:13px}}.top{{position:sticky;top:0;z-index:9;display:grid;grid-template-columns:260px 1fr auto;gap:10px;align-items:center;background:#081022;border-bottom:1px solid var(--l);padding:4px 8px}}h1{{font-size:18px;margin:0}}.meta{{font-size:11px;color:var(--m);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.stats{{display:flex;height:38px}}.stat{{min-width:66px;padding:3px 8px;border-left:1px solid var(--l);background:#0e1a34}}.stat b{{font-size:16px;display:block;line-height:16px}}.stat span{{font-size:10px;color:var(--m);font-weight:800}}.ctrl{{display:grid;grid-template-columns:1fr 88px 88px;gap:8px;padding:6px 8px;background:#081022;border-bottom:1px solid var(--l)}}input,button,.mini{{background:#132441;color:var(--t);border:1px solid var(--l);border-radius:8px;padding:5px 8px}}.shell{{display:grid;grid-template-columns:96px 1fr}}.nav{{background:#0b1530;border-right:1px solid var(--l)}}.nav a{{display:block;color:var(--t);text-decoration:none;padding:7px 8px;font-weight:800}}.section{{display:flex;justify-content:space-between;height:28px;padding:4px 8px;background:#071027;font-weight:900}}.row{{display:grid;align-items:center;gap:6px;min-height:25px;padding:2px 8px;border-bottom:1px solid #12203c;background:#0b142b}}.show{{grid-template-columns:18px minmax(160px,1fr) auto auto auto auto auto minmax(80px,.6fr)}}.movie{{grid-template-columns:18px minmax(180px,1fr) auto auto auto minmax(90px,.6fr) minmax(360px,auto)}}.title{{font-weight:850;font-size:14px}}.clip{{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}.pill{{height:18px;border:1px solid var(--l);border-radius:999px;padding:0 7px;white-space:nowrap;background:#091426}}.green{{background:rgba(31,191,117,.18);border-color:var(--g)}}.blue{{background:rgba(59,130,246,.2);border-color:var(--b)}}.muted{{color:var(--m)}}.detail{{display:none;background:#071126}}.detail.open{{display:block}}.season{{display:grid;grid-template-columns:90px 58px minmax(160px,1fr);gap:6px;align-items:center;height:24px;padding:2px 8px 2px 28px;background:#0d1931}}table{{width:100%;border-collapse:collapse;table-layout:fixed}}td{{border-bottom:1px solid #111f3a;padding:3px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;height:24px}}td:nth-child(1){{width:70px;padding-left:42px;font-weight:800}}td:nth-child(3){{width:86px;color:var(--m)}}td:nth-child(4){{width:54px;color:var(--m)}}td:nth-child(5){{width:80px;color:var(--m)}}td:nth-child(7){{width:440px}}.links{{display:flex;gap:4px;justify-content:flex-end}}.mini{{font-size:11px;height:21px;padding:2px 6px;text-decoration:none;white-space:nowrap}}.play{{background:#123a2d;border-color:var(--g)}}.hidden{{display:none!important}}</style></head><body><header class="top"><h1>Recorded Media Library</h1><div class="meta">Generated {e(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))} · {e(root)}</div><div class="stats"><div class="stat"><span>Shows</span><b>{len(shows)}</b></div><div class="stat"><span>Episodes</span><b>{eps}</b></div><div class="stat"><span>Movies</span><b>{len(movies)}</b></div><div class="stat"><span>Files</span><b>{files}</b></div><div class="stat"><span>New 7d</span><b>{new7}</b></div><div class="stat"><span>New 14d</span><b>{new14}</b></div></div></header><div class="ctrl"><input id="f" placeholder="Filter..."><button id="ea">Expand all</button><button id="ca">Collapse all</button></div><main class="shell"><nav class="nav"><a href="#tv">TV Shows</a><a href="#movies">Movies</a></nav><section><div id="tv" class="section"><span>TV Shows</span><span class="pill">{len(shows)} shows</span></div>{''.join(sr)}<div id="movies" class="section"><span>Movies</span><span class="pill">{len(movies)} movies</span></div>{''.join(mr)}</section></main><script>function q(id){{return document.getElementById(id)}}document.addEventListener('click',ev=>{{let c=ev.target.closest('[data-copy]');if(c){{navigator.clipboard.writeText(c.getAttribute('data-copy')||'');c.textContent='Copied';setTimeout(()=>c.textContent=c.getAttribute('data-copy').startsWith('http')?'Copy HTTP':c.getAttribute('data-copy').startsWith('smb')?'Copy SMB':'Copy UNC',900);return}}let r=ev.target.closest('.show');if(r){{let d=q(r.dataset.target);let o=d&&!d.classList.contains('open');if(d)d.classList.toggle('open',o);let ca=r.querySelector('.caret');if(ca)ca.textContent=o?'▾':'▸'}}}});q('ea').onclick=()=>{{document.querySelectorAll('.detail').forEach(d=>d.classList.add('open'));document.querySelectorAll('.caret').forEach(c=>c.textContent='▾')}};q('ca').onclick=()=>{{document.querySelectorAll('.detail').forEach(d=>d.classList.remove('open'));document.querySelectorAll('.caret').forEach(c=>c.textContent='▸')}};q('f').oninput=function(){{let x=this.value.toLowerCase();document.querySelectorAll('[data-search]').forEach(el=>el.classList.toggle('hidden',x&&!el.dataset.search.toLowerCase().includes(x)))}};</script></body></html>"""
def output(repo,root,shows,movies,html):
    root.mkdir(parents=True,exist_ok=True); (root/'Media_Library.html').write_text(html,encoding='utf-8',newline='\n'); (root/'Media_Library.json').write_text(json.dumps({'version':VERSION,'shows':[asdict(s) for s in shows],'movies':[asdict(m) for m in movies]},indent=2,ensure_ascii=False),encoding='utf-8')
    rep=repo/'reports'/'media_library'/datetime.now().strftime('%Y%m%d_%H%M%S'); rep.mkdir(parents=True,exist_ok=True); (rep/'recordings_library.html').write_text(html,encoding='utf-8',newline='\n')
def gen(args):
    repo=Path(args.repo); root=Path(args.media_root); shows,movies=collect(root,repo,args.http_host,int(args.http_port)); h=render(root,shows,movies); output(repo,root,shows,movies,h); print(json.dumps({'html':str(root/'Media_Library.html'),'shows':len(shows),'movies':len(movies),'episodes':sum(s.episode_count for s in shows)},indent=2)); return 0
def selftest(args):
    with tempfile.TemporaryDirectory() as td:
        repo=Path(td)/'repo'; root=Path(td)/'media'; dd=repo/'data'/'catalog_detail'; dd.mkdir(parents=True); (dd/'1.json').write_text(json.dumps({'tmdb_id':1,'title':'Test Show','genres':[{'name':'Drama'}],'seasons':[{'season_number':1,'name':'Season 1','episodes':[{'episode_number':1,'name':'Pilot','air_date':date.today().isoformat(),'runtime':43}]}]}),encoding='utf-8'); d=root/'TV'/'Test Show [1]'/'Season 01'; d.mkdir(parents=True); (d/'Test Show - S01E01 - Pilot.mp4').write_bytes(b'1'); args.repo=str(repo); args.media_root=str(root); gen(args); h=(root/'Media_Library.html').read_text(encoding='utf-8'); assert 'Copy HTTP' in h and 'new 14d' in h and 'data-target' in h; print('self-test passed'); return 0
def main():
    p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='cmd',required=True)
    for n in ['generate','self-test']:
        c=sp.add_parser(n); c.add_argument('--repo',required=True); c.add_argument('--media-root',required=True); c.add_argument('--http-host',default='AJP-Laptop-X1CG10'); c.add_argument('--http-port',default='8010')
    a=p.parse_args(); return gen(a) if a.cmd=='generate' else selftest(a)
if __name__=='__main__': raise SystemExit(main())
