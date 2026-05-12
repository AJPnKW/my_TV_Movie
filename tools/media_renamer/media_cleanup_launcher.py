from __future__ import annotations
import subprocess,sys
from pathlib import Path
from PySide6.QtCore import QObject,QRunnable,QThreadPool,Signal,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication,QLabel,QMessageBox,QPushButton,QTextEdit,QVBoxLayout,QHBoxLayout,QWidget
class Sig(QObject): finished=Signal(int,str,str)
class Work(QRunnable):
 def __init__(self,repo,script): super().__init__(); self.repo=repo; self.script=script; self.signals=Sig()
 def run(self):
  cmd=['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.repo/'scripts'/self.script)]; r=subprocess.run(cmd,cwd=str(self.repo),capture_output=True,text=True); out=(r.stdout or '')+('\n'+r.stderr if r.stderr else ''); log=''
  for line in out.splitlines():
   if 'Log:' in line: log=line.split('Log:',1)[1].strip()
  self.signals.finished.emit(r.returncode,out,log)
class App(QWidget):
 def __init__(self):
  super().__init__(); self.repo=Path(__file__).resolve().parents[2]; self.media=Path(r'C:\X1_Share\Recordings'); self.pool=QThreadPool.globalInstance(); self.last=''; self.setWindowTitle('Media Cleanup Hub'); self.resize(980,560)
  lay=QVBoxLayout(); title=QLabel('Media Cleanup Hub'); title.setStyleSheet('font-size:24px;font-weight:900'); lay.addWidget(title); lay.addWidget(QLabel('Run cleanup, generate the library page, start the media server, and test playback.'))
  row=QHBoxLayout();
  for text,script in [('Clean + Generate Library','run_media_cleanup_fast_cycle.ps1'),('Check Only','run_media_cleanup_plan.ps1'),('Generate Library','generate_media_library_page.ps1'),('Playback QA','qa_media_playback.ps1'),('Start HTTP Server','start_media_http_server.ps1')]:
   b=QPushButton(text); b.clicked.connect(lambda _=False,s=script:self.run(s)); row.addWidget(b)
  lay.addLayout(row); row2=QHBoxLayout()
  for text,fn in [('Open Library',self.open_lib),('Open Recordings',self.open_rec),('Open Reports',self.open_reports),('Open Last Log',self.open_log)]:
   b=QPushButton(text); b.clicked.connect(fn); row2.addWidget(b)
  lay.addLayout(row2); self.status=QLabel('Ready'); self.out=QTextEdit(); self.out.setReadOnly(True); lay.addWidget(self.status); lay.addWidget(self.out); self.setLayout(lay); self.setStyleSheet('QWidget{background:#050914;color:#f2f6ff;font-family:Segoe UI;font-size:13px}QPushButton{background:#132441;border:1px solid #274166;border-radius:8px;padding:8px;font-weight:700}QTextEdit{background:#07101f;border:1px solid #263b5f;border-radius:8px;font-family:Consolas}')
 def run(self,s): self.status.setText('Running '+s); w=Work(self.repo,s); w.signals.finished.connect(self.done); self.pool.start(w)
 def done(self,code,out,log):
  self.out.append(out); self.last=log or self.last; self.status.setText('Finished' if code==0 else 'Failed')
  if code!=0:
   m=QMessageBox(self); m.setWindowTitle('Run failed'); m.setText('The run did not finish successfully.'); m.setInformativeText('Log: '+(self.last or 'No log path found')); ob=m.addButton('Open Log',QMessageBox.ActionRole); m.addButton(QMessageBox.Ok); m.exec();
   if m.clickedButton() is ob: self.open_log()
 def open(self,p): QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
 def open_lib(self): self.open(self.media/'Media_Library.html')
 def open_rec(self): self.open(self.media)
 def open_reports(self): self.open(self.repo/'reports')
 def open_log(self):
  if self.last: self.open(Path(self.last))
def main(): app=QApplication(sys.argv); w=App(); w.show(); return app.exec()
if __name__=='__main__': raise SystemExit(main())
