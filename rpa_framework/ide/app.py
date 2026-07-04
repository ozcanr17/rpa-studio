import keyword
import multiprocessing
import os
import re
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    __package__ = "rpa_framework.ide"
    import rpa_framework.ide

from .capture import build_capture_class, grab_desktop
from .editor import build_editor_class
from .engine import ExecutionEngine
from .panels import IMAGE_EXTS, build_panels, sikuli_main_script, slugify, spawn, watch
from .qt_shim import cached_builder, load_qt
from .theme import COLORS, apply_theme, logo_icon, logo_pixmap, make_icon
from ..packaging.runtime_paths import bundle_root, configured_ocr, docs_path, examples_dir, is_compiled

_DEFAULT_OPTS = {"font": 11, "delay": 2.0, "similarity": 0.95, "ocr_lang": "eng", "autosave": True}

_ABOUT = """<h3>RPA Studio</h3>
<p><i>Automate. Connect. Achieve.</i></p>
<p>Cross-platform desktop automation: native accessibility trees first,
computer vision (SIFT) and OCR as the visual fallback.</p>
<p>Scripts run in an isolated process, so the interface always stays
responsive. SikuliX-style commands work out of the box.</p>"""


@cached_builder
def build_main_window_class(qt):
    QtCore, QtGui, QtWidgets = qt.QtCore, qt.QtGui, qt.QtWidgets
    ScriptEditor = build_editor_class(qt)
    capture = build_capture_class(qt)
    CaptureOverlay = capture.Overlay
    HighlightOverlay = capture.Highlight
    panels = build_panels(qt)

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self._engine = ExecutionEngine()
            self._settings = QtCore.QSettings("RPAFramework", "RPAStudio")
            self._build_process = None
            self._overlay = None
            self._highlight = None
            self._help_windows = []
            self._run_path = None
            self.setWindowTitle("RPA Studio")
            self.setWindowIcon(logo_icon(qt))
            self.setAcceptDrops(True)
            self._tabs = QtWidgets.QTabWidget(self)
            self._tabs.setTabsClosable(True)
            self._tabs.setMovable(True)
            self._tabs.setDocumentMode(True)
            self._tabs.tabCloseRequested.connect(self._close_tab)
            self._tabs.currentChanged.connect(self._tab_changed)
            self._tabs.tabBar().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self._tabs.tabBar().customContextMenuRequested.connect(self._tab_menu)
            self.setCentralWidget(self._tabs)
            self._console = panels.ConsolePanel(self)
            self._files = panels.FilesPanel(self)
            self._spy = panels.SpyPanel(self)
            self._winspy = panels.WindowSpyPanel(self)
            self._terminal = panels.TerminalPanel(self)
            self._reference = panels.ReferencePanel(self)
            self._files.fileActivated.connect(self.open_path)
            self._files.imageActivated.connect(self._test_asset)
            self._spy.insertRequested.connect(self._insert_snippet)
            self._winspy.insertRequested.connect(self._insert_snippet)
            self._reference.insertRequested.connect(self._insert_snippet)
            self._docks = {}
            areas = QtCore.Qt.DockWidgetArea
            for key, title, widget, area in (
                ("files", "Explorer", self._files, areas.LeftDockWidgetArea),
                ("reference", "Commands", self._reference, areas.RightDockWidgetArea),
                ("console", "Output", self._console, areas.BottomDockWidgetArea),
                ("spy", "Element Spy", self._spy, areas.BottomDockWidgetArea),
                ("winspy", "Window Spy", self._winspy, areas.BottomDockWidgetArea),
                ("terminal", "Terminal", self._terminal, areas.BottomDockWidgetArea),
            ):
                dock = QtWidgets.QDockWidget(title, self)
                dock.setObjectName("dock_" + key)
                dock.setWidget(widget)
                self.addDockWidget(area, dock)
                self._docks[key] = dock
            self.splitDockWidget(self._docks["console"], self._docks["spy"], QtCore.Qt.Orientation.Horizontal)
            self.tabifyDockWidget(self._docks["console"], self._docks["terminal"])
            self.tabifyDockWidget(self._docks["spy"], self._docks["winspy"])
            self._docks["console"].raise_()
            self._docks["spy"].raise_()
            self.resizeDocks([self._docks["console"], self._docks["spy"]], [700, 380], QtCore.Qt.Orientation.Horizontal)
            self._timer = QtCore.QTimer(self)
            self._timer.setInterval(50)
            self._timer.timeout.connect(self._drain)
            self._state = QtWidgets.QLabel("Idle")
            self._lint = QtWidgets.QLabel("")
            self._where = QtWidgets.QLabel("")
            self._place = QtWidgets.QLabel("Ln 1, Col 1")
            self.statusBar().addWidget(self._state)
            self.statusBar().addWidget(self._lint)
            self.statusBar().addPermanentWidget(self._where)
            self.statusBar().addPermanentWidget(self._place)
            self._build_actions()
            self._delay.setValue(self._opt("delay"))
            self.resize(1280, 800)
            self._restore_layout()
            self._new_file()
            samples = examples_dir()
            if samples:
                self._files.set_root(samples)

        def _build_actions(self):
            self._actions = {}
            bar = self.addToolBar("Main")
            bar.setObjectName("main_toolbar")
            bar.setMovable(False)
            bar.setIconSize(QtCore.QSize(22, 22))
            file_menu = self.menuBar().addMenu("&File")
            run_menu = self.menuBar().addMenu("&Run")
            tools_menu = self.menuBar().addMenu("&Tools")
            view_menu = self.menuBar().addMenu("&View")
            help_menu = self.menuBar().addMenu("&Help")
            entries = (
                ("new", "&New Script", "Ctrl+N", "new", self._new_file, file_menu, True),
                ("open", "&Open...", "Ctrl+O", "open", self._open_file, file_menu, True),
                ("save", "&Save", "Ctrl+S", "save", self._save_file, file_menu, True),
                ("save_as", "Save &As...", "Ctrl+Shift+S", None, self._save_file_as, file_menu, False),
                ("close_tab", "&Close Tab", "Ctrl+W", None, self._close_current_tab, file_menu, False),
                ("settings", "Se&ttings...", "Ctrl+,", None, self._show_settings, file_menu, False),
                ("run", "&Run Script", "F5", "run", self._run, run_menu, True),
                ("pause", "&Pause", "F6", "pause", self._toggle_pause, run_menu, True),
                ("stop", "S&top", "Shift+F5", "stop", self._stop, run_menu, True),
                ("capture", "&Capture Image (Instant)...", "Ctrl+Shift+C", "camera", self._capture_image, tools_menu, True),
                ("capture_delayed", "Capture Image (&Delayed)...", "Ctrl+Shift+D", "timer", self._delayed_capture, tools_menu, True),
                ("ocr", "&Read Screen Text (OCR)...", "Ctrl+Shift+R", "ocr", self._read_screen_text, tools_menu, True),
                ("region", "Capture Re&gion From Screen...", "Ctrl+Shift+G", "region", self._insert_region, tools_menu, True),
                ("location", "Capture &Location From Screen...", "Ctrl+Shift+L", "location", self._capture_location, tools_menu, True),
                ("offset", "Draw Target O&ffset...", "Ctrl+Shift+T", "offset", self._draw_offset_tool, tools_menu, True),
                ("spy_show", "Show &Element Spy", "Ctrl+Shift+E", "spy", self._show_spy, tools_menu, True),
                ("winspy_show", "Show &Window Spy", "Ctrl+Shift+W", "window", self._show_winspy, tools_menu, True),
                ("terminal_show", "Ter&minal", "Alt+F12", "terminal", self._show_terminal, tools_menu, True),
                ("find_files", "Find in F&iles...", "Ctrl+Shift+F", "search", lambda: self._find_in_files(False), tools_menu, True),
                ("replace_files", "Replace in Files...", "Ctrl+Shift+R", None, lambda: self._find_in_files(True), tools_menu, False),
                ("goto_file", "Go to File...", "Ctrl+Shift+N", None, self._goto_file, tools_menu, False),
                ("build", "&Build Standalone EXE", None, "build", self._build_exe, tools_menu, True),
                ("guide_en", "User &Guide (English)", "F1", "book", lambda: self._show_doc("TUTORIAL.md", "User Guide"), help_menu, True),
                ("guide_tr", "Kullanim &Kilavuzu (Turkce)", None, None, lambda: self._show_doc("KILAVUZ.md", "Kullanim Kilavuzu"), help_menu, False),
                ("about", "&About RPA Studio", None, None, self._about, help_menu, False),
            )
            groups = {"run": bar, "capture": bar, "guide_en": bar}
            for key, text, shortcut, icon, slot, menu, in_bar in entries:
                action = QtGui.QAction(text, self)
                if shortcut:
                    action.setShortcut(shortcut)
                if icon:
                    action.setIcon(make_icon(qt, icon))
                action.triggered.connect(slot)
                menu.addAction(action)
                if in_bar:
                    if key in groups:
                        bar.addSeparator()
                    bar.addAction(action)
                self._actions[key] = action
            file_menu.insertSeparator(self._actions["close_tab"])
            sikuli_action = QtGui.QAction("Open Siku&liX Folder...", self)
            sikuli_action.triggered.connect(self._open_sikuli)
            file_menu.insertAction(self._actions["save"], sikuli_action)
            self._recent_menu = QtWidgets.QMenu("Open &Recent", self)
            file_menu.insertMenu(self._actions["save"], self._recent_menu)
            self._examples_menu = QtWidgets.QMenu("Open E&xample", self)
            file_menu.insertMenu(self._actions["save"], self._examples_menu)
            file_menu.addSeparator()
            quit_action = QtGui.QAction("E&xit", self)
            quit_action.setShortcut("Ctrl+Q")
            quit_action.triggered.connect(self.close)
            file_menu.addAction(quit_action)
            self._delay = QtWidgets.QDoubleSpinBox(self)
            self._delay.setRange(0.0, 30.0)
            self._delay.setDecimals(1)
            self._delay.setSingleStep(0.5)
            self._delay.setValue(2.0)
            self._delay.setSuffix(" s")
            self._delay.setToolTip("Delay used only by Capture Image (Delayed): time to switch to the target before the screen freezes")
            self._delay.setFixedWidth(64)
            bar.insertWidget(self._actions["ocr"], self._delay)
            for key in ("files", "spy", "winspy", "terminal", "reference", "console"):
                view_menu.addAction(self._docks[key].toggleViewAction())
            for key, action in self._actions.items():
                stored = self._settings.value("key_" + key)
                if stored:
                    action.setShortcut(QtGui.QKeySequence(str(stored)))
            self._fill_recent_menu()
            self._fill_examples_menu()
            if is_compiled():
                self._actions["build"].setEnabled(False)
                self._actions["build"].setToolTip("Building is available when running from source")
            self._refresh_ui()

        def _fill_recent_menu(self):
            self._recent_menu.clear()
            paths = [p for p in self._recent_paths() if os.path.isfile(p)]
            self._recent_menu.setEnabled(bool(paths))
            for path in paths:
                action = QtGui.QAction(os.path.basename(path), self)
                action.setToolTip(path)
                action.triggered.connect(lambda checked=False, p=path: self.open_path(p))
                self._recent_menu.addAction(action)

        def _recent_paths(self):
            value = self._settings.value("recent") or []
            if isinstance(value, str):
                value = [value]
            return [v for v in value if v]

        def _add_recent(self, path):
            items = [path] + [p for p in self._recent_paths() if p != path]
            self._settings.setValue("recent", items[:8])
            self._fill_recent_menu()

        def _fill_examples_menu(self):
            self._examples_menu.clear()
            folder = examples_dir()
            names = sorted(n for n in os.listdir(folder)) if folder else []
            names = [n for n in names if n.endswith(".py")]
            self._examples_menu.setEnabled(bool(names))
            for name in names:
                action = QtGui.QAction(name, self)
                action.triggered.connect(lambda checked=False, p=os.path.join(folder, name): self.open_path(p))
                self._examples_menu.addAction(action)

        def _restore_layout(self):
            geometry = self._settings.value("geometry")
            state = self._settings.value("state")
            try:
                if geometry:
                    self.restoreGeometry(geometry)
                if state:
                    self.restoreState(state, 2)
            except Exception:
                pass

        def _new_tab(self, path=None):
            editor = ScriptEditor(self._tabs)
            editor._file_path = None
            try:
                editor.set_point_size(self._opt("font"))
            except Exception:
                pass
            editor.document().modificationChanged.connect(self._sync_tab_state)
            editor.cursorPositionChanged.connect(self._update_place)
            editor.lintChanged.connect(self._lint_status)
            editor.imageOpenRequested.connect(self._test_asset)
            if path:
                editor.load_file(path)
                editor._file_path = path
            index = self._tabs.addTab(editor, os.path.basename(path) if path else "untitled")
            self._tabs.setCurrentIndex(index)
            self._sync_tab_state()
            return editor

        def current_editor(self):
            return self._tabs.currentWidget()

        def _new_file(self):
            self._new_tab()

        def open_path(self, path):
            path = os.path.abspath(path)
            if os.path.isdir(path):
                script = sikuli_main_script(path)
                if script is None:
                    QtWidgets.QMessageBox.warning(self, "Open failed", "No .py script found inside {}".format(path))
                    return
                path = script
            for i in range(self._tabs.count()):
                editor = self._tabs.widget(i)
                if getattr(editor, "_file_path", None) == path:
                    self._tabs.setCurrentIndex(i)
                    return
            current = self.current_editor()
            reuse = current is not None and getattr(current, "_file_path", None) is None and not current.document().isModified() and not current.toPlainText()
            try:
                if reuse:
                    current.load_file(path)
                    current._file_path = path
                else:
                    self._new_tab(path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Open failed", str(exc))
                return
            self._add_recent(path)
            root = os.path.normpath(self._files.root_path() or "")
            inside = root and os.path.normpath(path).lower().startswith((root + os.sep).lower())
            if not inside:
                self._files.set_root(os.path.dirname(path))
            self._sync_tab_state()

        def _open_file(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Script", self._start_dir(), "Python scripts (*.py);;All files (*.*)")
            if path:
                self.open_path(path)

        def _start_dir(self):
            editor = self.current_editor()
            path = getattr(editor, "_file_path", None) if editor else None
            if path:
                return os.path.dirname(path)
            return examples_dir() or os.path.expanduser("~")

        def _save_file(self):
            editor = self.current_editor()
            return self._save_editor(editor) if editor else False

        def _save_file_as(self):
            editor = self.current_editor()
            return self._save_editor_as(editor) if editor else False

        def _save_editor(self, editor):
            path = getattr(editor, "_file_path", None)
            if path is None:
                return self._save_editor_as(editor)
            try:
                editor.save_file(path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))
                return False
            self._sync_tab_state()
            return True

        def _save_editor_as(self, editor):
            suggested = os.path.join(self._start_dir(), "script.py")
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Script", suggested, "Python scripts (*.py);;All files (*.*)")
            if not path:
                return False
            editor._file_path = path
            try:
                editor.save_file(path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Save failed", str(exc))
                return False
            self._add_recent(path)
            self._files.set_root(os.path.dirname(path))
            self._sync_tab_state()
            return True

        def _close_current_tab(self):
            self._close_tab(self._tabs.currentIndex())

        def _close_tab(self, index):
            if index < 0:
                return
            editor = self._tabs.widget(index)
            if editor.document().isModified():
                buttons = QtWidgets.QMessageBox.StandardButton
                choice = QtWidgets.QMessageBox.question(self, "Unsaved changes", "Save changes to {}?".format(self._tabs.tabText(index).rstrip("*")), buttons.Save | buttons.Discard | buttons.Cancel)
                if choice == buttons.Cancel:
                    return
                if choice == buttons.Save and not self._save_editor(editor):
                    return
            self._tabs.removeTab(index)
            editor.deleteLater()
            if self._tabs.count() == 0:
                self._new_file()

        def _sync_tab_state(self):
            bar = self._tabs.tabBar()
            for i in range(self._tabs.count()):
                editor = self._tabs.widget(i)
                name = os.path.basename(getattr(editor, "_file_path", None) or "untitled")
                star = "*" if editor.document().isModified() else ""
                self._tabs.setTabText(i, name + star)
                bar.setTabTextColor(i, QtGui.QColor(COLORS["warn"]) if getattr(editor, "_pin", False) else QtGui.QColor())
            self._refresh_ui()

        def _tab_changed(self, index):
            self._refresh_ui()
            self._update_place()

        def _update_place(self):
            editor = self.current_editor()
            if editor is not None:
                line, column = editor.cursor_place()
                self._place.setText("Ln {}, Col {}".format(line, column))

        def _refresh_ui(self):
            running = self._engine.running
            self._actions["run"].setEnabled(not running)
            self._actions["stop"].setEnabled(running)
            self._actions["pause"].setEnabled(running)
            self._actions["pause"].setText("&Resume" if self._engine.paused else "&Pause")
            editor = self.current_editor()
            path = getattr(editor, "_file_path", None) if editor else None
            name = os.path.basename(path) if path else "untitled"
            star = "*" if editor is not None and editor.document().isModified() else ""
            self.setWindowTitle("RPA Studio - {}{}".format(name, star))
            self._where.setText(path or "")

        def _set_state(self, text):
            self._state.setText(text)

        def _insert_snippet(self, text):
            editor = self.current_editor()
            if editor is not None:
                editor.insert_snippet(text)

        def _show_spy(self):
            self._docks["spy"].show()
            self._docks["spy"].raise_()

        def _show_winspy(self):
            self._docks["winspy"].show()
            self._docks["winspy"].raise_()
            self._winspy.refresh()

        def _show_terminal(self):
            self._docks["terminal"].show()
            self._docks["terminal"].raise_()
            self._terminal.start(self._files.root_path() or self._start_dir())

        def _tab_menu(self, point):
            bar = self._tabs.tabBar()
            index = bar.tabAt(point)
            if index < 0:
                return
            editor = self._tabs.widget(index)
            path = getattr(editor, "_file_path", None)
            pinned = bool(getattr(editor, "_pin", False))
            menu = QtWidgets.QMenu(bar)
            entries = (
                ("Close", lambda: self._close_tab(index), not pinned),
                ("Close Others", lambda: self._close_many(keep=editor), True),
                ("Close All", lambda: self._close_many(), True),
                ("Close Tabs to the Right", lambda: self._close_many(right_of=editor), True),
                (None, None, None),
                ("Unpin Tab" if pinned else "Pin Tab", lambda: self._toggle_pin(editor), True),
                (None, None, None),
                ("Copy Full Path", lambda: QtWidgets.QApplication.clipboard().setText(os.path.normpath(path or "")), bool(path)),
                ("Reveal in File Explorer", lambda: self._reveal_path(path), bool(path)),
                ("Rename File...", lambda: self._rename_tab_file(editor), bool(path)),
                ("Open in New Window", lambda: self._open_in_window(path), bool(path)),
            )
            for label, slot, enabled in entries:
                if label is None:
                    menu.addSeparator()
                    continue
                action = menu.addAction(label)
                action.setEnabled(bool(enabled))
                action.triggered.connect(lambda checked=False, s=slot: s())
            menu.exec(bar.mapToGlobal(point))

        def _toggle_pin(self, editor):
            editor._pin = not bool(getattr(editor, "_pin", False))
            self._sync_tab_state()

        def _close_many(self, keep=None, right_of=None):
            limit = self._tabs.indexOf(right_of) if right_of is not None else -1
            doomed = []
            for i in range(self._tabs.count()):
                widget = self._tabs.widget(i)
                if widget is keep or getattr(widget, "_pin", False):
                    continue
                if right_of is not None and i <= limit:
                    continue
                doomed.append(widget)
            for widget in doomed:
                index = self._tabs.indexOf(widget)
                if index >= 0:
                    self._close_tab(index)

        def _reveal_path(self, path):
            if not path:
                return
            try:
                os.startfile(os.path.dirname(path))
            except Exception:
                pass

        def _rename_tab_file(self, editor):
            path = getattr(editor, "_file_path", None)
            if not path:
                return
            old = os.path.basename(path)
            new, ok = QtWidgets.QInputDialog.getText(self, "Rename File", "New name:", text=old)
            if not ok or not new.strip() or new.strip() == old:
                return
            target = os.path.join(os.path.dirname(path), new.strip())
            try:
                os.rename(path, target)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Rename failed", str(exc))
                return
            editor._file_path = target
            self._add_recent(target)
            self._sync_tab_state()

        def _open_in_window(self, path):
            if not path:
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("{} (view)".format(os.path.basename(path)))
            layout = QtWidgets.QVBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            viewer = ScriptEditor(dialog)
            try:
                viewer.load_file(path)
            except Exception:
                pass
            viewer.setReadOnly(True)
            layout.addWidget(viewer)
            dialog.resize(860, 640)
            dialog.show()
            self._help_windows.append(dialog)

        def _search_root(self):
            return self._files.root_path() or self._start_dir()

        def _iter_search_files(self):
            root = self._search_root()
            skip = (".venv", ".venv-build", "__pycache__", ".git", "dist")
            for base, dirs, names in os.walk(root):
                dirs[:] = [d for d in dirs if d not in skip]
                for name in names:
                    if name.lower().endswith((".py", ".md", ".txt", ".json")):
                        yield os.path.join(base, name)

        def _open_result(self, item):
            data = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not data:
                return
            path, line = data
            self.open_path(path)
            editor = self.current_editor()
            if editor is not None and line:
                editor.go_to_line(line)

        def _find_in_files(self, replace=False):
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Replace in Files" if replace else "Find in Files")
            layout = QtWidgets.QVBoxLayout(dialog)
            form = QtWidgets.QFormLayout()
            needle_edit = QtWidgets.QLineEdit(dialog)
            form.addRow("Find:", needle_edit)
            replace_edit = QtWidgets.QLineEdit(dialog)
            if replace:
                form.addRow("Replace with:", replace_edit)
            layout.addLayout(form)
            results = QtWidgets.QListWidget(dialog)
            results.itemDoubleClicked.connect(self._open_result)
            layout.addWidget(results, 1)
            status = QtWidgets.QLabel("", dialog)
            layout.addWidget(status)
            buttons = QtWidgets.QHBoxLayout()
            find_button = QtWidgets.QPushButton("Find", dialog)
            buttons.addWidget(find_button)
            apply_button = QtWidgets.QPushButton("Replace All", dialog)
            apply_button.setEnabled(False)
            if replace:
                buttons.addWidget(apply_button)
            buttons.addStretch(1)
            layout.addLayout(buttons)
            root = self._search_root()

            def run_find():
                needle = needle_edit.text()
                results.clear()
                if not needle:
                    return
                count = 0
                for path in self._iter_search_files():
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as handle:
                            lines = handle.read().splitlines()
                    except Exception:
                        continue
                    for number, text in enumerate(lines, 1):
                        if needle.lower() in text.lower():
                            item = QtWidgets.QListWidgetItem("{}:{}: {}".format(os.path.relpath(path, root), number, text.strip()[:120]))
                            item.setData(QtCore.Qt.ItemDataRole.UserRole, (path, number))
                            results.addItem(item)
                            count += 1
                            if count >= 500:
                                status.setText("Stopped at 500 matches.")
                                apply_button.setEnabled(replace and count > 0)
                                return
                status.setText("{} match(es).".format(count))
                apply_button.setEnabled(replace and count > 0)

            def run_replace():
                needle = needle_edit.text()
                replacement = replace_edit.text()
                if not needle:
                    return
                changed = 0
                for path in self._iter_search_files():
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as handle:
                            content = handle.read()
                    except Exception:
                        continue
                    if needle not in content:
                        continue
                    try:
                        with open(path, "w", encoding="utf-8", newline="") as handle:
                            handle.write(content.replace(needle, replacement))
                        changed += 1
                    except Exception:
                        continue
                    for i in range(self._tabs.count()):
                        widget = self._tabs.widget(i)
                        if getattr(widget, "_file_path", None) == path and not widget.document().isModified():
                            widget.load_file(path)
                            widget._file_path = path
                status.setText("Replaced in {} file(s).".format(changed))
                run_find()

            find_button.clicked.connect(run_find)
            needle_edit.returnPressed.connect(run_find)
            apply_button.clicked.connect(run_replace)
            dialog.resize(760, 480)
            dialog.show()
            self._help_windows.append(dialog)

        def _goto_file(self):
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Go to File")
            layout = QtWidgets.QVBoxLayout(dialog)
            filter_edit = QtWidgets.QLineEdit(dialog)
            filter_edit.setPlaceholderText("Type part of a file name...")
            layout.addWidget(filter_edit)
            results = QtWidgets.QListWidget(dialog)
            results.itemDoubleClicked.connect(lambda item: (self._open_result(item), dialog.accept()))
            layout.addWidget(results, 1)
            root = self._search_root()
            everything = []
            for path in self._iter_search_files():
                everything.append(path)
                if len(everything) >= 3000:
                    break

            def refresh():
                needle = filter_edit.text().lower()
                results.clear()
                for path in everything:
                    name = os.path.basename(path)
                    if needle in name.lower():
                        item = QtWidgets.QListWidgetItem(os.path.relpath(path, root))
                        item.setData(QtCore.Qt.ItemDataRole.UserRole, (path, 0))
                        results.addItem(item)
                        if results.count() >= 200:
                            return

            def open_first():
                if results.count():
                    self._open_result(results.item(0))
                    dialog.accept()

            filter_edit.textChanged.connect(refresh)
            filter_edit.returnPressed.connect(open_first)
            refresh()
            dialog.resize(560, 420)
            dialog.show()
            self._help_windows.append(dialog)

        def _run(self):
            editor = self.current_editor()
            if editor is None or self._engine.running:
                return
            if getattr(editor, "_file_path", None) is None or editor.document().isModified():
                if editor.document().isModified() and getattr(editor, "_file_path", None) is not None and not self._opt("autosave"):
                    buttons = QtWidgets.QMessageBox.StandardButton
                    if QtWidgets.QMessageBox.question(self, "Save before run", "Save changes and run?", buttons.Yes | buttons.No) != buttons.Yes:
                        return
                if not self._save_editor(editor):
                    return
            self._console.clear()
            self._docks["console"].show()
            self._run_path = editor._file_path
            if self._engine.start(self._run_path):
                self._timer.start()
                self._set_state("Running")
                self._refresh_ui()

        def _stop(self):
            self._engine.stop()

        def _toggle_pause(self):
            if not self._engine.running:
                return
            if self._engine.paused:
                self._engine.resume()
                self._set_state("Running")
            else:
                self._engine.pause()
                self._set_state("Paused")
            self._refresh_ui()

        def _drain(self):
            for event in self._engine.poll():
                kind = event.get("type")
                data = event.get("data")
                if kind == "started":
                    self._console.append("[run] {}\n".format(data), kind)
                elif kind == "pass":
                    self._console.append("[pass] {}\n".format(data), kind)
                elif kind == "fail":
                    payload = data if isinstance(data, dict) else {"message": data}
                    self._console.append_fail(payload.get("message", ""), payload.get("image"))
                elif kind == "event":
                    self._console.append("[event] {}\n".format(data), kind)
                elif kind == "finished":
                    self._console.append("[done] exit code {}\n".format(data), kind)
                elif kind == "exit":
                    self._timer.stop()
                    self._console.append("[process] ended with code {}\n".format(data), kind)
                    self._set_state("Idle")
                    self._refresh_ui()
                else:
                    self._console.append(str(data), kind)

        def _begin_overlay(self, handler, message, mode="box", allow_offset=False, delay_seconds=0.0):
            if self._overlay is not None:
                return
            self.hide()

            def show_overlay():
                pixmap, union = grab_desktop(qt)
                overlay = CaptureOverlay(pixmap, union, message, mode, allow_offset)
                overlay.captured.connect(handler)
                overlay.canceled.connect(self._overlay_done)
                self._overlay = overlay
                overlay.show()
                overlay.activateWindow()
                overlay.setFocus()

            QtCore.QTimer.singleShot(max(160, int(delay_seconds * 1000)), show_overlay)

        def _overlay_done(self):
            self._overlay = None
            self.show()
            self.activateWindow()

        def _show_highlight(self, rects):
            overlay = HighlightOverlay(rects)
            self._highlight = overlay
            overlay.show()

        def _ready_to_capture(self):
            editor = self.current_editor()
            if editor is None:
                return False
            if getattr(editor, "_file_path", None) is None and not self._save_editor(editor):
                self._console.append("save the script first so the image can be stored next to it\n", "tool")
                return False
            return True

        def _capture_image(self):
            if self._ready_to_capture():
                self._begin_overlay(self._capture_done, "Drag to select the target image.", allow_offset=True)

        def _delayed_capture(self):
            if self._ready_to_capture():
                self._begin_overlay(self._capture_done, "Delayed capture: bring the target into view, then drag to select it.", allow_offset=True, delay_seconds=self._delay.value())

        def _next_image_name(self, folder):
            index = 1
            while os.path.exists(os.path.join(folder, "image_{}.png".format(index))):
                index += 1
            return "image_{}.png".format(index)

        def _pattern_var(self, name):
            stem = os.path.splitext(os.path.basename(name))[0]
            var = slugify(stem, "image", limit=4)
            if var[0].isdigit():
                var = "img_" + var
            if keyword.iskeyword(var):
                var = var + "_img"
            return var

        def _default_var(self, prefix):
            editor = self.current_editor()
            text = editor.toPlainText() if editor is not None else ""
            index = 1
            while re.search(r"\b{}_{}\b".format(prefix, index), text):
                index += 1
            return "{}_{}".format(prefix, index)

        def _ask_variable(self, title, default):
            name, ok = QtWidgets.QInputDialog.getText(self, title, "Variable name:", text=default)
            if not ok or not name.strip():
                return None
            raw = name.strip()
            if raw.isidentifier() and not keyword.iskeyword(raw):
                return raw
            var = slugify(raw, "item", limit=6)
            if var[0].isdigit():
                var = "v_" + var
            if keyword.iskeyword(var):
                var = var + "_v"
            return var

        def _capture_done(self, image, region, offset=None):
            self._overlay_done()
            editor = self.current_editor()
            if editor is None:
                return
            folder = editor.base_dir()
            default = os.path.splitext(self._next_image_name(folder))[0]
            var = self._ask_variable("Save Image Target", default)
            if var is None:
                return
            name = var + ".png"
            path = os.path.join(folder, name)
            if not image.save(path):
                QtWidgets.QMessageBox.warning(self, "Capture failed", "Could not write {}".format(path))
                return
            snippet = '{} = Pattern("{}").similar({:.2f})'.format(var, name, self._opt("similarity"))
            if offset:
                snippet += ".targetOffset({}, {})".format(offset[0], offset[1])
            editor.insert_snippet(snippet)
            self._console.append("saved {} and inserted:  {}\n".format(name, snippet), "tool")

        def _read_screen_text(self):
            self._begin_overlay(self._ocr_done, "Drag over the text to read. Esc cancels.")

        def _insert_region(self):
            self._begin_overlay(self._region_done, "Drag to select a region.")

        def _region_done(self, image, region, offset=None):
            self._overlay_done()
            editor = self.current_editor()
            if editor is None:
                return
            var = self._ask_variable("Save Region", self._default_var("region"))
            if var is None:
                return
            snippet = "{} = Region({}, {}, {}, {})".format(var, region.x(), region.y(), region.width(), region.height())
            editor.insert_snippet(snippet)
            self._console.append("inserted {}\n".format(snippet), "tool")

        def _capture_location(self):
            self._begin_overlay(self._location_done, "Click the spot you want to store as a Location.", mode="point")

        def _location_done(self, image, region, offset=None):
            self._overlay_done()
            editor = self.current_editor()
            if editor is None:
                return
            var = self._ask_variable("Save Location", self._default_var("location"))
            if var is None:
                return
            snippet = "{} = Location({}, {})".format(var, region.x(), region.y())
            editor.insert_snippet(snippet)
            self._console.append("inserted {}\n".format(snippet), "tool")

        def _draw_offset_tool(self):
            self._begin_overlay(self._offset_done, "Drag from the match center to the click target.", "line")

        def _offset_done(self, image, region, offset):
            self._overlay_done()
            editor = self.current_editor()
            if editor is None or not offset:
                return
            var = self._ask_variable("Save Target Offset", self._default_var("offset"))
            if var is None:
                return
            snippet = "{} = Offset({}, {})".format(var, offset[0], offset[1])
            editor.insert_snippet(snippet)
            self._console.append("inserted {}\n".format(snippet), "tool")

        def _ocr_done(self, image, region, offset=None):
            self._overlay_done()
            handle, tmp = tempfile.mkstemp(suffix=".png")
            os.close(handle)
            image.save(tmp)

            lang = self._opt("ocr_lang")

            def job():
                try:
                    return configured_ocr(lang=lang).read_text(tmp)
                finally:
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass

            self._docks["console"].show()
            self._console.append("reading text from a {}x{} region...\n".format(region.width(), region.height()), "tool")
            watch(qt, spawn(job), self._ocr_ok, self._ocr_err)

        def _ocr_ok(self, text):
            self._console.append((text or "(no text recognized)") + "\n", "stdout")

        def _ocr_err(self, exc):
            self._console.append("OCR failed: {} (is Tesseract installed or bundled in vendor/?)\n".format(exc), "stderr")

        def _build_exe(self):
            if is_compiled() or self._build_process is not None:
                return
            self._docks["console"].show()
            self._docks["console"].raise_()
            proc = QtCore.QProcess(self)
            proc.setWorkingDirectory(bundle_root())
            proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
            proc.readyReadStandardOutput.connect(lambda: self._console.append(bytes(proc.readAllStandardOutput()).decode("utf-8", "replace"), "tool"))
            proc.finished.connect(self._build_finished)
            self._build_process = proc
            self._console.append("starting EXE build, this can take a long time...\n", "tool")
            self._actions["build"].setEnabled(False)
            proc.start(sys.executable, ["-m", "rpa_framework.packaging.build"])

        def _build_finished(self, code, status):
            self._console.append("build finished with code {}\n".format(code), "tool")
            self._build_process = None
            self._actions["build"].setEnabled(not is_compiled())

        def _opt(self, key):
            value = self._settings.value("opt_" + key)
            fallback = _DEFAULT_OPTS[key]
            if value is None:
                return fallback
            if isinstance(fallback, bool):
                return str(value).lower() in ("true", "1", "yes")
            try:
                return type(fallback)(value)
            except Exception:
                return fallback

        def _apply_settings(self, values):
            for key, value in values.items():
                self._settings.setValue("opt_" + key, value)
            self._delay.setValue(self._opt("delay"))
            for i in range(self._tabs.count()):
                try:
                    self._tabs.widget(i).set_point_size(self._opt("font"))
                except Exception:
                    pass

        def _show_settings(self):
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Settings")
            outer = QtWidgets.QVBoxLayout(dialog)
            tabs = QtWidgets.QTabWidget(dialog)
            outer.addWidget(tabs)
            general = QtWidgets.QWidget(dialog)
            tabs.addTab(general, "General")
            form = QtWidgets.QFormLayout(general)
            font_spin = QtWidgets.QSpinBox(dialog)
            font_spin.setRange(8, 28)
            font_spin.setValue(self._opt("font"))
            form.addRow("Editor font size:", font_spin)
            delay_spin = QtWidgets.QDoubleSpinBox(dialog)
            delay_spin.setRange(0.0, 30.0)
            delay_spin.setDecimals(1)
            delay_spin.setSingleStep(0.5)
            delay_spin.setSuffix(" s")
            delay_spin.setValue(self._opt("delay"))
            form.addRow("Delayed capture wait:", delay_spin)
            sim_spin = QtWidgets.QDoubleSpinBox(dialog)
            sim_spin.setRange(0.5, 0.99)
            sim_spin.setDecimals(2)
            sim_spin.setSingleStep(0.01)
            sim_spin.setValue(self._opt("similarity"))
            form.addRow("Default Pattern similarity:", sim_spin)
            lang_edit = QtWidgets.QLineEdit(self._opt("ocr_lang"), dialog)
            lang_edit.setToolTip("Tesseract language codes, joined with +. Bundled: eng, tur, dejavu_sans. Example: eng+tur")
            form.addRow("OCR language:", lang_edit)
            autosave = QtWidgets.QCheckBox("Save the script automatically before Run", dialog)
            autosave.setChecked(self._opt("autosave"))
            form.addRow("", autosave)
            shortcut_area = QtWidgets.QScrollArea(dialog)
            shortcut_area.setWidgetResizable(True)
            shortcut_host = QtWidgets.QWidget(dialog)
            shortcut_form = QtWidgets.QFormLayout(shortcut_host)
            shortcut_area.setWidget(shortcut_host)
            tabs.addTab(shortcut_area, "Shortcuts")
            editors = {}
            for key in sorted(self._actions):
                action = self._actions[key]
                editor = QtWidgets.QKeySequenceEdit(action.shortcut(), dialog)
                shortcut_form.addRow(action.text().replace("&", "") + ":", editor)
                editors[key] = editor
            buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel, dialog)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            outer.addWidget(buttons)
            dialog.resize(520, 480)
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self._apply_settings({
                    "font": font_spin.value(),
                    "delay": delay_spin.value(),
                    "similarity": sim_spin.value(),
                    "ocr_lang": lang_edit.text().strip() or "eng",
                    "autosave": autosave.isChecked(),
                })
                self._apply_shortcuts({key: editor.keySequence().toString() for key, editor in editors.items()})

        def _apply_shortcuts(self, mapping):
            for key, sequence in mapping.items():
                action = self._actions.get(key)
                if action is None:
                    continue
                self._settings.setValue("key_" + key, sequence)
                action.setShortcut(QtGui.QKeySequence(sequence))

        def _show_doc(self, filename, title):
            path = docs_path(filename)
            if not path:
                self._console.append("document not found: {}\n".format(filename), "tool")
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(title)
            dialog.resize(940, 720)
            layout = QtWidgets.QVBoxLayout(dialog)
            browser = QtWidgets.QTextBrowser(dialog)
            browser.setOpenExternalLinks(True)
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                browser.setMarkdown(handle.read())
            layout.addWidget(browser)
            dialog.show()
            self._help_windows.append(dialog)

        def _about(self):
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("About RPA Studio")
            box.setText(_ABOUT)
            box.setIconPixmap(logo_pixmap(qt, 96))
            box.exec()

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()

        def dropEvent(self, event):
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(".py") or (os.path.isdir(path) and path.lower().endswith(".sikuli")):
                    self.open_path(path)

        def _open_sikuli(self):
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open SikuliX Folder", self._start_dir())
            if path:
                self.open_path(path)

        def _lint_status(self, error):
            editor = self.sender()
            if editor is not self.current_editor():
                return
            if error:
                self._lint.setText("Syntax error, line {}: {}".format(error[0], error[1]))
            else:
                self._lint.setText("")

        def _similarity_for(self, name):
            fallback = self._opt("similarity")
            editor = self.current_editor()
            if editor is None:
                return fallback
            pattern = re.compile(re.escape(name) + r"[\"']\s*\)\s*\.similar\(\s*([0-9.]+)\s*\)")
            match = pattern.search(editor.toPlainText())
            if not match:
                return fallback
            try:
                return min(0.99, max(0.5, float(match.group(1))))
            except ValueError:
                return fallback

        def _test_asset(self, path):
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Asset Tester - {}".format(os.path.basename(path)))
            layout = QtWidgets.QVBoxLayout(dialog)
            preview = QtWidgets.QLabel(dialog)
            pixmap = QtGui.QPixmap(path)
            if pixmap.width() > 320:
                pixmap = pixmap.scaledToWidth(320, QtCore.Qt.TransformationMode.SmoothTransformation)
            preview.setPixmap(pixmap)
            preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(preview)
            row = QtWidgets.QHBoxLayout()
            row.addWidget(QtWidgets.QLabel("Similarity:", dialog))
            slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, dialog)
            slider.setRange(50, 99)
            start = int(round(self._similarity_for(os.path.basename(path)) * 100))
            slider.setValue(start)
            value_label = QtWidgets.QLabel("{:.2f}".format(start / 100.0), dialog)
            slider.valueChanged.connect(lambda v: value_label.setText("{:.2f}".format(v / 100.0)))
            row.addWidget(slider, 1)
            row.addWidget(value_label)
            layout.addLayout(row)
            result = QtWidgets.QLabel("Press Find on Screen to test at the current similarity.", dialog)
            result.setWordWrap(True)
            layout.addWidget(result)
            buttons = QtWidgets.QHBoxLayout()
            find_button = QtWidgets.QPushButton("Find on Screen", dialog)
            insert_button = QtWidgets.QPushButton("Insert Pattern", dialog)
            buttons.addWidget(find_button)
            buttons.addWidget(insert_button)
            layout.addLayout(buttons)

            def job(similarity):
                from ..compat import sikuli
                return sikuli.exists(sikuli.Pattern(path).similar(similarity), 0)

            def find_ok(match):
                dialog.show()
                self.show()
                find_button.setEnabled(True)
                if match is None:
                    result.setText("Not found at similarity {:.2f}. Try lowering it.".format(slider.value() / 100.0))
                    return
                target = match.getTarget()
                result.setText("Found at ({}, {}) with score {:.2f}. A red box marks it on screen.".format(target.x, target.y, match.getScore()))
                self._show_highlight([QtCore.QRect(match.x, match.y, match.w, match.h)])

            def find_err(exc):
                dialog.show()
                self.show()
                find_button.setEnabled(True)
                result.setText("Search failed: {}".format(exc))

            def run_find():
                find_button.setEnabled(False)
                similarity = slider.value() / 100.0
                dialog.hide()
                self.hide()
                QtCore.QTimer.singleShot(180, lambda: watch(qt, spawn(lambda: job(similarity)), find_ok, find_err))

            def insert_pattern():
                editor = self.current_editor()
                if editor is not None:
                    name = os.path.basename(path)
                    var = self._pattern_var(name)
                    editor.insert_snippet('{} = Pattern("{}").similar({:.2f})'.format(var, name, slider.value() / 100.0))

            find_button.clicked.connect(run_find)
            insert_button.clicked.connect(insert_pattern)
            dialog.show()
            self._help_windows.append(dialog)

        def closeEvent(self, event):
            modified = any(self._tabs.widget(i).document().isModified() for i in range(self._tabs.count()))
            if modified:
                buttons = QtWidgets.QMessageBox.StandardButton
                choice = QtWidgets.QMessageBox.question(self, "Unsaved changes", "Discard unsaved changes?", buttons.Yes | buttons.No)
                if choice != buttons.Yes:
                    event.ignore()
                    return
            self._settings.setValue("geometry", self.saveGeometry())
            self._settings.setValue("state", self.saveState(2))
            self._spy.shutdown()
            self._terminal.shutdown()
            if self._build_process is not None:
                try:
                    self._build_process.kill()
                except Exception:
                    pass
            self._engine.stop()
            event.accept()

    return MainWindow


def _selftest_lines():
    from ..core.os_facade.base import OSFacadeFactory, Rect
    from ..core.inspector.base import InspectorFactory
    from ..packaging.runtime_paths import configured_ocr, docs_path, examples_dir, tessdata_dir, tesseract_cmd
    lines = []

    def probe(name, fn):
        try:
            lines.append("[ok] {}: {}".format(name, fn()))
        except Exception as exc:
            lines.append("[fail] {}: {}".format(name, exc))

    def ocr_probe():
        import numpy as np
        import cv2
        canvas = np.full((60, 300), 255, np.uint8)
        cv2.putText(canvas, "TEST 123", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 2)
        return repr(configured_ocr().read_text(canvas))

    def import_probe(name):
        probe("import " + name, lambda: bool(__import__(name)))

    def uia_probe():
        import comtypes.client
        comtypes.client.gen_dir = None
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen.UIAutomationClient import CUIAutomation
        return bool(CUIAutomation)

    for module_name in ("win32gui", "win32api", "win32con", "win32process", "mss", "comtypes", "comtypes.client"):
        import_probe(module_name)
    probe("uia_codegen", uia_probe)
    for module_name in ("pywinauto", "pywinauto.mouse", "pywinauto.keyboard"):
        import_probe(module_name)
    probe("backend", lambda: type(OSFacadeFactory.create()).__name__)
    probe("cursor", lambda: OSFacadeFactory.create().cursor_position())
    probe("capture", lambda: getattr(OSFacadeFactory.create().capture(Rect(0, 0, 40, 40)), "shape", None))
    probe("inspector", lambda: type(InspectorFactory.create()).__name__)
    probe("element_at", lambda: InspectorFactory.create().element_at(100, 100))
    probe("tesseract_cmd", tesseract_cmd)
    probe("tessdata_dir", tessdata_dir)
    probe("ocr_read", ocr_probe)
    probe("docs", lambda: (docs_path("TUTORIAL.md"), docs_path("KILAVUZ.md")))
    probe("examples", examples_dir)
    return lines


def run_selftest(args):
    index = args.index("--selftest")
    target = args[index + 1] if index + 1 < len(args) else os.path.join(os.getcwd(), "rpastudio_selftest.txt")
    lines = _selftest_lines()
    with open(target, "w", encoding="ascii", errors="replace") as handle:
        handle.write("\n".join(lines) + "\n")
    return 0 if all(line.startswith("[ok]") for line in lines) else 1


def main(argv=None):
    multiprocessing.freeze_support()
    args = sys.argv if argv is None else list(argv)
    if "--selftest" in args:
        return run_selftest(args)
    qt = load_qt()
    app = qt.QtWidgets.QApplication(sys.argv if argv is None else list(argv))
    app.setApplicationName("RPA Studio")
    app.setOrganizationName("RPAFramework")
    apply_theme(app)
    app.setWindowIcon(logo_icon(qt))
    window = build_main_window_class(qt)()
    for arg in (sys.argv if argv is None else list(argv))[1:]:
        if os.path.isfile(arg):
            window.open_path(arg)
            break
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
