# ==============================================================================
# [FILE]    inputs_gui_app.py
# [PROJECT] my_TV_Movie
# [ROLE]    PySide6 GUI to manage data/inputs.json (TMDB search + list management)
# [VERSION] v0.2.4
# [UPDATED] 2026-02-25T00:00:00Z
#
# [CHANGELOG]
# - v0.2.4: immediate-write mode (no Save button; edits persist to disk instantly)
# - v0.2.3: header-toggle select all, seasons icon-in-cell, local-poster/date UX fixes
# - v0.2.2: duplicate-safe row selection/deletion by item refs; clearer selection header
# - v0.2.1: async TMDB search worker, sort-safe table/item mapping, cached poster pixmaps
# - v0.2.0: 2-column layout (Search | Library), selection column + bulk actions,
#           sort/filter, status+poster, save/reload confirmations, detail panel enriched
# - v0.1.0: initial GUI
# ==============================================================================
from __future__ import annotations

import os
import subprocess
import sys
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from PySide6 import QtCore, QtGui, QtWidgets

try:
    from .inputs_gui_model import InputsItem, InputsModel
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from inputs_gui_model import InputsItem, InputsModel


APP_TITLE = "my_TV_Movie • Inputs Editor (GUI)"
APP_VERSION = "v0.2.5"

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w342"
ItemRef = int


def tmdb_search(api_key: str, kind: str, query: str) -> List[Dict[str, Any]]:
    url = f"{TMDB_BASE}/search/{kind}"
    params = {"api_key": api_key, "query": query, "include_adult": "false"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json() or {}
    out: List[Dict[str, Any]] = []
    for x in data.get("results", []) or []:
        title = x.get("name") if kind == "tv" else x.get("title")
        date = x.get("first_air_date") if kind == "tv" else x.get("release_date")
        year = str(date)[:4] if date else ""
        season_date = x.get("last_air_date") if kind == "tv" else None
        poster_rel = str(x.get("poster_path") or "").strip()
        out.append(
            {
                "kind": kind,
                "tmdb_id": int(x.get("id")),
                "title": str(title or "").strip(),
                "year": year,
                "original_date": str(date or ""),
                "season_date": str(season_date or ""),
                "poster_rel": poster_rel,
                "popularity": float(x.get("popularity") or 0.0),
            }
        )
    return out


class TmdbSearchWorker(QtCore.QObject):
    resultsReady = QtCore.Signal(list)
    error = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, api_key: str, kind: str, query: str) -> None:
        super().__init__()
        self._api_key = api_key
        self._kind = kind
        self._query = query

    @QtCore.Slot()
    def run(self) -> None:
        try:
            results = tmdb_search(self._api_key, self._kind, self._query)
            self.resultsReady.emit(results)
        except Exception as ex:
            self.error.emit(str(ex)[:300])
        finally:
            self.finished.emit()


class MultiSelectComboBox(QtWidgets.QComboBox):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setModel(QtGui.QStandardItemModel(self))
        self.view().pressed.connect(self._on_pressed)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Select seasons")
        self._refresh_text()

    def add_check_item(self, text: str, checked: bool = False) -> None:
        item = QtGui.QStandardItem(text)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
        item.setData(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)
        self.model().appendRow(item)
        self._refresh_text()

    def _on_pressed(self, index: QtCore.QModelIndex) -> None:
        item = self.model().itemFromIndex(index)
        if not item:
            return
        cur = item.data(QtCore.Qt.CheckStateRole)
        item.setData(QtCore.Qt.Unchecked if cur == QtCore.Qt.Checked else QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)
        self._refresh_text()

    def selected_numbers(self) -> List[int]:
        out: List[int] = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item and item.data(QtCore.Qt.CheckStateRole) == QtCore.Qt.Checked:
                txt = str(item.text()).strip()
                if txt.isdigit():
                    out.append(int(txt))
        return sorted(set(out))

    def _refresh_text(self) -> None:
        vals = [str(x) for x in self.selected_numbers()]
        self.lineEdit().setText(",".join(vals) if vals else "")


class SeasonsDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget, item: InputsItem, available_seasons: Optional[List[int]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Seasons")
        self.setModal(True)
        self._item = item
        self._available = sorted(set(int(x) for x in (available_seasons or []) if isinstance(x, int) and x >= 0))
        self._included = self._included_from_item(item.seasons)
        merged = sorted(set(self._available + self._included))

        self.all_radio = QtWidgets.QRadioButton("All")
        self.start_radio = QtWidgets.QRadioButton("Start +")
        self.list_radio = QtWidgets.QRadioButton("Listing")
        self.mode_group = QtWidgets.QButtonGroup(self)
        self.mode_group.addButton(self.all_radio)
        self.mode_group.addButton(self.start_radio)
        self.mode_group.addButton(self.list_radio)

        self.start_combo = QtWidgets.QComboBox()
        for n in merged:
            self.start_combo.addItem(str(n), n)
        if self.start_combo.count() == 0:
            self.start_combo.addItem("1", 1)

        self.list_combo = MultiSelectComboBox()
        for n in merged:
            self.list_combo.add_check_item(str(n), checked=(n in self._included))

        self.available_lbl = QtWidgets.QLabel(f"Available seasons: {', '.join(str(x) for x in self._available) if self._available else 'unknown'}")
        self.included_lbl = QtWidgets.QLabel(f"Included seasons: {', '.join(str(x) for x in self._included) if self._included else 'ALL'}")

        options = QtWidgets.QFormLayout()
        options.addRow(self.available_lbl)
        options.addRow(self.included_lbl)
        options.addRow(self.all_radio)
        options.addRow(self.start_radio, self.start_combo)
        options.addRow(self.list_radio, self.list_combo)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(options)
        layout.addWidget(btns)

        self._apply_initial_state(item.seasons)
        self.mode_group.buttonClicked.connect(lambda _btn: self._mode_changed())
        self._mode_changed()

    def _mode_changed(self) -> None:
        self.start_combo.setEnabled(self.start_radio.isChecked())
        self.list_combo.setEnabled(self.list_radio.isChecked())

    def result_value(self) -> Any:
        if self.all_radio.isChecked():
            return None
        if self.start_radio.isChecked():
            return {"start": int(self.start_combo.currentData() or 1), "future": True}
        vals = self.list_combo.selected_numbers()
        return vals if vals else []

    def _included_from_item(self, seasons: Any) -> List[int]:
        if isinstance(seasons, list):
            out = []
            for x in seasons:
                try:
                    out.append(int(x))
                except Exception:
                    pass
            return sorted(set(out))
        if isinstance(seasons, dict):
            try:
                return [int(seasons.get("start") or seasons.get("nplus") or 1)]
            except Exception:
                return []
        return []

    def _apply_initial_state(self, seasons: Any) -> None:
        if seasons in (None, "all", "*"):
            self.all_radio.setChecked(True)
            return
        if isinstance(seasons, dict):
            start = int(seasons.get("start") or seasons.get("nplus") or 1)
            idx = self.start_combo.findData(start)
            if idx >= 0:
                self.start_combo.setCurrentIndex(idx)
            self.start_radio.setChecked(True)
            return
        if isinstance(seasons, list):
            self.list_radio.setChecked(True)
            return
        self.all_radio.setChecked(True)


class MainWindow(QtWidgets.QMainWindow):
    COL_SELECT = 0
    COL_IN_SCOPE = 1
    COL_KIND = 2
    COL_POSTER = 3
    COL_TITLE = 4
    COL_TMDB_ID = 5
    COL_STATUS = 6
    COL_SEASONS = 7

    HEADERS = ["Select", "In scope", "Type", "Poster", "Title", "TMDB ID", "Status", "Seasons"]

    def __init__(self, repo_root: Path, inputs_path: Path, tmdb_key: str) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.inputs_path = inputs_path
        self.tmdb_key = tmdb_key

        self.model = InputsModel(repo_root=repo_root, inputs_path=inputs_path)
        self.model.load_inputs()

        self._dirty = False
        self._search_results: List[Dict[str, Any]] = []
        self._search_checked_keys: set[Tuple[str, int]] = set()
        self._search_thread: Optional[QtCore.QThread] = None
        self._search_worker: Optional[TmdbSearchWorker] = None
        self._poster_pixmap_cache: Dict[Tuple[str, int, int], QtGui.QPixmap] = {}
        self._header_filter_values: Dict[int, str] = {}
        self._suggestions_results: List[Dict[str, Any]] = []
        self._updating_search_checks = False

        self.setWindowTitle(f"{APP_TITLE} • {APP_VERSION}")
        self.resize(1300, 760)

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        tabs = QtWidgets.QTabWidget()
        outer.addWidget(tabs)

        inputs_tab = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(inputs_tab)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        left = self._build_search_panel()
        right = self._build_library_panel()
        grid.addWidget(left, 0, 0)
        grid.addWidget(right, 0, 1)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 9)

        tools_tab = QtWidgets.QWidget()
        tools_layout = QtWidgets.QVBoxLayout(tools_tab)
        self.tools_out = QtWidgets.QPlainTextEdit()
        self.tools_out.setReadOnly(True)
        btns = QtWidgets.QHBoxLayout()
        self.btn_git_status = QtWidgets.QPushButton("Git status")
        self.btn_git_fetch = QtWidgets.QPushButton("Git fetch")
        self.btn_git_pull = QtWidgets.QPushButton("Git pull")
        self.btn_git_push = QtWidgets.QPushButton("Git push")
        self.btn_git_push_remote = QtWidgets.QPushButton("Push to remote…")
        self.btn_dedupe = QtWidgets.QPushButton("Dedup by key")
        self.btn_bulk_spec = QtWidgets.QPushButton("Bulk season_spec")
        self.btn_poster_audit = QtWidgets.QPushButton("Poster audit")
        self.btn_fetch_missing_posters = QtWidgets.QPushButton("Fetch missing posters")
        self.btn_data_audit = QtWidgets.QPushButton("Data/asset audit")
        self.btn_episode_dup_audit = QtWidgets.QPushButton("Episode dup audit")
        self.btn_episode_dup_fix = QtWidgets.QPushButton("Fix episode dups")
        self.btn_git_security_diag = QtWidgets.QPushButton("Git security diagnostics")
        self.btn_tools_clear = QtWidgets.QPushButton("Clear output")
        self.btn_git_status.clicked.connect(self._tool_git_status)
        self.btn_git_fetch.clicked.connect(self._tool_git_fetch)
        self.btn_git_pull.clicked.connect(self._tool_git_pull)
        self.btn_git_push.clicked.connect(self._tool_git_push)
        self.btn_git_push_remote.clicked.connect(self._tool_git_push_remote)
        self.btn_dedupe.clicked.connect(self._tool_dedup)
        self.btn_bulk_spec.clicked.connect(self._tool_bulk_season_spec)
        self.btn_poster_audit.clicked.connect(self._tool_poster_audit)
        self.btn_fetch_missing_posters.clicked.connect(self._tool_fetch_missing_posters)
        self.btn_data_audit.clicked.connect(self._tool_data_audit)
        self.btn_episode_dup_audit.clicked.connect(self._tool_episode_dup_audit)
        self.btn_episode_dup_fix.clicked.connect(self._tool_episode_dup_fix)
        self.btn_git_security_diag.clicked.connect(self._tool_git_security_diag)
        self.btn_tools_clear.clicked.connect(self.tools_out.clear)
        for b in [
            self.btn_git_status,
            self.btn_git_fetch,
            self.btn_git_pull,
            self.btn_git_push,
            self.btn_git_push_remote,
            self.btn_git_security_diag,
            self.btn_dedupe,
            self.btn_bulk_spec,
            self.btn_poster_audit,
            self.btn_fetch_missing_posters,
            self.btn_data_audit,
            self.btn_episode_dup_audit,
            self.btn_episode_dup_fix,
            self.btn_tools_clear,
        ]:
            btns.addWidget(b)
        tools_layout.addLayout(btns)
        tools_layout.addWidget(self.tools_out)
        tools_layout.addStretch(1)

        sugg_tab = QtWidgets.QWidget()
        sugg_layout = QtWidgets.QVBoxLayout(sugg_tab)
        top = QtWidgets.QHBoxLayout()
        self.sugg_kind = QtWidgets.QComboBox()
        self.sugg_kind.addItems(["TV", "Movie"])
        self.sugg_mode = QtWidgets.QComboBox()
        self.sugg_mode.addItems(["Trending", "Popular", "New", "Upcoming"])
        self.sugg_lang_en = QtWidgets.QCheckBox("English only")
        self.sugg_lang_en.setChecked(True)
        self.sugg_exclude_kids = QtWidgets.QCheckBox("Exclude kids/animation")
        self.sugg_refresh = QtWidgets.QPushButton("Load suggestions")
        self.sugg_add_selected = QtWidgets.QPushButton("Add selected suggestion")
        self.sugg_add_selected.setEnabled(False)
        self.sugg_refresh.clicked.connect(self._load_suggestions)
        self.sugg_add_selected.clicked.connect(self._add_selected_suggestion)
        for w in [self.sugg_kind, self.sugg_mode, self.sugg_lang_en, self.sugg_exclude_kids, self.sugg_refresh, self.sugg_add_selected]:
            top.addWidget(w)
        top.addStretch(1)
        sugg_layout.addLayout(top)
        self.sugg_table = QtWidgets.QTableWidget()
        self.sugg_table.setColumnCount(7)
        self.sugg_table.setHorizontalHeaderLabels(["Poster", "Title", "Type", "Date", "Score", "In list", "Add"])
        self.sugg_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.sugg_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.sugg_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.sugg_table.setAlternatingRowColors(True)
        self.sugg_table.setStyleSheet("QTableView::item:selected { color: white; }")
        self.sugg_table.currentCellChanged.connect(lambda r, _c, _pr, _pc: self._suggestion_selected(r))
        sh = self.sugg_table.horizontalHeader()
        sh.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        sh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        sh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        self.sugg_table.setColumnWidth(0, 70)
        self.sugg_table.setIconSize(QtCore.QSize(44, 66))
        sugg_layout.addWidget(self.sugg_table, 2)
        self.sugg_detail = QtWidgets.QTextEdit()
        self.sugg_detail.setReadOnly(True)
        sugg_layout.addWidget(self.sugg_detail, 1)

        tabs.addTab(inputs_tab, "Inputs")
        tabs.addTab(tools_tab, "Tools")
        tabs.addTab(sugg_tab, "Suggestions")

        self._refresh_library_table()

    def _build_search_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox("Find on TMDB")
        v = QtWidgets.QVBoxLayout(box)

        top = QtWidgets.QHBoxLayout()
        self.search_text = QtWidgets.QLineEdit()
        self.search_text.setPlaceholderText("Search TMDB… (title)")
        self.search_kind = QtWidgets.QComboBox()
        self.search_kind.addItems(["TV", "Movie"])
        self.search_btn = QtWidgets.QPushButton("Search")
        self.search_btn.clicked.connect(self._do_search)
        self.search_text.returnPressed.connect(self._do_search)

        top.addWidget(self.search_text, 1)
        top.addWidget(self.search_kind)
        top.addWidget(self.search_btn)
        v.addLayout(top)

        sortrow = QtWidgets.QHBoxLayout()
        self.search_sort = QtWidgets.QComboBox()
        self.search_sort.addItems(
            [
                "A→Z",
                "Z→A",
                "Release date (new→old)",
                "Release date (old→new)",
                "Season date (new→old)",
                "Season date (old→new)",
            ]
        )
        self.search_sort.currentIndexChanged.connect(self._render_search_results)
        sortrow.addWidget(QtWidgets.QLabel("Sort:"))
        sortrow.addWidget(self.search_sort)
        sortrow.addStretch(1)
        v.addLayout(sortrow)

        self.search_status = QtWidgets.QLabel("")
        v.addWidget(self.search_status)

        self.search_list = QtWidgets.QListWidget()
        self.search_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.search_list.setStyleSheet("QListWidget::item:selected { color: white; }")
        self.search_list.currentRowChanged.connect(self._search_selection_changed)
        self.search_list.itemChanged.connect(self._on_search_item_changed)
        self.search_list.itemClicked.connect(self._on_search_item_clicked)
        v.addWidget(self.search_list, 1)

        self.search_detail = QtWidgets.QGroupBox("Selected")
        dv = QtWidgets.QVBoxLayout(self.search_detail)
        self.search_detail_title = QtWidgets.QLabel("—")
        self.search_detail_title.setWordWrap(True)
        self.search_detail_meta = QtWidgets.QLabel("")
        self.search_detail_meta.setWordWrap(True)
        self.search_detail_poster = QtWidgets.QLabel("")
        self.search_detail_poster.setFixedHeight(180)
        self.search_detail_poster.setAlignment(QtCore.Qt.AlignCenter)
        self.search_detail_poster.setStyleSheet("border:1px solid #333; border-radius:6px;")
        dv.addWidget(self.search_detail_title)
        dv.addWidget(self.search_detail_meta)
        dv.addWidget(self.search_detail_poster)
        v.addWidget(self.search_detail)

        self.add_btn = QtWidgets.QPushButton("Add selected")
        self.add_btn.clicked.connect(self._add_selected_search_result)
        self.add_btn.setEnabled(False)
        v.addWidget(self.add_btn)

        return box

    def _build_library_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox("My Listing (data/inputs.json)")
        v = QtWidgets.QVBoxLayout(box)

        header = QtWidgets.QHBoxLayout()
        self.count_lbl = QtWidgets.QLabel("")
        self.reload_btn = QtWidgets.QPushButton("Reload")
        self.reload_btn.clicked.connect(self._reload_inputs)
        header.addWidget(self.count_lbl)
        header.addStretch(1)
        header.addWidget(self.reload_btn)
        v.addLayout(header)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setStyleSheet("QTableView::item:selected { color: white; }")
        self.table.itemSelectionChanged.connect(self._library_selection_changed)
        self.table.cellDoubleClicked.connect(self._library_cell_double_clicked)
        self.table.itemChanged.connect(self._on_table_item_changed)

        hdr = self.table.horizontalHeader()
        hdr.sectionClicked.connect(self._on_table_header_clicked)
        hdr.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        hdr.customContextMenuRequested.connect(self._on_header_filter_menu)
        hdr.setSectionResizeMode(self.COL_SELECT, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_IN_SCOPE, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_KIND, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_POSTER, QtWidgets.QHeaderView.Fixed)
        hdr.setSectionResizeMode(self.COL_TITLE, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(self.COL_TMDB_ID, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_STATUS, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_SEASONS, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(self.COL_POSTER, 56)
        self.table.setColumnWidth(self.COL_SEASONS, 110)
        self.table.setIconSize(QtCore.QSize(44, 66))
        self._update_header_filter_labels()

        v.addWidget(self.table, 1)

        actions = QtWidgets.QHBoxLayout()
        self.btn_toggle_scope = QtWidgets.QPushButton("Toggle in-scope")
        self.btn_toggle_scope.clicked.connect(self._bulk_toggle_scope)

        self.btn_delete = QtWidgets.QPushButton("Delete selected")
        self.btn_delete.clicked.connect(self._bulk_delete)

        actions.addWidget(self.btn_toggle_scope)
        actions.addWidget(self.btn_delete)
        actions.addStretch(1)
        v.addLayout(actions)

        self.detail = QtWidgets.QGroupBox("Details")
        dv = QtWidgets.QHBoxLayout(self.detail)

        self.detail_poster = QtWidgets.QLabel("")
        self.detail_poster.setFixedSize(120, 180)
        self.detail_poster.setAlignment(QtCore.Qt.AlignCenter)
        self.detail_poster.setStyleSheet("border:1px solid #333; border-radius:6px;")

        self.detail_text = QtWidgets.QTextEdit()
        self.detail_text.setReadOnly(True)

        dv.addWidget(self.detail_poster)
        dv.addWidget(self.detail_text, 1)
        v.addWidget(self.detail)

        self.path_lbl = QtWidgets.QLabel(f"Loaded: {str(self.inputs_path)}")
        v.addWidget(self.path_lbl)

        return box

    def _do_search(self) -> None:
        if self._search_thread is not None:
            return
        q = self.search_text.text().strip()
        if not q:
            return
        kind = "tv" if self.search_kind.currentText() == "TV" else "movie"
        self._set_search_busy(True)

        thread = QtCore.QThread(self)
        worker = TmdbSearchWorker(api_key=self.tmdb_key, kind=kind, query=q)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.resultsReady.connect(self._on_search_results)
        worker.error.connect(self._on_search_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(self._on_search_finished)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_search_thread_state)

        self._search_thread = thread
        self._search_worker = worker
        thread.start()

    def _set_search_busy(self, busy: bool) -> None:
        self.search_btn.setEnabled(not busy)
        self.search_text.setEnabled(not busy)
        self.search_kind.setEnabled(not busy)
        self.search_sort.setEnabled(not busy)
        self.search_btn.setText("Searching..." if busy else "Search")
        self.search_status.setText("Search in progress..." if busy else "")
        if busy:
            self.add_btn.setEnabled(False)

    def _clear_search_thread_state(self) -> None:
        self._search_thread = None
        self._search_worker = None

    def _on_search_results(self, results: list) -> None:
        self._search_results = results if isinstance(results, list) else []

    def _on_search_error(self, err: str) -> None:
        self._search_results = []
        QtWidgets.QMessageBox.critical(self, "TMDB search failed", err)

    def _on_search_finished(self) -> None:
        self._set_search_busy(False)
        self._render_search_results()

    def _render_search_results(self) -> None:
        items = list(self._search_results)
        mode = self.search_sort.currentText()
        def _d(val: str) -> str:
            return str(val or "")

        if mode == "A→Z":
            items.sort(key=lambda x: (x["title"].lower(), x["tmdb_id"]))
        elif mode == "Z→A":
            items.sort(key=lambda x: (x["title"].lower(), x["tmdb_id"]), reverse=True)
        elif mode == "Release date (new→old)":
            items.sort(key=lambda x: (_d(x.get("original_date")), x["title"].lower()), reverse=True)
        elif mode == "Release date (old→new)":
            items.sort(key=lambda x: (_d(x.get("original_date")) or "9999-99-99", x["title"].lower()))
        elif mode == "Season date (new→old)":
            items.sort(
                key=lambda x: (1 if _d(x.get("season_date")) else 0, _d(x.get("season_date")), x["title"].lower()),
                reverse=True,
            )
        else:
            items.sort(
                key=lambda x: (0 if _d(x.get("season_date")) else 1, _d(x.get("season_date")) or "9999-99-99", x["title"].lower())
            )

        self.search_list.clear()
        for r in items:
            key = self.model.item_key(r["kind"], int(r["tmdb_id"]))
            d1 = r.get("original_date") or "—"
            d2 = r.get("season_date") or "—"
            state_icon = self._search_state_icon(r["kind"], int(r["tmdb_id"]))
            item = QtWidgets.QListWidgetItem(f"{state_icon} {r['title']}  •  orig:{d1}  •  season:{d2}  •  id={r['tmdb_id']}")
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if key in self._search_checked_keys else QtCore.Qt.Unchecked)
            item.setData(QtCore.Qt.UserRole, key)
            self.search_list.addItem(item)
        self.search_list.setCurrentRow(0 if self.search_list.count() else -1)
        self._search_results = items
        self._sync_search_add_state()

    def _search_selection_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._search_results):
            self.search_detail_title.setText("—")
            self.search_detail_meta.setText("")
            self.search_detail_poster.setText("")
            self.search_detail_poster.setPixmap(QtGui.QPixmap())
            return
        r = self._search_results[row]
        key = self.model.item_key(r["kind"], int(r["tmdb_id"]))
        self._set_single_search_checked_key(key)
        self._sync_search_add_state()
        self._ensure_local_poster_for_result(r)
        self.search_detail_title.setText(r["title"])
        self.search_detail_meta.setText(
            f"Type: {r['kind']}\nOriginal date: {r.get('original_date') or '—'}\n"
            f"Season date: {r.get('season_date') or '—'}\nTMDB ID: {r['tmdb_id']}"
        )
        pix = self._load_local_poster_pixmap(r["kind"], r["tmdb_id"], max_w=220, max_h=180)
        if pix:
            self.search_detail_poster.setText("")
            self.search_detail_poster.setPixmap(pix)
        else:
            self.search_detail_poster.setPixmap(QtGui.QPixmap())
            self.search_detail_poster.setText("No local poster yet")

    def _add_selected_search_result(self) -> None:
        checked = self._get_checked_search_results()
        if len(checked) != 1:
            return
        r = checked[0]
        if self._has_item(r["kind"], r["tmdb_id"]):
            QtWidgets.QMessageBox.information(self, "Already exists", "That item is already in your inputs.json list.")
            return

        it = InputsItem(kind=r["kind"], tmdb_id=int(r["tmdb_id"]), title=str(r["title"]), in_scope=True)
        if it.kind == "tv":
            dlg = SeasonsDialog(self, it)
            if dlg.exec() != QtWidgets.QDialog.Accepted:
                return
            it.seasons = dlg.result_value()
        self.model.items.append(it)
        self.model.items.sort(key=lambda x: (x.kind, x.title.lower(), x.tmdb_id))
        self.model.refresh_enrichment()
        self.model.reindex_items()
        self._poster_pixmap_cache.clear()
        if not self._save_model_now():
            return
        self._set_dirty(False)
        self._refresh_library_table()
        self._select_row_by_item_ref(self.model.item_ref(it))
        QtWidgets.QMessageBox.information(self, "Added", f"Added: {it.title} (id={it.tmdb_id})")
        self._render_search_results()

    def _search_state_icon(self, kind: str, tmdb_id: int) -> str:
        matches = self.model.get_all_by_key((kind, tmdb_id))
        if not matches:
            return "⬜"
        if any(not it.in_scope for it in matches):
            return "🟧"
        return "✅"

    def _sync_search_add_state(self) -> None:
        self.add_btn.setEnabled(len(self._get_checked_search_results()) == 1)

    def _on_search_item_changed(self, item: QtWidgets.QListWidgetItem) -> None:
        if self._updating_search_checks:
            return
        data = item.data(QtCore.Qt.UserRole)
        if not isinstance(data, tuple) or len(data) != 2:
            return
        key = self.model.item_key(str(data[0]), int(data[1]))
        if item.checkState() == QtCore.Qt.Checked:
            self._set_single_search_checked_key(key)
        else:
            self._search_checked_keys.discard(key)
            self._sync_search_add_state()

    def _on_search_item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        row = self.search_list.row(item)
        if row >= 0:
            self.search_list.setCurrentRow(row)
            data = item.data(QtCore.Qt.UserRole)
            if isinstance(data, tuple) and len(data) == 2:
                self._set_single_search_checked_key(self.model.item_key(str(data[0]), int(data[1])))

    def _set_single_search_checked_key(self, key: Optional[Tuple[str, int]]) -> None:
        self._search_checked_keys = {key} if key else set()
        self._updating_search_checks = True
        try:
            for idx in range(self.search_list.count()):
                item = self.search_list.item(idx)
                if not item:
                    continue
                data = item.data(QtCore.Qt.UserRole)
                if not isinstance(data, tuple) or len(data) != 2:
                    item.setCheckState(QtCore.Qt.Unchecked)
                    continue
                item_key = self.model.item_key(str(data[0]), int(data[1]))
                item.setCheckState(QtCore.Qt.Checked if key and item_key == key else QtCore.Qt.Unchecked)
        finally:
            self._updating_search_checks = False
        self._sync_search_add_state()

    def _get_checked_search_results(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        wanted = set(self._search_checked_keys)
        for r in self._search_results:
            key = self.model.item_key(r["kind"], int(r["tmdb_id"]))
            if key in wanted:
                out.append(r)
        return out

    def _ensure_local_poster_for_result(self, r: Dict[str, Any]) -> None:
        kind = str(r.get("kind") or "")
        tmdb_id = int(r.get("tmdb_id") or 0)
        if not kind or tmdb_id <= 0:
            return
        if self.model.poster_path_for_key((kind, tmdb_id)):
            return
        rel = str(r.get("poster_rel") or "").strip()
        if not rel:
            return
        saved = self._download_tmdb_poster(kind, tmdb_id, rel)
        if saved:
            self.model.register_local_poster(kind, tmdb_id, saved)
            self._poster_pixmap_cache.clear()

    def _download_tmdb_poster(self, kind: str, tmdb_id: int, poster_rel: str) -> Optional[str]:
        rel = poster_rel if poster_rel.startswith("/") else f"/{poster_rel}"
        url = f"{TMDB_POSTER_BASE}{rel}"
        ext = Path(rel).suffix or ".jpg"
        sub = "tv" if kind == "tv" else "movies"
        out_dir = self.repo_root / "assets" / "posters" / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{tmdb_id}{ext}"
        if out_path.exists():
            return str(out_path)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            return str(out_path)
        except Exception:
            return None

    def _has_item(self, kind: str, tmdb_id: int) -> bool:
        return self.model.get_by_key((kind, tmdb_id)) is not None

    def _refresh_library_table(self) -> None:
        visible: List[InputsItem] = []
        for it in self.model.items:
            if not self._row_passes_header_filters(it):
                continue
            visible.append(it)

        tv_count = sum(1 for it in self.model.items if it.kind == "tv")
        mv_count = sum(1 for it in self.model.items if it.kind == "movie")
        self.count_lbl.setText(f"TV: {tv_count}  •  Movies: {mv_count}  •  Mode: immediate write")

        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(len(visible))

        for row, it in enumerate(visible):
            sel_item = QtWidgets.QTableWidgetItem("")
            sel_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            sel_item.setCheckState(QtCore.Qt.Unchecked)
            self.table.setItem(row, self.COL_SELECT, sel_item)

            scope_item = QtWidgets.QTableWidgetItem("")
            scope_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            scope_item.setCheckState(QtCore.Qt.Checked if it.in_scope else QtCore.Qt.Unchecked)
            self.table.setItem(row, self.COL_IN_SCOPE, scope_item)

            kind_item = QtWidgets.QTableWidgetItem("TV" if it.kind == "tv" else "MOVIE")
            kind_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.table.setItem(row, self.COL_KIND, kind_item)

            poster_item = QtWidgets.QTableWidgetItem("")
            poster_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            pix = self._load_local_poster_pixmap(it.kind, it.tmdb_id, max_w=44, max_h=66)
            if pix:
                poster_item.setIcon(QtGui.QIcon(pix))
            self.table.setItem(row, self.COL_POSTER, poster_item)

            title_item = QtWidgets.QTableWidgetItem(it.title)
            title_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            title_item.setData(QtCore.Qt.UserRole, self.model.item_ref(it))
            self.table.setItem(row, self.COL_TITLE, title_item)

            id_item = QtWidgets.QTableWidgetItem(str(it.tmdb_id))
            id_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.table.setItem(row, self.COL_TMDB_ID, id_item)

            status_item = QtWidgets.QTableWidgetItem(str(it.status or ""))
            status_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.table.setItem(row, self.COL_STATUS, status_item)

            seasons_item = QtWidgets.QTableWidgetItem(it.seasons_display())
            seasons_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            if it.kind == "movie":
                seasons_item.setText("—")
            self.table.setItem(row, self.COL_SEASONS, seasons_item)
            if it.kind == "tv":
                btn = QtWidgets.QToolButton(self.table)
                btn.setText("🎬")
                btn.setToolTip("Edit seasons")
                btn.setStyleSheet("QToolButton { color: #ffb347; font-weight: 700; }")
                item_ref = self.model.item_ref(it)
                btn.clicked.connect(lambda _=False, ref=item_ref: self._edit_tv_seasons_for_ref(ref))
                wrap = QtWidgets.QWidget(self.table)
                lay = QtWidgets.QHBoxLayout(wrap)
                lay.setContentsMargins(4, 0, 4, 0)
                lay.setSpacing(6)
                lbl = QtWidgets.QLabel(it.seasons_display(), wrap)
                lay.addWidget(lbl)
                lay.addStretch(1)
                lay.addWidget(btn)
                self.table.setCellWidget(row, self.COL_SEASONS, wrap)
            else:
                self.table.setCellWidget(row, self.COL_SEASONS, None)
            self.table.setRowHeight(row, 70)

        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)
        self._sync_select_all_state()

    def _set_all_row_checks(self, checked: bool) -> None:
        check = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            it = self.table.item(r, self.COL_SELECT)
            if it:
                it.setCheckState(check)
        self.table.blockSignals(False)
        self._sync_select_all_state()

    def _get_selected_row_indexes(self) -> List[int]:
        out: List[int] = []
        for r in range(self.table.rowCount()):
            it = self.table.item(r, self.COL_SELECT)
            if it and it.checkState() == QtCore.Qt.Checked:
                out.append(r)
        return out

    def _all_rows_checked(self) -> bool:
        total = self.table.rowCount()
        if total == 0:
            return False
        for r in range(total):
            it = self.table.item(r, self.COL_SELECT)
            if not it or it.checkState() != QtCore.Qt.Checked:
                return False
        return True

    def _update_select_header_label(self) -> None:
        label = "☑" if self._all_rows_checked() else "☐"
        hdr_item = self.table.horizontalHeaderItem(self.COL_SELECT)
        if hdr_item is None:
            hdr_item = QtWidgets.QTableWidgetItem(label)
            self.table.setHorizontalHeaderItem(self.COL_SELECT, hdr_item)
        else:
            hdr_item.setText(label)

    def _update_bulk_action_state(self) -> None:
        has_selected = len(self._get_selected_item_refs()) > 0
        self.btn_delete.setEnabled(has_selected)

    def _on_table_header_clicked(self, section: int) -> None:
        if section != self.COL_SELECT:
            return
        self._set_all_row_checks(not self._all_rows_checked())

    def _on_header_filter_menu(self, pos: QtCore.QPoint) -> None:
        hdr = self.table.horizontalHeader()
        section = hdr.logicalIndexAt(pos)
        if section < 0 or section == self.COL_SELECT:
            return
        current = self._header_filter_values.get(section, "")
        txt, ok = QtWidgets.QInputDialog.getText(self, "Column filter", f"Contains filter for '{self.HEADERS[section]}':", text=current)
        if not ok:
            return
        val = txt.strip()
        if val:
            self._header_filter_values[section] = val.lower()
        elif section in self._header_filter_values:
            del self._header_filter_values[section]
        self._update_header_filter_labels()
        self._refresh_library_table()

    def _update_header_filter_labels(self) -> None:
        for col in range(len(self.HEADERS)):
            if col == self.COL_SELECT:
                continue
            base = self.HEADERS[col]
            suffix = " ▾●" if col in self._header_filter_values else " ▾"
            item = self.table.horizontalHeaderItem(col)
            if item is None:
                item = QtWidgets.QTableWidgetItem(f"{base}{suffix}")
                self.table.setHorizontalHeaderItem(col, item)
            else:
                item.setText(f"{base}{suffix}")

    def _row_passes_header_filters(self, it: InputsItem) -> bool:
        if not self._header_filter_values:
            return True
        vals = {
            self.COL_KIND: ("TV" if it.kind == "tv" else "MOVIE").lower(),
            self.COL_TITLE: it.title.lower(),
            self.COL_TMDB_ID: str(it.tmdb_id),
            self.COL_STATUS: str(it.status or "").lower(),
            self.COL_SEASONS: str(it.seasons_display()).lower(),
        }
        for col, needle in self._header_filter_values.items():
            if needle not in vals.get(col, ""):
                return False
        return True

    def _on_table_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() == self.COL_SELECT:
            self._sync_select_all_state()
            return
        if item.column() != self.COL_IN_SCOPE:
            return
        row = item.row()
        item_ref = self._item_ref_for_row(row)
        it = self.model.get_by_ref(item_ref) if item_ref is not None else None
        if not it:
            return
        it.in_scope = (item.checkState() == QtCore.Qt.Checked)
        if self._save_model_now():
            self._set_dirty(False)

    def _item_ref_for_row(self, row: int) -> Optional[ItemRef]:
        if row < 0 or row >= self.table.rowCount():
            return None
        item = self.table.item(row, self.COL_TITLE)
        if not item:
            return None
        data = item.data(QtCore.Qt.UserRole)
        if not isinstance(data, int):
            return None
        return int(data)

    def _get_selected_item_refs(self) -> List[ItemRef]:
        out: List[ItemRef] = []
        seen_refs = set()
        for r in range(self.table.rowCount()):
            select_cell = self.table.item(r, self.COL_SELECT)
            if not select_cell or select_cell.checkState() != QtCore.Qt.Checked:
                continue
            item_ref = self._item_ref_for_row(r)
            if item_ref is not None and item_ref not in seen_refs:
                out.append(item_ref)
                seen_refs.add(item_ref)
        return out

    def _bulk_delete(self) -> None:
        selected_refs = self._get_selected_item_refs()
        if not selected_refs:
            QtWidgets.QMessageBox.information(self, "Delete selected", "No rows selected.")
            return
        keys = self._selected_keys_for_refs(selected_refs)
        if QtWidgets.QMessageBox.question(self, "Confirm delete", f"Delete {len(keys)} selected item key(s) and all duplicate instances?") != QtWidgets.QMessageBox.Yes:
            return

        removed = self.model.delete_by_keys(keys)
        if not self._save_model_now():
            return
        self._set_dirty(False)
        self._refresh_library_table()
        self._set_all_row_checks(False)
        QtWidgets.QMessageBox.information(self, "Deleted", f"Deleted {removed} item(s).")

    def _selected_keys_for_refs(self, refs: List[int]) -> List[Tuple[str, int]]:
        out: List[Tuple[str, int]] = []
        seen = set()
        for item_ref in refs:
            it = self.model.get_by_ref(item_ref)
            if not it:
                continue
            key = self.model.item_key(it.kind, it.tmdb_id)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    def _bulk_toggle_scope(self) -> None:
        selected_refs = self._get_selected_item_refs()
        if not selected_refs:
            QtWidgets.QMessageBox.information(self, "Toggle in-scope", "No rows selected.")
            return
        for item_ref in selected_refs:
            it = self.model.get_by_ref(item_ref)
            if not it:
                continue
            it.in_scope = not it.in_scope
        if not self._save_model_now():
            return
        self._set_dirty(False)
        self._refresh_library_table()

    def _edit_selected_tv_seasons(self) -> None:
        selected_refs = self._get_selected_item_refs()
        if len(selected_refs) != 1:
            QtWidgets.QMessageBox.information(self, "Edit seasons", "Select exactly one TV row.")
            return
        self._edit_tv_seasons_for_ref(selected_refs[0])

    def _edit_tv_seasons_for_ref(self, item_ref: int) -> None:
        it = self.model.get_by_ref(item_ref)
        if not it:
            return
        if it.kind != "tv":
            QtWidgets.QMessageBox.information(self, "Edit seasons", "That item is not TV.")
            return
        available = self.model.available_seasons_for_key((it.kind, it.tmdb_id))
        dlg = SeasonsDialog(self, it, available_seasons=available)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            it.seasons = dlg.result_value()
            if not self._save_model_now():
                return
            self._set_dirty(False)
            self._refresh_library_table()
            self._select_row_by_item_ref(item_ref)

    def _library_selection_changed(self) -> None:
        r = self.table.currentRow()
        item_ref = self._item_ref_for_row(r)
        it = self.model.get_by_ref(item_ref) if item_ref is not None else None
        if not it:
            self.detail_text.setPlainText("")
            self.detail_poster.setPixmap(QtGui.QPixmap())
            return
        self._render_detail(it)

    def _library_cell_double_clicked(self, row: int, col: int) -> None:
        item_ref = self._item_ref_for_row(row)
        it = self.model.get_by_ref(item_ref) if item_ref is not None else None
        if not it:
            return
        if col == self.COL_IN_SCOPE:
            it.in_scope = not it.in_scope
            if not self._save_model_now():
                return
            self._set_dirty(False)
            self._refresh_library_table()
            return
        if col == self.COL_SEASONS and it.kind == "tv":
            self._edit_tv_seasons_for_ref(item_ref)

    def _clear_row_selections(self) -> None:
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            it = self.table.item(r, self.COL_SELECT)
            if it:
                it.setCheckState(QtCore.Qt.Unchecked)
        self.table.blockSignals(False)

    def _reload_inputs(self) -> None:
        self.model.load_inputs()
        self.model.reindex_items()
        self._poster_pixmap_cache.clear()
        self._set_dirty(False)
        self._refresh_library_table()
        QtWidgets.QMessageBox.information(self, "Reloaded", "Reloaded inputs.json from disk.")

    def _save_inputs(self) -> None:
        self._sync_table_to_model()
        try:
            self.model.save_inputs()
        except Exception as ex:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(ex))
            return
        self._set_dirty(False)
        self._refresh_library_table()
        QtWidgets.QMessageBox.information(self, "Saved", "Saved inputs.json to disk.")

    def _save_model_now(self) -> bool:
        try:
            self.model.save_inputs()
        except Exception as ex:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(ex))
            return False
        return True

    def _tool_log(self, msg: str) -> None:
        self.tools_out.appendPlainText(msg)

    def _tool_section(self, name: str) -> None:
        stamp = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")
        self._tool_log("")
        self._tool_log(f"========== {name} @ {stamp} ==========")

    def _run_git(self, args: List[str], section_name: Optional[str] = None) -> subprocess.CompletedProcess:
        if section_name:
            self._tool_section(section_name)
        try:
            p = subprocess.run(["git", *args], cwd=str(self.repo_root), capture_output=True, text=True)
            out = (p.stdout or "") + (p.stderr or "")
            self._tool_log(f"$ git {' '.join(args)}\n{out}\n(exit {p.returncode})\n")
            return p
        except Exception as ex:
            self._tool_log(f"git error: {ex}")
            class _P:
                returncode = 1
                stdout = ""
                stderr = str(ex)
            return _P()  # type: ignore[return-value]

    def _tool_git_status(self) -> None:
        self._run_git(["status", "--short"], "Git status")

    def _tool_git_fetch(self) -> None:
        self._run_git(["fetch", "--all", "--prune"], "Git fetch")

    def _tool_git_pull(self) -> None:
        self._run_git(["pull"], "Git pull")

    def _tool_git_push(self) -> None:
        p = self._run_git(["push"], "Git push")
        if p.returncode != 0 and "fetch first" in ((p.stderr or "") + (p.stdout or "")).lower():
            self._tool_log("Push rejected (remote ahead). Recommended:")
            self._tool_log("  1) Git fetch")
            self._tool_log("  2) Git pull --rebase")
            self._tool_log("  3) Resolve conflicts if any")
            self._tool_log("  4) Git push")

    def _tool_git_push_remote(self) -> None:
        remote, ok = QtWidgets.QInputDialog.getText(self, "Push remote", "Remote name (e.g. origin, gitea):", text="origin")
        if not ok or not remote.strip():
            return
        branch, ok2 = QtWidgets.QInputDialog.getText(self, "Push branch", "Branch:", text="main")
        if not ok2 or not branch.strip():
            return
        self._run_git(["push", remote.strip(), branch.strip()], f"Git push {remote.strip()} {branch.strip()}")

    def _tool_dedup(self) -> None:
        self._tool_section("Dedup by key")
        seen = set()
        deduped = []
        removed = 0
        for it in self.model.items:
            k = self.model.item_key(it.kind, it.tmdb_id)
            if k in seen:
                removed += 1
                continue
            seen.add(k)
            deduped.append(it)
        self.model.items = deduped
        self.model.reindex_items()
        self._save_model_now()
        self._refresh_library_table()
        self._tool_log(f"Dedup removed {removed} duplicate rows.")

    def _tool_bulk_season_spec(self) -> None:
        spec, ok = QtWidgets.QInputDialog.getText(self, "Bulk season_spec", "Enter season_spec (e.g. *, 5+, 1,2,3):")
        if not ok or not spec.strip():
            return
        self._tool_section("Bulk season_spec")
        spec = spec.strip()
        target_refs = self._get_selected_item_refs()
        targets = [self.model.get_by_ref(r) for r in target_refs] if target_refs else self.model.items
        count = 0
        for it in targets:
            if not it or it.kind != "tv":
                continue
            it.seasons = self.model._season_spec_to_seasons(spec)
            count += 1
        self._save_model_now()
        self._refresh_library_table()
        self._tool_log(f"Bulk season_spec applied to {count} TV items.")

    def _tool_poster_audit(self) -> None:
        self._tool_section("Poster audit")
        missing = []
        for it in self.model.items:
            if not self.model.poster_path_for_key((it.kind, it.tmdb_id)):
                missing.append((it.kind, it.tmdb_id, it.title))
        self._tool_log(f"Poster audit: {len(missing)} missing posters.")
        for k, tid, t in missing[:50]:
            self._tool_log(f"  - {k}:{tid} {t}")

    def _tool_fetch_missing_posters(self) -> None:
        self._tool_section("Fetch missing posters")
        missing = [it for it in self.model.items if not self.model.poster_path_for_key((it.kind, it.tmdb_id))]
        if not missing:
            self._tool_log("Fetch missing posters: none missing.")
            return
        added = 0
        unresolved: List[str] = []
        for it in missing:
            poster_rel = self._tmdb_poster_rel_for_item(it.kind, it.tmdb_id, it.title)
            if not poster_rel:
                unresolved.append(f"{it.kind}:{it.tmdb_id} {it.title} -> no TMDB poster found")
                continue
            saved = self._download_tmdb_poster(it.kind, it.tmdb_id, poster_rel)
            if not saved:
                unresolved.append(f"{it.kind}:{it.tmdb_id} {it.title} -> download failed")
                continue
            self.model.register_local_poster(it.kind, it.tmdb_id, saved)
            added += 1
        self._poster_pixmap_cache.clear()
        self._refresh_library_table()
        self._tool_log(f"Fetch missing posters: downloaded {added}/{len(missing)}.")
        if unresolved:
            self._tool_log("Unresolved:")
            for line in unresolved[:30]:
                self._tool_log(f"  - {line}")

    def _tmdb_poster_rel_for_item(self, kind: str, tmdb_id: int, title: str = "") -> str:
        try:
            r = requests.get(f"{TMDB_BASE}/{kind}/{tmdb_id}", params={"api_key": self.tmdb_key}, timeout=30)
            if r.status_code >= 400:
                data = {}
            else:
                data = r.json() or {}
            poster_rel = str(data.get("poster_path") or "").strip()
            if poster_rel:
                return poster_rel
            q = title.strip() or str(data.get("title") or data.get("name") or "").strip()
            if not q:
                return ""
            rs = requests.get(
                f"{TMDB_BASE}/search/{kind}",
                params={"api_key": self.tmdb_key, "query": q, "include_adult": "false"},
                timeout=30,
            )
            if rs.status_code >= 400:
                return ""
            js = rs.json() or {}
            for cand in js.get("results", []) or []:
                rel = str(cand.get("poster_path") or "").strip()
                if rel:
                    return rel
            return ""
        except Exception:
            return ""

    def _tool_data_audit(self) -> None:
        self._tool_section("Data/asset audit")
        no_status = 0
        no_provider = 0
        no_network = 0
        missing_local_poster = 0
        for it in self.model.items:
            if not (it.status or "").strip():
                no_status += 1
            if len(self.model.providers_for_key((it.kind, it.tmdb_id))) == 0:
                no_provider += 1
            if it.kind == "tv" and len(self.model.networks_for_key((it.kind, it.tmdb_id))) == 0:
                no_network += 1
            if not self.model.poster_path_for_key((it.kind, it.tmdb_id)):
                missing_local_poster += 1
        self._tool_log(
            f"Data audit: no_status={no_status}, no_provider={no_provider}, no_network(tv)={no_network}, missing_local_poster={missing_local_poster}"
        )

    def _tool_git_security_diag(self) -> None:
        self._tool_section("Git security diagnostics")
        self._run_git(["config", "--show-origin", "--get-all", "credential.helper"])
        self._run_git(["config", "--show-origin", "--get-all", "credential.interactive"])
        self._run_git(["remote", "-v"])
        self._tool_log("If push/pull fails with local security authority errors:")
        self._tool_log("1) git config --global credential.helper manager-core")
        self._tool_log("2) Prefer HTTPS remotes for PAT auth (or configure SSH agent outside LSA).")
        self._tool_log("3) Re-run pull/push from this tab after credential refresh.")

    def _data_json_path(self) -> Path:
        return self.repo_root / "data" / "data.json"

    def _load_data_json(self) -> Dict[str, Any]:
        path = self._data_json_path()
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_data_json(self, obj: Dict[str, Any]) -> None:
        path = self._data_json_path()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _find_episode_duplicates(self, obj: Dict[str, Any]) -> List[Tuple[str, int, int, int]]:
        issues: List[Tuple[str, int, int, int]] = []
        for show in obj.get("shows", []) or []:
            show_name = str(show.get("title") or f"tmdb:{show.get('tmdb_id')}")
            for season in show.get("seasons", []) or []:
                season_no = int(season.get("season_number") or 0)
                seen: Dict[str, int] = {}
                dup_count = 0
                for ep in season.get("episodes", []) or []:
                    ep_no = ep.get("episode_number")
                    ep_id = ep.get("id")
                    key = f"n:{int(ep_no)}" if isinstance(ep_no, int) else (f"id:{int(ep_id)}" if isinstance(ep_id, int) else "")
                    if not key:
                        continue
                    seen[key] = seen.get(key, 0) + 1
                for cnt in seen.values():
                    if cnt > 1:
                        dup_count += cnt - 1
                if dup_count > 0:
                    issues.append((show_name, int(show.get("tmdb_id") or 0), season_no, dup_count))
        return issues

    def _tool_episode_dup_audit(self) -> None:
        self._tool_section("Episode duplicate audit")
        try:
            obj = self._load_data_json()
        except Exception as ex:
            self._tool_log(f"Failed to read data.json: {ex}")
            return
        issues = self._find_episode_duplicates(obj)
        self._tool_log(f"Duplicate-episode seasons found: {len(issues)}")
        for show_name, tmdb_id, season_no, dup_count in issues[:100]:
            self._tool_log(f"  - {show_name} (tmdb:{tmdb_id}) season {season_no}: {dup_count} duplicate episode rows")

    def _tool_episode_dup_fix(self) -> None:
        self._tool_section("Fix episode duplicates")
        try:
            obj = self._load_data_json()
        except Exception as ex:
            self._tool_log(f"Failed to read data.json: {ex}")
            return
        issues = self._find_episode_duplicates(obj)
        if not issues:
            self._tool_log("No duplicate episodes detected.")
            return
        total_dups = sum(x[3] for x in issues)
        msg = f"Fix duplicate episodes in data.json?\nSeasons affected: {len(issues)}\nRows to remove: {total_dups}"
        if QtWidgets.QMessageBox.question(self, "Fix episode duplicates", msg) != QtWidgets.QMessageBox.Yes:
            self._tool_log("Fix cancelled by user.")
            return

        removed = 0
        for show in obj.get("shows", []) or []:
            for season in show.get("seasons", []) or []:
                src = season.get("episodes", []) or []
                out = []
                seen: set[str] = set()
                for ep in src:
                    ep_no = ep.get("episode_number")
                    ep_id = ep.get("id")
                    key = f"n:{int(ep_no)}" if isinstance(ep_no, int) else (f"id:{int(ep_id)}" if isinstance(ep_id, int) else "")
                    if key and key in seen:
                        removed += 1
                        continue
                    if key:
                        seen.add(key)
                    out.append(ep)
                season["episodes"] = out

        try:
            self._save_data_json(obj)
            self.model.refresh_enrichment()
            self._refresh_library_table()
            self._tool_log(f"Duplicate episode fix complete. Removed {removed} duplicate episode rows.")
        except Exception as ex:
            self._tool_log(f"Failed to write data.json: {ex}")

    def _load_suggestions(self) -> None:
        kind = "tv" if self.sugg_kind.currentText() == "TV" else "movie"
        mode = self.sugg_mode.currentText()
        self.sugg_table.clearContents()
        self.sugg_table.setRowCount(0)
        self.sugg_detail.clear()
        self.sugg_add_selected.setEnabled(False)
        self._suggestions_results = []
        try:
            merged = self._fetch_hybrid_suggestions(kind=kind, mode=mode)
            self._suggestions_results = merged
            self.sugg_table.setRowCount(min(len(merged), 80))
            for row, x in enumerate(merged[:80]):
                self._render_suggestion_row(row, x)
            if self.sugg_table.rowCount():
                self.sugg_table.setCurrentCell(0, 1)
            self._sync_suggestion_add_state()
        except Exception as ex:
            self.sugg_detail.setPlainText(f"Suggestions load failed: {ex}")

    def _render_suggestion_row(self, row: int, x: Dict[str, Any]) -> None:
        tmdb_id = int(x.get("tmdb_id") or 0) if x.get("tmdb_id") else 0
        kind = str(x.get("kind") or "")
        title = str(x.get("title") or "—")
        date = str(x.get("date") or "—")
        score = float(x.get("score") or 0.0)

        poster_item = QtWidgets.QTableWidgetItem("")
        poster_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        if tmdb_id > 0 and kind in ("tv", "movie"):
            if not self.model.poster_path_for_key((kind, tmdb_id)) and x.get("poster_rel"):
                saved = self._download_tmdb_poster(kind, tmdb_id, str(x.get("poster_rel")))
                if saved:
                    self.model.register_local_poster(kind, tmdb_id, saved)
            pix = self._load_local_poster_pixmap(kind, tmdb_id, max_w=44, max_h=66)
            if pix:
                poster_item.setIcon(QtGui.QIcon(pix))
        self.sugg_table.setItem(row, 0, poster_item)

        title_item = QtWidgets.QTableWidgetItem(title)
        title_item.setData(QtCore.Qt.UserRole, x)
        title_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.sugg_table.setItem(row, 1, title_item)
        self.sugg_table.setItem(row, 2, QtWidgets.QTableWidgetItem("TV" if kind == "tv" else "MOVIE"))
        self.sugg_table.setItem(row, 3, QtWidgets.QTableWidgetItem(date))
        self.sugg_table.setItem(row, 4, QtWidgets.QTableWidgetItem(f"{score:.2f}"))

        in_state = self._search_state_icon(kind, tmdb_id) if tmdb_id > 0 else "⬜"
        in_item = QtWidgets.QTableWidgetItem(in_state)
        in_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        self.sugg_table.setItem(row, 5, in_item)

        add_btn = QtWidgets.QPushButton("Add")
        add_btn.setEnabled(tmdb_id > 0 and not self._has_item(kind, tmdb_id))
        add_btn.clicked.connect(lambda _=False, data=x: self._add_suggestion_item(data))
        self.sugg_table.setCellWidget(row, 6, add_btn)
        self.sugg_table.setRowHeight(row, 74)

    def _add_suggestion_item(self, data: Dict[str, Any]) -> None:
        kind = str(data.get("kind") or "")
        tmdb_id = int(data.get("tmdb_id") or 0)
        title = str(data.get("title") or "").strip()
        if kind not in ("tv", "movie") or tmdb_id <= 0 or not title:
            return
        if self._has_item(kind, tmdb_id):
            QtWidgets.QMessageBox.information(self, "Already exists", "That item is already in your inputs.json list.")
            return
        it = InputsItem(kind=kind, tmdb_id=tmdb_id, title=title, in_scope=True)
        if kind == "tv":
            available = self.model.available_seasons_for_key((kind, tmdb_id))
            dlg = SeasonsDialog(self, it, available_seasons=available)
            if dlg.exec() != QtWidgets.QDialog.Accepted:
                return
            it.seasons = dlg.result_value()
        self.model.items.append(it)
        self.model.items.sort(key=lambda x: (x.kind, x.title.lower(), x.tmdb_id))
        self.model.refresh_enrichment()
        self.model.reindex_items()
        self._poster_pixmap_cache.clear()
        if not self._save_model_now():
            return
        self._refresh_library_table()
        self._select_row_by_item_ref(self.model.item_ref(it))
        QtWidgets.QMessageBox.information(self, "Added", f"Added: {it.title} (id={it.tmdb_id})")
        self._load_suggestions()

    def _selected_suggestion_data(self) -> Dict[str, Any]:
        row = self.sugg_table.currentRow()
        if row < 0:
            return {}
        item = self.sugg_table.item(row, 1)
        if not item:
            return {}
        data = item.data(QtCore.Qt.UserRole)
        return data if isinstance(data, dict) else {}

    def _sync_suggestion_add_state(self) -> None:
        data = self._selected_suggestion_data()
        kind = str(data.get("kind") or "")
        tmdb_id = int(data.get("tmdb_id") or 0) if data.get("tmdb_id") else 0
        self.sugg_add_selected.setEnabled(kind in ("tv", "movie") and tmdb_id > 0 and not self._has_item(kind, tmdb_id))

    def _add_selected_suggestion(self) -> None:
        data = self._selected_suggestion_data()
        if data:
            self._add_suggestion_item(data)

    def _suggestion_selected(self, row: int) -> None:
        if row < 0 or row >= self.sugg_table.rowCount():
            self.sugg_detail.clear()
            self.sugg_add_selected.setEnabled(False)
            return
        item = self.sugg_table.item(row, 1)
        if not item:
            self.sugg_detail.clear()
            self.sugg_add_selected.setEnabled(False)
            return
        data = item.data(QtCore.Qt.UserRole) or {}
        kind = data.get("kind")
        tmdb_id = data.get("tmdb_id")
        title = data.get("title")
        overview = data.get("overview") or ""
        lines = [f"Title: {title}", f"Type: {kind}", f"TMDB ID: {tmdb_id or '—'}", f"Overview: {overview}"]
        lines.append(f"Source blend: {data.get('source') or 'hybrid'}")
        lines.append(f"Original date: {data.get('date') or '—'}")
        try:
            if tmdb_id:
                d = requests.get(f"{TMDB_BASE}/{kind}/{tmdb_id}", params={"api_key": self.tmdb_key}, timeout=30).json() or {}
                lines.append(f"Status: {d.get('status') or '—'}")
                if kind == "tv":
                    lines.append(f"Seasons: {d.get('number_of_seasons') or '—'}")
                    nets = [n.get("name") for n in d.get("networks", []) or [] if n.get("name")]
                    lines.append(f"Networks: {', '.join(nets) if nets else '—'}")
                genres = [g.get("name") for g in d.get("genres", []) or [] if g.get("name")]
                lines.append(f"Genres: {', '.join(genres) if genres else '—'}")
                prov = requests.get(f"{TMDB_BASE}/{kind}/{tmdb_id}/watch/providers", params={"api_key": self.tmdb_key}, timeout=30).json() or {}
                us = (((prov.get("results") or {}).get("US") or {}).get("flatrate") or [])
                providers = [p.get("provider_name") for p in us if p.get("provider_name")]
                lines.append(f"Providers (US): {', '.join(providers) if providers else '—'}")
        except Exception:
            pass
        self.sugg_detail.setPlainText("\n".join(lines))
        self._sync_suggestion_add_state()

    def _fetch_hybrid_suggestions(self, kind: str, mode: str) -> List[Dict[str, Any]]:
        tmdb = self._fetch_tmdb_suggestions(kind, mode)
        tvmaze = self._fetch_tvmaze_suggestions(kind, mode)
        trakt = self._fetch_trakt_suggestions(kind, mode)
        merged: Dict[str, Dict[str, Any]] = {}

        def norm_key(title: str, date: str) -> str:
            y = str(date or "")[:4]
            return f"{str(title or '').strip().lower()}::{y}"

        for src_name, rows in [("tmdb", tmdb), ("tvmaze", tvmaze), ("trakt", trakt)]:
            for r in rows:
                title = r.get("title") or ""
                date = r.get("date") or ""
                k = norm_key(title, date)
                base = merged.get(k)
                if not base:
                    base = {
                        "kind": kind,
                        "title": title,
                        "date": date,
                        "overview": r.get("overview") or "",
                        "tmdb_id": r.get("tmdb_id"),
                        "score": 0.0,
                        "source": [],
                    }
                    merged[k] = base
                if not base.get("overview") and r.get("overview"):
                    base["overview"] = r.get("overview")
                if not base.get("tmdb_id") and r.get("tmdb_id"):
                    base["tmdb_id"] = r.get("tmdb_id")
                base["score"] += float(r.get("score") or 0.0)
                base["source"].append(src_name)

        out = list(merged.values())
        if self.sugg_lang_en.isChecked():
            out = [x for x in out if str(x.get("lang") or "en") in ("en", "")]
        if self.sugg_exclude_kids.isChecked():
            bad = ("animation", "kids", "family")
            out = [x for x in out if not any(b in str(x.get("overview") or "").lower() for b in bad)]
        out.sort(key=lambda x: (x.get("score") or 0.0, str(x.get("date") or "")), reverse=True)
        return out

    def _fetch_tmdb_suggestions(self, kind: str, mode: str) -> List[Dict[str, Any]]:
        if mode == "Trending":
            url = f"{TMDB_BASE}/trending/{kind}/week"
            params = {"api_key": self.tmdb_key}
        elif mode == "Popular":
            url = f"{TMDB_BASE}/{kind}/popular"
            params = {"api_key": self.tmdb_key}
        elif mode == "Upcoming":
            if kind == "movie":
                url = f"{TMDB_BASE}/movie/upcoming"
                params = {"api_key": self.tmdb_key}
            else:
                today = _dt.datetime.now(_dt.UTC).date().isoformat()
                url = f"{TMDB_BASE}/discover/tv"
                params = {"api_key": self.tmdb_key, "first_air_date.gte": today, "sort_by": "first_air_date.asc"}
        else:
            url = f"{TMDB_BASE}/discover/{kind}"
            params = {"api_key": self.tmdb_key, "sort_by": "primary_release_date.desc" if kind == "movie" else "first_air_date.desc"}
        if self.sugg_lang_en.isChecked():
            params["with_original_language"] = "en"
        if self.sugg_exclude_kids.isChecked():
            params["without_genres"] = "16,10751"
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json() or {}
        rows = []
        for x in (data.get("results") or [])[:80]:
            rows.append(
                {
                    "title": x.get("name") if kind == "tv" else x.get("title"),
                    "date": x.get("first_air_date") if kind == "tv" else x.get("release_date"),
                    "overview": x.get("overview") or "",
                    "tmdb_id": int(x.get("id")) if x.get("id") else None,
                    "poster_rel": str(x.get("poster_path") or ""),
                    "score": 1.0 + float(x.get("popularity") or 0.0) / 1000.0,
                    "lang": x.get("original_language") or "",
                }
            )
        return rows

    def _fetch_tvmaze_suggestions(self, kind: str, mode: str) -> List[Dict[str, Any]]:
        if kind != "tv":
            return []
        q = "new" if mode == "New" else ("popular" if mode == "Popular" else "trending")
        r = requests.get("https://api.tvmaze.com/search/shows", params={"q": q}, timeout=30)
        r.raise_for_status()
        data = r.json() or []
        rows = []
        for x in data[:80]:
            show = x.get("show") or {}
            rows.append(
                {
                    "title": show.get("name") or "",
                    "date": show.get("premiered") or "",
                    "overview": show.get("summary") or "",
                    "tmdb_id": None,
                    "score": 0.8 + float(x.get("score") or 0.0),
                    "lang": str(show.get("language") or "").lower()[:2],
                }
            )
        return rows

    def _fetch_trakt_suggestions(self, kind: str, mode: str) -> List[Dict[str, Any]]:
        api_key = os.environ.get("TRAKT_API_KEY", "").strip()
        if not api_key:
            return []
        if mode == "Trending":
            path = f"/{kind}s/trending"
        elif mode == "Popular":
            path = f"/{kind}s/popular"
        else:
            path = f"/calendars/all/{kind}s/new/7"
        headers = {"trakt-api-key": api_key, "trakt-api-version": "2"}
        r = requests.get(f"https://api.trakt.tv{path}", headers=headers, timeout=30)
        if r.status_code >= 400:
            return []
        data = r.json() or []
        rows = []
        for x in data[:80]:
            obj = x.get(kind) if isinstance(x, dict) and kind in x else x
            if not isinstance(obj, dict):
                continue
            ids = obj.get("ids") or {}
            rows.append(
                {
                    "title": obj.get("title") or "",
                    "date": obj.get("released") or obj.get("first_aired") or "",
                    "overview": obj.get("overview") or "",
                    "tmdb_id": ids.get("tmdb"),
                    "score": 1.2,
                    "lang": "en",
                }
            )
        return rows

    def _select_row_by_item_ref(self, item_ref: int) -> None:
        for r in range(self.table.rowCount()):
            ref = self._item_ref_for_row(r)
            if ref == item_ref:
                self.table.setCurrentCell(r, self.COL_TITLE)
                self.table.scrollToItem(self.table.item(r, self.COL_TITLE))
                return

    def _sync_table_to_model(self) -> None:
        for r in range(self.table.rowCount()):
            item_ref = self._item_ref_for_row(r)
            it = self.model.get_by_ref(item_ref) if item_ref is not None else None
            if not it:
                continue
            cell = self.table.item(r, self.COL_IN_SCOPE)
            if cell:
                it.in_scope = (cell.checkState() == QtCore.Qt.Checked)

    def _render_detail(self, it: InputsItem) -> None:
        lines = [
            f"Title: {it.title}",
            f"Type: {it.kind}",
            f"TMDB ID: {it.tmdb_id}",
            f"In scope: {'yes' if it.in_scope else 'no'}",
            f"Status: {it.status or ''}",
            f"Seasons: {it.seasons_display()}",
        ]
        self.detail_text.setPlainText("\n".join(lines))
        pix = self._load_local_poster_pixmap(it.kind, it.tmdb_id, max_w=120, max_h=180)
        self.detail_poster.setPixmap(pix if pix else QtGui.QPixmap())

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty

    def _sync_select_all_state(self) -> None:
        self._update_select_header_label()
        self._update_bulk_action_state()

    def _load_local_poster_pixmap(self, kind: str, tmdb_id: int, max_w: int, max_h: int) -> Optional[QtGui.QPixmap]:
        item_key = self.model.item_key(kind, tmdb_id)
        path = self.model.poster_path_for_key(item_key)
        if not path:
            return None
        key = (path, int(max_w), int(max_h))
        cached = self._poster_pixmap_cache.get(key)
        if cached is not None:
            return cached

        p = Path(path)
        if not p.exists():
            return None
        pix = QtGui.QPixmap(str(p))
        if pix.isNull():
            return None
        scaled = pix.scaled(max_w, max_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self._poster_pixmap_cache[key] = scaled
        return scaled

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._search_thread is not None:
            self._search_thread.quit()
            self._search_thread.wait(1500)
        super().closeEvent(event)


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if (cur / ".git").exists() or (cur / "scripts").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    repo_root = find_repo_root(Path.cwd())
    inputs_path = repo_root / "data" / "inputs.json"
    tmdb_key = os.environ.get("API_TMDB_KEY", "").strip()
    if not tmdb_key:
        QtWidgets.QMessageBox.critical(None, "Missing TMDB key", "Set env var API_TMDB_KEY before running.")
        return 2
    if not inputs_path.exists():
        QtWidgets.QMessageBox.critical(None, "Missing inputs.json", f"Not found: {str(inputs_path)}")
        return 2
    w = MainWindow(repo_root=repo_root, inputs_path=inputs_path, tmdb_key=tmdb_key)
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
