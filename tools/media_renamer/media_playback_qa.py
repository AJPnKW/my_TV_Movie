from __future__ import annotations
import argparse,csv,json,shutil,subprocess,html
from pathlib import Path
from datetime import datetime
EXT={'.mp4','.mkv','.avi','.mov','.m4v','.ts','.mpg','.mpeg','.wmv'}
def tool(n):
    x=shutil.which(n)
    if x: return x
    for p in [Path(r'C:\Utilities\ffmpeg\bin')/(n+'.exe'),Path(r'C:\Utilities\ffmpeg')/(n+'.exe')]:
        if p.exists(): return str(p)
    return ''
def files(root): return sorted([p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in EXT and not any(x in p.parts for x in ['_MediaRenamer_Originals','_MediaRenamer_Duplicates','_MediaRenamer_Quarantine'])],key=lambda p:str(p).lower())
def probe(ff,p):
    if not ff: return {'status':'warning','reason':'ffprobe not found','path':str(p)}
    r=subprocess.run([ff,'-v','error','-show_entries','format=duration,format_name:stream=codec_type,codec_name','-of','json',str(p)],capture_output=True,text=True)
    if r.returncode: return {'status':'error','reason':r.stderr.strip(),'path':str(p)}
    d=json.loads(r.stdout or '{}'); streams=d.get('streams') or []; v=[s for s in streams if s.get('codec_type')=='video']; a=[s for s in streams if s.get('codec_type')=='audio']; fmt=d.get('format') or {}; issues=[]
    if float(fmt.get('duration') or 0)<=0: issues.append('missing duration')
    if not v: issues.append('missing video stream')
    vc=v[0].get('codec_name','') if v else ''; ac=a[0].get('codec_name','') if a else ''
    if p.suffix.lower()=='.mp4' and vc and vc not in {'h264','hevc','mpeg4'}: issues.append('TV-risk video codec '+vc)
    if p.suffix.lower()=='.mp4' and ac and ac not in {'aac','mp3','ac3','eac3'}: issues.append('TV-risk audio codec '+ac)
    return {'status':'error' if issues else 'ok','reason':'; '.join(issues),'path':str(p),'duration':fmt.get('duration',''),'video_codec':vc,'audio_codec':ac,'size_mb':round(p.stat().st_size/1048576,1)}
def report(repo,rows):
    rd=repo/'reports'/'media_playback_qa'/datetime.now().strftime('%Y%m%d_%H%M%S'); rd.mkdir(parents=True,exist_ok=True); fields=['status','reason','path','duration','video_codec','audio_codec','size_mb']
    with (rd/'media_playback_qa.csv').open('w',encoding='utf-8',newline='') as f: wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader(); [wr.writerow({k:r.get(k,'') for k in fields}) for r in rows]
    trs=''.join(f"<tr><td>{html.escape(str(r.get('status','')))}</td><td>{html.escape(str(r.get('reason','')))}</td><td>{html.escape(str(r.get('path','')))}</td></tr>" for r in rows)
    (rd/'media_playback_qa.html').write_text('<html><body><table>'+trs+'</table></body></html>',encoding='utf-8'); return rd
def scan(a):
    repo=Path(a.repo); root=Path(a.media_root); rows=[probe(tool('ffprobe'),p) for p in files(root)]; rd=report(repo,rows); print(json.dumps({'report_dir':str(rd),'files':len(rows),'errors':sum(r['status']=='error' for r in rows)},indent=2)); return 0
def repair(a):
    root=Path(a.media_root); ff=tool('ffmpeg')
    if not ff: raise FileNotFoundError('ffmpeg not found')
    targets=[p for p in files(root) if 'Your Friends' in str(p) and p.suffix.lower()=='.mp4']; b=root/'_MediaRenamer_Originals'/datetime.now().strftime('%Y%m%d_%H%M%S'); results=[]
    for p in targets:
        dst=b/p.relative_to(root); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dst); tmp=p.with_suffix('.remux.tmp.mp4'); r=subprocess.run([ff,'-y','-i',str(p),'-map','0','-c','copy','-movflags','+faststart',str(tmp)],capture_output=True,text=True)
        if r.returncode==0 and tmp.exists(): tmp.replace(p); results.append({'path':str(p),'status':'repaired','backup':str(dst)})
        else: results.append({'path':str(p),'status':'error','reason':r.stderr[-1000:]})
    print(json.dumps({'targets':len(targets),'results':results},indent=2)); return 0
def main():
    p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='cmd',required=True)
    for n in ['scan','repair-known']:
        c=sp.add_parser(n); c.add_argument('--repo',required=True); c.add_argument('--media-root',required=True)
    a=p.parse_args(); return scan(a) if a.cmd=='scan' else repair(a)
if __name__=='__main__': raise SystemExit(main())
