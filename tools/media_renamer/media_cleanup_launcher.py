# FILE: tools/media_renamer/media_cleanup_launcher.py
# VERSION: v0.4.0
# CHANGE NOTES:
# - Optional two-button PySide6 launcher for the media cleanup pipeline.
# - No tabs, no row approval, no technical maintenance workflow.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget


class WorkerSignals(QObject):
    finished = Signal(int, str)


class CommandWorker(QRunnable):
    def __init__(self, command: list[str]) -> None:
        super().__init__()
        self.command = command
        self.signals = WorkerSignals()

    def run(self) -> None:
        completed = subprocess.run(self.command, check=False, capture_output=True, text=True)
        output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        self.signals.finished.emit(completed.returncode, output)


class MediaCleanupWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.repo_root = Path(__file__).resolve().parents[2]
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("Media Cleanup")
        self.resize(920, 620)
        self.media_root = QLineEdit(r"C:\X1_Share\Recordings")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.plan_button = QPushButton("1. Build Cleanup Plan")
        self.apply_button = QPushButton("2. Apply Cleanup Plan")
        self.report_button = QPushButton("Open Reports Folder")
        self.apply_button.setEnabled(True)
        choose_button = QPushButton("Choose Folder")
        choose_button.clicked.connect(self.choose_folder)
        self.plan_button.clicked.connect(self.run_plan)
        self.apply_button.clicked.connect(self.run_apply)
        self.report_button.clicked.connect(self.open_reports)
        top = QLabel("Safe matches will be fixed automatically. Problem files will be left alone.")
        top.setStyleSheet("font-size: 18px; font-weight: 700; padding: 8px;")
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Recordings folder:"))
        folder_row.addWidget(self.media_root)
        folder_row.addWidget(choose_button)
        button_row = QHBoxLayout()
        button_row.addWidget(self.plan_button)
        button_row.addWidget(self.apply_button)
        button_row.addWidget(self.report_button)
        layout = QVBoxLayout()
        layout.addWidget(top)
        layout.addLayout(folder_row)
        layout.addLayout(button_row)
        layout.addWidget(QLabel("Result summary:"))
        layout.addWidget(self.output)
        self.setLayout(layout)
        self.setStyleSheet("QPushButton { font-size: 16px; padding: 12px; } QLineEdit { padding: 8px; } QTextEdit { font-family: Consolas; }")

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose recordings folder", self.media_root.text())
        if folder:
            self.media_root.setText(folder)

    def run_command(self, mode: str) -> None:
        command = [
            sys.executable,
            str(self.repo_root / "tools" / "media_renamer" / "media_cleanup_pipeline.py"),
            mode,
            "--repo-root",
            str(self.repo_root),
            "--media-root",
            self.media_root.text(),
        ]
        self.output.append(f"Running {mode}...\n")
        worker = CommandWorker(command)
        worker.signals.finished.connect(self.command_finished)
        self.thread_pool.start(worker)

    def run_plan(self) -> None:
        self.run_command("plan")

    def run_apply(self) -> None:
        self.run_command("apply")

    def command_finished(self, return_code: int, output: str) -> None:
        self.output.append(output)
        self.output.append(f"\nFinished with exit code {return_code}.\n")

    def open_reports(self) -> None:
        reports = self.repo_root / "reports" / "media_renamer"
        reports.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(reports)])


def main() -> int:
    app = QApplication(sys.argv)
    window = MediaCleanupWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
