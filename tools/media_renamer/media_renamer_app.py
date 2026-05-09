"""One-screen PySide6 app for safely organizing home recordings."""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from media_catalog_builder import build_media_reference
from media_renamer_engine import DEFAULT_RECORDING_ROOT, ExecutionOptions, PlanItem, execute_plan, run_scan, summarize


APP_NAME = "my_TV_Movie Media Renamer"
APP_VERSION = "0.3.0"


class ScanWorker(QThread):
    progress = Signal(str)
    done = Signal(object, object)
    failed = Signal(str)

    def __init__(self, repo_root: Path, input_root: Path, output_root: Path, workers: int, use_ffprobe: bool, hash_duplicates: bool) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.input_root = input_root
        self.output_root = output_root
        self.workers = workers
        self.use_ffprobe = use_ffprobe
        self.hash_duplicates = hash_duplicates

    def run(self) -> None:
        try:
            build_media_reference(self.repo_root)
            report_dir, items = run_scan(
                self.repo_root,
                self.input_root,
                self.output_root,
                validate_with_ffprobe=self.use_ffprobe,
                detect_hash_duplicates=self.hash_duplicates,
                scan_workers=self.workers,
                progress_callback=self.progress.emit,
            )
            self.done.emit(report_dir, items)
        except Exception as exc:
            self.failed.emit(str(exc))


class ExecuteWorker(QThread):
    progress = Signal(str)
    done = Signal(object, object)
    failed = Signal(str)

    def __init__(self, repo_root: Path, plan_path: Path) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.plan_path = plan_path

    def run(self) -> None:
        try:
            report_dir, rows = execute_plan(ExecutionOptions(repo_root=self.repo_root, plan_json_path=self.plan_path), progress_callback=self.progress.emit)
            self.done.emit(report_dir, rows)
        except Exception as exc:
            self.failed.emit(str(exc))


class MediaRenamerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.repo_root = Path(__file__).resolve().parents[2]
        self.latest_report_dir: Path | None = None
        self.latest_plan_path: Path | None = None
        self.plan_items: list[PlanItem] = []
        self.scan_worker: ScanWorker | None = None
        self.execute_worker: ExecuteWorker | None = None
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1120, 820)
        self.build_ui()
        self.apply_styles()

    def build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setSpacing(12)

        title = QLabel("Media Renamer")
        title.setObjectName("Title")
        layout.addWidget(title)
        statement = QLabel("Safe matches will be fixed automatically. Problem files will be left alone.")
        statement.setObjectName("Statement")
        layout.addWidget(statement)

        self.build_choose_folders(layout)
        self.build_scan_section(layout)
        self.build_fix_section(layout)
        self.build_problem_section(layout)
        self.build_reports_section(layout)
        self.setCentralWidget(root)

    def build_choose_folders(self, parent: QVBoxLayout) -> None:
        box = QGroupBox("1. Choose folders")
        layout = QGridLayout(box)
        self.input_edit = QLineEdit(str(DEFAULT_RECORDING_ROOT))
        self.output_edit = QLineEdit(str(DEFAULT_RECORDING_ROOT))
        layout.addWidget(QLabel("Recordings folder"), 0, 0)
        layout.addWidget(self.input_edit, 0, 1)
        layout.addWidget(self.button("Choose", self.choose_input), 0, 2)
        layout.addWidget(QLabel("Output root"), 1, 0)
        layout.addWidget(self.output_edit, 1, 1)
        layout.addWidget(self.button("Choose", self.choose_output), 1, 2)
        self.advanced_button = self.button("Advanced settings", self.toggle_advanced)
        layout.addWidget(self.advanced_button, 2, 0)
        self.advanced_panel = QWidget()
        advanced = QHBoxLayout(self.advanced_panel)
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 12)
        self.workers_spin.setValue(4)
        self.ffprobe_check = QCheckBox("Check video files with ffprobe")
        self.hash_check = QCheckBox("Hash same-size duplicates")
        advanced.addWidget(QLabel("Scan workers"))
        advanced.addWidget(self.workers_spin)
        advanced.addWidget(self.ffprobe_check)
        advanced.addWidget(self.hash_check)
        advanced.addStretch(1)
        self.advanced_panel.setVisible(False)
        layout.addWidget(self.advanced_panel, 3, 0, 1, 3)
        parent.addWidget(box)

    def build_scan_section(self, parent: QVBoxLayout) -> None:
        box = QGroupBox("2. Scan recordings")
        layout = QVBoxLayout(box)
        row = QHBoxLayout()
        self.scan_button = self.button("Scan Recordings", self.start_scan, primary=True)
        row.addWidget(self.scan_button)
        self.scan_again_button = self.button("Scan Again", self.start_scan)
        self.scan_again_button.setEnabled(False)
        row.addWidget(self.scan_again_button)
        row.addStretch(1)
        layout.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.status_label = QLabel("No scan has run yet.")
        layout.addWidget(self.status_label)
        self.summary_grid = QGridLayout()
        self.summary_labels: dict[str, QLabel] = {}
        for index, name in enumerate(["Ready to fix", "Already OK", "Needs review", "Broken/empty", "Duplicates", "Skipped support files"]):
            label = QLabel("0")
            label.setObjectName("Count")
            self.summary_labels[name] = label
            self.summary_grid.addWidget(QLabel(name), index // 3 * 2, index % 3)
            self.summary_grid.addWidget(label, index // 3 * 2 + 1, index % 3)
        layout.addLayout(self.summary_grid)
        parent.addWidget(box)

    def build_fix_section(self, parent: QVBoxLayout) -> None:
        box = QGroupBox("3. Fix safe changes")
        layout = QHBoxLayout(box)
        self.fix_button = self.button("Fix Safe Changes", self.start_fix, primary=True)
        self.fix_button.setEnabled(False)
        layout.addWidget(self.fix_button)
        self.fix_label = QLabel("Run a scan first.")
        layout.addWidget(self.fix_label, 1)
        parent.addWidget(box)

    def build_problem_section(self, parent: QVBoxLayout) -> None:
        box = QGroupBox("4. Problem files")
        layout = QVBoxLayout(box)
        self.problem_table = QTableWidget(0, 6)
        self.problem_table.setHorizontalHeaderLabels(["Status", "File", "Matched title", "Confidence", "Reason", "Location"])
        self.problem_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.problem_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.problem_table.setAlternatingRowColors(True)
        layout.addWidget(self.problem_table)
        parent.addWidget(box, 1)

    def build_reports_section(self, parent: QVBoxLayout) -> None:
        box = QGroupBox("5. Reports")
        layout = QHBoxLayout(box)
        layout.addWidget(self.button("Open latest report", self.open_latest_report))
        layout.addWidget(self.button("Open reports folder", self.open_reports_folder))
        layout.addWidget(self.button("Export problem list", self.export_problem_list))
        self.report_label = QLabel("Reports will be saved under reports/media_renamer.")
        layout.addWidget(self.report_label, 1)
        parent.addWidget(box)

    def button(self, text: str, callback: Any, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if primary:
            button.setObjectName("PrimaryButton")
        button.clicked.connect(callback)
        return button

    def choose_input(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose recordings folder", self.input_edit.text())
        if selected:
            self.input_edit.setText(selected)

    def choose_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose output root", self.output_edit.text())
        if selected:
            self.output_edit.setText(selected)

    def toggle_advanced(self) -> None:
        self.advanced_panel.setVisible(not self.advanced_panel.isVisible())

    def start_scan(self) -> None:
        input_root = Path(self.input_edit.text()).expanduser()
        output_root = Path(self.output_edit.text()).expanduser()
        if not input_root.exists():
            QMessageBox.warning(self, "Missing folder", f"Recordings folder does not exist:\n{input_root}")
            return
        if not output_root.exists():
            QMessageBox.warning(self, "Missing folder", f"Output root does not exist:\n{output_root}")
            return
        self.scan_button.setEnabled(False)
        self.scan_again_button.setEnabled(False)
        self.fix_button.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Scanning recordings...")
        self.scan_worker = ScanWorker(self.repo_root, input_root, output_root, self.workers_spin.value(), self.ffprobe_check.isChecked(), self.hash_check.isChecked())
        self.scan_worker.progress.connect(self.status_label.setText)
        self.scan_worker.done.connect(self.scan_finished)
        self.scan_worker.failed.connect(self.worker_failed)
        self.scan_worker.start()

    def scan_finished(self, report_dir_object: object, items_object: object) -> None:
        self.scan_button.setEnabled(True)
        self.scan_again_button.setEnabled(True)
        self.progress.setVisible(False)
        self.latest_report_dir = Path(str(report_dir_object))
        self.latest_plan_path = self.latest_report_dir / "scan_plan.json"
        self.plan_items = list(items_object) if isinstance(items_object, list) else []
        summary = summarize(self.plan_items)
        for name, label in self.summary_labels.items():
            label.setText(str(summary.get(name, 0)))
        safe_count = summary.get("Safe actions", 0)
        self.fix_button.setEnabled(safe_count > 0)
        self.fix_label.setText(f"{safe_count} safe changes are ready. Problem files will stay where they are.")
        self.status_label.setText(f"Scan complete. Report: {self.latest_report_dir}")
        self.report_label.setText(str(self.latest_report_dir / "summary.html"))
        self.populate_problem_table()

    def populate_problem_table(self) -> None:
        rows = [item for item in self.plan_items if item.category in {"Needs review", "Broken/empty", "Duplicates"}]
        self.problem_table.setRowCount(0)
        for row_index, item in enumerate(rows):
            self.problem_table.insertRow(row_index)
            values = [item.category, item.original_filename, item.matched_title, str(item.confidence), item.reason, item.source_path]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                self.problem_table.setItem(row_index, col, table_item)

    def start_fix(self) -> None:
        if not self.latest_plan_path or not self.latest_plan_path.exists():
            QMessageBox.warning(self, "No scan plan", "Run Scan Recordings before fixing files.")
            return
        self.fix_button.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Fixing safe changes...")
        self.execute_worker = ExecuteWorker(self.repo_root, self.latest_plan_path)
        self.execute_worker.progress.connect(self.status_label.setText)
        self.execute_worker.done.connect(self.fix_finished)
        self.execute_worker.failed.connect(self.worker_failed)
        self.execute_worker.start()

    def fix_finished(self, report_dir_object: object, rows_object: object) -> None:
        self.progress.setVisible(False)
        rows = list(rows_object) if isinstance(rows_object, list) else []
        self.status_label.setText(f"Safe changes finished. {len(rows)} actions logged.")
        self.fix_label.setText("Safe changes were applied. Click Scan Again to refresh the summary.")
        self.scan_again_button.setEnabled(True)
        self.report_label.setText(str(Path(str(report_dir_object)) / "summary.html"))
        QMessageBox.information(self, "Safe changes finished", f"{len(rows)} safe actions were logged.\nProblem files were left alone.")

    def open_latest_report(self) -> None:
        if not self.latest_report_dir:
            self.latest_report_dir = self.find_latest_report_dir()
        if not self.latest_report_dir:
            QMessageBox.warning(self, "No report", "No media renamer report was found.")
            return
        self.open_path(self.latest_report_dir / "summary.html")

    def open_reports_folder(self) -> None:
        folder = self.repo_root / "reports" / "media_renamer"
        folder.mkdir(parents=True, exist_ok=True)
        self.open_path(folder)

    def export_problem_list(self) -> None:
        if not self.plan_items:
            QMessageBox.warning(self, "No scan", "Run a scan before exporting problem files.")
            return
        report_dir = self.latest_report_dir or (self.repo_root / "reports" / "media_renamer" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
        report_dir.mkdir(parents=True, exist_ok=True)
        output = report_dir / "problem_files.csv"
        rows = [asdict(item) for item in self.plan_items if item.category in {"Needs review", "Broken/empty", "Duplicates"}]
        fields = list(rows[0].keys()) if rows else ["category", "source_path", "reason"]
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        self.open_path(output)

    def find_latest_report_dir(self) -> Path | None:
        root = self.repo_root / "reports" / "media_renamer"
        if not root.exists():
            return None
        dirs = [path for path in root.iterdir() if path.is_dir() and (path / "summary.html").exists()]
        return max(dirs, default=None, key=lambda path: path.name)

    def open_path(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "Missing path", f"Missing:\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def worker_failed(self, message: str) -> None:
        self.scan_button.setEnabled(True)
        self.scan_again_button.setEnabled(True)
        self.fix_button.setEnabled(bool(self.latest_plan_path and self.latest_plan_path.exists()))
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Task failed", message)

    def apply_styles(self) -> None:
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("""
        QMainWindow, QWidget { background:#f8fafc; color:#111827; font-family:Segoe UI,Arial,sans-serif; }
        QLabel#Title { font-size:24px; font-weight:700; }
        QLabel#Statement { font-size:14px; font-weight:600; color:#0f766e; }
        QGroupBox { background:#ffffff; border:1px solid #cbd5e1; border-radius:8px; margin-top:8px; padding:14px; font-weight:700; }
        QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 5px; }
        QLineEdit, QSpinBox { background:#ffffff; border:1px solid #94a3b8; border-radius:6px; padding:7px; }
        QPushButton { background:#e2e8f0; border:1px solid #94a3b8; border-radius:6px; padding:8px 12px; font-weight:600; }
        QPushButton:hover { background:#cbd5e1; }
        QPushButton#PrimaryButton { background:#0f766e; color:white; border-color:#115e59; }
        QPushButton#PrimaryButton:hover { background:#115e59; }
        QPushButton:disabled { color:#94a3b8; background:#f1f5f9; }
        QLabel#Count { font-size:26px; font-weight:700; color:#1e293b; }
        QTableWidget { background:#ffffff; alternate-background-color:#f1f5f9; gridline-color:#e2e8f0; }
        QHeaderView::section { background:#e2e8f0; padding:6px; border:1px solid #cbd5e1; font-weight:700; }
        QProgressBar { border:1px solid #94a3b8; border-radius:6px; height:18px; text-align:center; }
        QProgressBar::chunk { background:#0f766e; border-radius:6px; }
        """)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MediaRenamerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
