# FILE: tools/media_renamer/media_cleanup_launcher.py
# VERSION: v0.6.8
# UPDATED: 2026-05-11
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout


REPO_ROOT = Path(__file__).resolve().parents[2]


class WorkerSignals(QObject):
    finished = Signal(int, str)


class CommandWorker(QRunnable):
    def __init__(self, command: list[str]) -> None:
        super().__init__()
        self.command = [str(x) for x in command]
        self.signals = WorkerSignals()

    def run(self) -> None:
        completed = subprocess.run(self.command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
        output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        self.signals.finished.emit(completed.returncode, output)


class MediaCleanupWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.pool = QThreadPool.globalInstance()
        self.setWindowTitle("Media Cleanup Hub")
        self.resize(980, 620)
        self.status = QLabel("Ready")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.clean_button = QPushButton("Clean + QA + Generate Library")
        self.check_button = QPushButton("Check Naming Only")
        self.library_button = QPushButton("Generate Media Library")
        self.qa_button = QPushButton("QA Playback")
        self.repair_button = QPushButton("Repair Playback Issues")
        self.open_button = QPushButton("Open Media Library")
        self.server_button = QPushButton("Start Network Media Page")
        self.report_button = QPushButton("Open Reports Folder")
        self.clean_button.clicked.connect(lambda: self.run_script("run_media_cleanup_integrated.ps1", "Clean + QA + Generate Library"))
        self.check_button.clicked.connect(lambda: self.run_script("run_media_cleanup_plan.ps1", "Check Naming Only"))
        self.library_button.clicked.connect(lambda: self.run_script("generate_media_library_page.ps1", "Generate Media Library"))
        self.qa_button.clicked.connect(lambda: self.run_script("qa_media_playback.ps1", "QA Playback"))
        self.repair_button.clicked.connect(lambda: self.run_script("repair_media_playback.ps1", "Repair Playback Issues"))
        self.open_button.clicked.connect(self.open_library)
        self.server_button.clicked.connect(lambda: self.run_script("start_media_http_server.ps1", "Start Network Media Page"))
        self.report_button.clicked.connect(self.open_reports)
        layout = QVBoxLayout()
        title = QLabel("Media Cleanup Hub")
        title.setObjectName("title")
        subtitle = QLabel("One process: clean names, validate media files, repair playback issues, and generate the local library page.")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        row1 = QHBoxLayout(); row1.addWidget(self.clean_button); row1.addWidget(self.check_button); row1.addWidget(self.library_button)
        row2 = QHBoxLayout(); row2.addWidget(self.qa_button); row2.addWidget(self.repair_button); row2.addWidget(self.server_button)
        row3 = QHBoxLayout(); row3.addWidget(self.open_button); row3.addWidget(self.report_button)
        layout.addLayout(row1); layout.addLayout(row2); layout.addLayout(row3); layout.addWidget(self.status); layout.addWidget(self.output)
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget { background:#06101f; color:#f4f7ff; font:14px 'Segoe UI'; }
            QLabel#title { font-size:34px; font-weight:900; letter-spacing:2px; }
            QPushButton { background:#14284c; border:1px solid #2b4a7c; border-radius:10px; color:#fff; padding:12px; font-weight:800; }
            QPushButton:hover { border-color:#78e8ff; }
            QTextEdit { background:#020812; border:1px solid #1f3156; border-radius:10px; font-family:Consolas; }
        """)

    def set_busy(self, busy: bool) -> None:
        for button in [self.clean_button, self.check_button, self.library_button, self.qa_button, self.repair_button, self.server_button]:
            button.setEnabled(not busy)

    def run_script(self, script_name: str, label: str) -> None:
        self.set_busy(True)
        self.status.setText(f"Running: {label}")
        self.output.append(f"\nSTART: {label}\n")
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(REPO_ROOT / "scripts" / script_name)]
        worker = CommandWorker(command)
        worker.signals.finished.connect(lambda code, out: self.command_finished(label, code, out))
        self.pool.start(worker)

    def command_finished(self, label: str, code: int, output: str) -> None:
        self.output.append(output)
        self.output.append(f"\nFINISHED: {label}; exit code {code}\n")
        self.status.setText("Ready" if code == 0 else f"Failed: {label}")
        self.set_busy(False)

    def open_library(self) -> None:
        subprocess.Popen(["explorer", r"C:\X1_Share\Recordings\Media_Library.html"])

    def open_reports(self) -> None:
        subprocess.Popen(["explorer", str(REPO_ROOT / "reports")])


def main() -> int:
    app = QApplication(sys.argv)
    window = MediaCleanupWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
