import keyword
import os
import queue
import re
import shutil
import threading

from .qt_shim import cached_builder
from .theme import COLORS, make_icon, python_icon

CONSOLE_COLORS = {
    "stdout": COLORS["text"],
    "stderr": COLORS["error"],
    "event": COLORS["ok"],
    "pass": COLORS["ok"],
    "started": COLORS["info"],
    "finished": COLORS["info"],
    "exit": COLORS["info"],
    "tool": COLORS["warn"],
}

_TRANSLIT = {
    "\u00e7": "c", "\u00c7": "c", "\u011f": "g", "\u011e": "g", "\u0131": "i", "\u0130": "i",
    "\u00f6": "o", "\u00d6": "o", "\u015f": "s", "\u015e": "s", "\u00fc": "u", "\u00dc": "u",
}
_SLUG_RE = re.compile(r"[^a-z0-9]+")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp")
VK_RBUTTON = 0x02


def slugify(text, fallback="item", limit=3):
    text = "".join(_TRANSLIT.get(ch, ch) for ch in str(text or ""))
    parts = [p for p in _SLUG_RE.split(text.lower()) if p]
    if not parts:
        return fallback
    return "_".join(parts[:limit])


def element_var(data):
    name = slugify(data.get("name") or data.get("automation_id") or "", "", limit=3)
    role = slugify(data.get("role") or "", "", limit=1)
    if role and (not name or not name.endswith(role)):
        name = (name + "_" + role) if name else role
    var = name or "element"
    if var[0].isdigit():
        var = "el_" + var
    if keyword.iskeyword(var):
        var = var + "_el"
    return var


_SPY_ACTIONS = (
    ("just the variable", None, None),
    ("click", "{v}.click()", None),
    ("double-click", "{v}.doubleClick()", None),
    ("right-click", "{v}.rightClick()", None),
    ("type text", '{v}.type("{a}")', "Text to type"),
    ("clear the field", "{v}.clear()", None),
    ("set text (clear then type)", '{v}.setText("{a}")', "New text"),
    ("get the text", "print({v}.getText())", None),
    ("check the box", "{v}.check()", None),
    ("uncheck the box", "{v}.uncheck()", None),
    ("open combo and select", '{v}.select("{a}")', "Item to pick"),
    ("select item in a list", '{v}.selectItem("{a}")', "Item to pick"),
)


def sikuli_main_script(folder):
    if not os.path.isdir(folder) or not folder.lower().endswith(".sikuli"):
        return None
    stem = os.path.splitext(os.path.basename(folder))[0]
    preferred = os.path.join(folder, stem + ".py")
    if os.path.isfile(preferred):
        return preferred
    scripts = sorted(n for n in os.listdir(folder) if n.endswith(".py"))
    return os.path.join(folder, scripts[0]) if scripts else None


def right_pressed():
    if os.name != "nt":
        return False
    try:
        import win32api
        return bool(win32api.GetAsyncKeyState(VK_RBUTTON) & 0x8000)
    except Exception:
        return False

API_REFERENCE = (
    ("Mouse", (
        ("click", 'click("image.png")', "Find the picture on screen and left-click its center"),
        ("doubleClick", 'doubleClick("image.png")', "Double-click the found picture"),
        ("rightClick", 'rightClick("image.png")', "Right-click the found picture"),
        ("hover", 'hover("image.png")', "Move the mouse onto the found picture"),
        ("click at point", "click(Location(100, 200))", "Click exact screen coordinates"),
        ("dragDrop", 'dragDrop("from.png", "to.png")', "Drag the first target onto the second"),
        ("wheel", "wheel(WHEEL_DOWN, 3)", "Scroll 3 notches (WHEEL_UP to scroll up)"),
        ("mouseDown / mouseUp", "mouseDown()", "Press or release a mouse button manually"),
    )),
    ("Keyboard", (
        ("type", 'type("hello" + Key.ENTER)', "Type text; Key.* constants press special keys"),
        ("type shortcut", 'type("s", KeyModifier.CTRL)', "Press a key combination like Ctrl+S"),
        ("paste", 'paste("some long text")', "Paste text through the clipboard"),
        ("keyDown / keyUp", "keyDown(Key.SHIFT)", "Hold or release a key"),
    )),
    ("Finding pictures", (
        ("wait", 'wait("dialog.png", 10)', "Wait up to 10s for the picture, error if missing"),
        ("exists", 'exists("popup.png", 3)', "Like wait but returns None instead of failing"),
        ("waitVanish", 'waitVanish("spinner.png", 30)', "Wait until the picture disappears"),
        ("find", 'match = find("logo.png")', "Find now; returns a Match with location and score"),
        ("findAll", 'for m in findAll("row.png"):', "Every place the picture appears"),
        ("Pattern", 'Pattern("btn.png").similar(0.9)', "Tune strictness; .targetOffset(dx, dy) shifts the click"),
        ("Region", "Region(0, 0, 800, 600)", "Limit searching to part of the screen"),
        ("Location", "Location(500, 300)", "An exact screen point; capture one with the Location tool"),
        ("Offset", "Offset(10, -4)", "A relative shift; Pattern(p).targetOffset(Offset(10, -4)) nudges the click"),
        ("autoScroll", 'click("row.png", autoScroll=True)', "Scroll down/right and rescan when the target is below the fold; also works on wait()"),
    )),
    ("Dynamic regions", (
        ("nearby", "match.nearby(50)", "Grow a region or match by 50px in every direction"),
        ("above / below", "match.above(120)", "The strip above (or below); no argument extends to the screen edge"),
        ("left / right", "match.right(200)", "The strip left (or right); no argument extends to the screen edge"),
        ("union", "r1.union(r2)", "Smallest region covering both regions"),
        ("intersection", "r1.intersection(r2)", "Overlap of two regions, or None"),
        ("setROI", "reg.setROI(0, 0, 800, 600)", "Move and resize the region in place"),
        ("chained search", 'click(find("label.png").right(150))', "Find something relative to an anchor and act on it"),
    )),
    ("Windows and elements", (
        ("openApp", 'app = openApp("notepad.exe")', "Start a program and get an App handle bound to its process"),
        ("switchApp", 'switchApp("notepad")', "Focus a window by title OR process name; contains=False for exact title"),
        ("closeApp", 'closeApp("Notepad")', "Close a window's process by title"),
        ("App", 'app = App("Notepad")', "A program handle: .open() .focus() .close() .window() .isRunning(); tracks the launched pid"),
        ("window controls", 'app.window().moveTo(0, 0).resize(800, 600)', "Also .maximize() .minimize() .restore() .setBounds() .focus()"),
        ("windowRegion", 'windowRegion("Notepad").find("save.png")', "A region glued to a window; follows it when it moves"),
        ("highlight", 'find("logo.png").highlight(2)', "Flash a red frame around a region, match or element on the real screen"),
        ("findElement", 'btn = findElement(name="OK", role="Button")', "Find a UI element (Element Spy writes these); result has .click() .type() .clear() .setText() .getText() .check() .uncheck() .select() .selectItem() .child()"),
        ("findElement in a window", 'findElement(name="Fire", window="Weapon Control")', "Search ONLY inside that window's controls - never another app; add region=... or timeout=5 too"),
        ("Target", 'Target(name="Fire", window="Console", image="fire.png", text="FIRE").click()', "Multi-anchor self-healing locator: OS element first, then the image, then OCR text; remembers what worked"),
        ("findUI", 'findUI("button", text="OK")', "Vision-only control detection for VDI or streamed desktops with no accessibility tree"),
        ("element.type", 'box.setText("hello")', "Clear a field and type into it (.type appends, .clear empties it)"),
        ("element.check", "agree.check()", "Tick a checkbox (.uncheck unticks, .isChecked reads it)"),
        ("element.select", 'combo.select("Option 2")', "Open a combo box and pick an item by name"),
        ("element.selectItem", 'listbox.selectItem("Row 3")', "Pick a row/item by name inside a list or tree"),
        ("clickElement", 'clickElement(name="OK", role="Button")', "Find a UI element and click its center"),
    )),
    ("Screen text (OCR)", (
        ("read region", "Region(0, 0, 800, 200).text()", "Read the text inside a screen area"),
        ("OCR engine", "engine = configured_ocr()", "Full OCR engine with word boxes and languages"),
    )),
    ("System (Env and Settings)", (
        ("Env.getClipboard", "text = Env.getClipboard()", "Read the clipboard text"),
        ("Env.setClipboard", 'Env.setClipboard("hello")', "Put text on the clipboard"),
        ("Env.getMouseLocation", "loc = Env.getMouseLocation()", "Where the mouse is right now"),
        ("Env.getScreenSize", "screen = Env.getScreenSize()", "The full screen as a Region"),
        ("Env.getOS", "Env.getOS()", "Windows / Linux; also isWindows() isLinux() isMac() getOSVersion()"),
        ("Settings.MinSimilarity", "Settings.MinSimilarity = 0.8", "Global matching strictness"),
        ("Settings.ClickDelay", "Settings.ClickDelay = 0.3", "Pause before every click; also MoveMouseDelay TypeDelay"),
        ("Settings.DelayBeforeDrag", "Settings.DelayBeforeDrag = 0.5", "dragDrop timing; also DelayBeforeMouseDown DelayBeforeDrop"),
        ("Settings.DefaultHighlightTime", "Settings.DefaultHighlightTime = 3", "How long highlight() stays visible"),
        ("Settings.OcrLanguage", 'Settings.OcrLanguage = "eng_best"', "OCR model for Region.text(); bundled: eng, eng_best, tur, dejavu_sans"),
    )),
    ("Flow and output", (
        ("sleep", "sleep(2)", "Wait a number of seconds"),
        ("popup", 'popup("done!")', "Show a message box"),
        ("emit", 'emit("stage", "login ok")', "Send a status event to the IDE console"),
        ("passed", 'passed("login ok")', "Green success line in the Output panel"),
        ("failed", 'failed("button missing")', "Red line plus an automatic clickable screenshot in the Output panel"),
        ("pause point", "wait_if_paused()", "Let the IDE Pause button take hold inside loops"),
        ("async main", "async def main(): ...", "Awaited automatically; use await checkpoint()"),
        ("Settings", "Settings.MinSimilarity = 0.8", "Global matching and timeout defaults"),
    )),
)


def spawn(fn):
    box = queue.Queue()

    def work():
        try:
            box.put(("ok", fn()))
        except Exception as exc:
            box.put(("err", exc))

    threading.Thread(target=work, daemon=True).start()
    return box


def watch(qt, box, on_ok, on_err):
    def check():
        try:
            status, value = box.get_nowait()
        except queue.Empty:
            qt.QtCore.QTimer.singleShot(50, check)
            return
        if status == "ok":
            on_ok(value)
        else:
            on_err(value)

    qt.QtCore.QTimer.singleShot(50, check)


@cached_builder
def build_panels(qt):
    QtCore, QtGui, QtWidgets, Signal = qt.QtCore, qt.QtGui, qt.QtWidgets, qt.Signal
    fs_model_class = getattr(QtGui, "QFileSystemModel", None) or getattr(QtWidgets, "QFileSystemModel", None)
    provider_class = getattr(QtWidgets, "QFileIconProvider", None) or getattr(QtGui, "QFileIconProvider", None)

    class FileIcons(provider_class):
        def icon(self, info):
            try:
                if hasattr(info, "suffix"):
                    if info.isDir():
                        if info.fileName().lower().endswith(".sikuli"):
                            return make_icon(qt, "build")
                        return provider_class.icon(self, info)
                    suffix = info.suffix().lower()
                    if suffix == "py":
                        badge = python_icon(qt)
                        return badge if badge is not None else make_icon(qt, "run")
                    if suffix in ("png", "jpg", "jpeg", "bmp"):
                        return make_icon(qt, "image")
                    if suffix == "md":
                        return make_icon(qt, "book")
                    if suffix in ("txt", "json", "cfg", "ini", "log"):
                        return make_icon(qt, "new")
            except Exception:
                pass
            return provider_class.icon(self, info)

    class FilesPanel(QtWidgets.QWidget):
        fileActivated = Signal(str)
        imageActivated = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._clip = None
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self._label = QtWidgets.QLabel("", self)
            self._label.setStyleSheet("padding: 6px 8px; color: {}; background: {};".format(COLORS["dim"], COLORS["panel"]))
            self._tree = QtWidgets.QTreeView(self)
            self._tree.setHeaderHidden(True)
            self._model = fs_model_class(self)
            self._model.setNameFilters(["*.py", "*.png", "*.jpg", "*.bmp", "*.md"])
            self._model.setNameFilterDisables(False)
            self._model.setReadOnly(False)
            try:
                self._icons = FileIcons()
                self._model.setIconProvider(self._icons)
            except Exception:
                pass
            self._tree.setModel(self._model)
            self._tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed)
            self._tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self._tree.customContextMenuRequested.connect(self._menu)
            self._tree.setDragEnabled(True)
            self._tree.viewport().setAcceptDrops(True)
            self._tree.setDropIndicatorShown(True)
            self._tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
            self._tree.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
            for column in range(1, 4):
                self._tree.hideColumn(column)
            self._tree.doubleClicked.connect(self._activated)
            bar = QtWidgets.QHBoxLayout()
            bar.setContentsMargins(4, 2, 4, 2)
            bar.setSpacing(2)
            for icon, tip, slot in (
                ("new", "New file", lambda: self._create(self._tree.currentIndex(), False)),
                ("folder", "New folder", lambda: self._create(self._tree.currentIndex(), True)),
                ("camera", "New .sikuli folder", lambda: self._create_sikuli(self._tree.currentIndex())),
                ("refresh", "Refresh", self._refresh),
                ("expand", "Expand all", lambda: self._tree.expandAll()),
                ("collapse", "Collapse all", lambda: self._tree.collapseAll()),
                ("open", "Choose folder", self._choose_root),
            ):
                button = QtWidgets.QToolButton(self)
                button.setIcon(make_icon(qt, icon))
                button.setToolTip(tip)
                button.clicked.connect(lambda checked=False, s=slot: s())
                bar.addWidget(button)
            bar.addStretch(1)
            for sequence, slot in (
                (QtGui.QKeySequence.StandardKey.Delete, lambda: self._delete(self._tree.currentIndex())),
                (QtGui.QKeySequence.StandardKey.Copy, lambda: self._copy(self._tree.currentIndex())),
                (QtGui.QKeySequence.StandardKey.Paste, lambda: self._paste(self._tree.currentIndex())),
            ):
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(sequence), self._tree)
                shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
                shortcut.activated.connect(slot)
            layout.addWidget(self._label)
            layout.addLayout(bar)
            layout.addWidget(self._tree)

        def set_root(self, path):
            if not path or not os.path.isdir(path):
                return
            self._label.setText(os.path.basename(path) or path)
            self._label.setToolTip(path)
            self._model.setRootPath(path)
            self._tree.setRootIndex(self._model.index(path))

        def root_path(self):
            return self._model.filePath(self._tree.rootIndex())

        def _activated(self, index):
            path = self._model.filePath(index)
            if os.path.isdir(path):
                script = sikuli_main_script(path)
                if script:
                    self.fileActivated.emit(script)
                return
            ext = os.path.splitext(path)[1].lower()
            if ext in (".py", ".md"):
                self.fileActivated.emit(path)
            elif ext in IMAGE_EXTS:
                self.imageActivated.emit(path)

        def _menu(self, point):
            index = self._tree.indexAt(point)
            menu = QtWidgets.QMenu(self._tree)
            entries = (
                ("New File...", lambda: self._create(index, False), True),
                ("New Folder...", lambda: self._create(index, True), True),
                ("New Sikuli Folder...", lambda: self._create_sikuli(index), True),
                (None, None, None),
                ("Rename", lambda: self._rename(index), index.isValid()),
                ("Delete", lambda: self._delete(index), index.isValid()),
                (None, None, None),
                ("Copy", lambda: self._copy(index), index.isValid()),
                ("Paste", lambda: self._paste(index), bool(self._clip)),
                (None, None, None),
                ("Copy Full Path", lambda: self._copy_path(index), index.isValid()),
                ("Reveal in File Explorer", lambda: self._reveal(index), index.isValid()),
                (None, None, None),
                ("Choose Folder...", self._choose_root, True),
            )
            for label, slot, enabled in entries:
                if label is None:
                    menu.addSeparator()
                    continue
                action = menu.addAction(label)
                action.setEnabled(bool(enabled))
                action.triggered.connect(lambda checked=False, s=slot: s())
            menu.exec(self._tree.viewport().mapToGlobal(point))

        def _dir_for(self, index):
            if index.isValid():
                path = self._model.filePath(index)
                return path if os.path.isdir(path) else os.path.dirname(path)
            return self.root_path() or os.getcwd()

        def _warn(self, title, exc):
            QtWidgets.QMessageBox.warning(self, title, str(exc))

        def _create(self, index, folder):
            base = self._dir_for(index)
            title = "New Folder" if folder else "New File"
            hint = "new_folder" if folder else "new_script.py"
            name, ok = QtWidgets.QInputDialog.getText(self, title, "Name:", text=hint)
            if not ok or not name.strip():
                return
            path = os.path.join(base, name.strip())
            try:
                if folder:
                    os.makedirs(path, exist_ok=True)
                elif not os.path.exists(path):
                    with open(path, "w", encoding="ascii") as handle:
                        handle.write("")
            except Exception as exc:
                self._warn(title + " failed", exc)

        def _create_sikuli(self, index):
            base = self._dir_for(index)
            name, ok = QtWidgets.QInputDialog.getText(self, "New Sikuli Folder", "Name (without .sikuli):", text="my_flow")
            if not ok or not name.strip():
                return
            stem = name.strip().replace(".sikuli", "")
            folder = os.path.join(base, stem + ".sikuli")
            script = os.path.join(folder, stem + ".py")
            try:
                os.makedirs(folder, exist_ok=True)
                if not os.path.exists(script):
                    with open(script, "w", encoding="ascii") as handle:
                        handle.write('popup("hello from {}")\n'.format(stem))
            except Exception as exc:
                self._warn("New Sikuli Folder failed", exc)
                return
            self.fileActivated.emit(script)

        def _rename(self, index):
            if index.isValid():
                self._tree.edit(index)

        def _delete(self, index):
            if not index.isValid():
                return
            path = self._model.filePath(index)
            buttons = QtWidgets.QMessageBox.StandardButton
            question = "Delete {}?".format(os.path.basename(path))
            if QtWidgets.QMessageBox.question(self, "Delete", question, buttons.Yes | buttons.No) != buttons.Yes:
                return
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as exc:
                self._warn("Delete failed", exc)

        def _copy(self, index):
            if index.isValid():
                self._clip = self._model.filePath(index)

        def _paste(self, index):
            source = self._clip
            if not source or not os.path.exists(source):
                return
            target = self._unique(os.path.join(self._dir_for(index), os.path.basename(source)))
            try:
                if os.path.isdir(source):
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
            except Exception as exc:
                self._warn("Paste failed", exc)

        def _unique(self, path):
            if not os.path.exists(path):
                return path
            stem, ext = os.path.splitext(path)
            index = 1
            while os.path.exists("{}_copy{}{}".format(stem, index, ext)):
                index += 1
            return "{}_copy{}{}".format(stem, index, ext)

        def _choose_root(self):
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose Folder", self.root_path() or os.path.expanduser("~"))
            if path:
                self.set_root(path)

        def _refresh(self):
            root = self.root_path()
            if root:
                self._model.setRootPath("")
                self.set_root(root)

        def _copy_path(self, index):
            if index.isValid():
                QtWidgets.QApplication.clipboard().setText(os.path.normpath(self._model.filePath(index)))

        def _reveal(self, index):
            if not index.isValid():
                return
            path = self._model.filePath(index)
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            try:
                if os.name == "nt":
                    os.startfile(folder)
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", folder])
            except Exception:
                pass

    class SpyPanel(QtWidgets.QWidget):
        insertRequested = Signal(str)
        _FIELDS = ("role", "name", "automation_id", "class_name", "bounding_box", "process_id")

        def __init__(self, parent=None):
            super().__init__(parent)
            self._daemon = None
            self._queue = queue.Queue()
            self._element = None
            self._timer = QtCore.QTimer(self)
            self._timer.setInterval(150)
            self._timer.timeout.connect(self._drain)
            self._hot_prev = False
            self._scraping = False
            self._pid_window = {}
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            scroll = QtWidgets.QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            inner = QtWidgets.QWidget(self)
            scroll.setWidget(inner)
            outer.addWidget(scroll)
            columns = QtWidgets.QHBoxLayout(inner)
            columns.setContentsMargins(8, 6, 8, 6)
            columns.setSpacing(12)
            layout = QtWidgets.QVBoxLayout()
            layout.setSpacing(4)
            right_column = QtWidgets.QVBoxLayout()
            right_column.setSpacing(4)
            columns.addLayout(layout, 1)
            columns.addLayout(right_column, 1)
            steps = QtWidgets.QLabel("Start watching, hover any control in any app, then RIGHT-CLICK it (or press Insert) to drop it into the script as a variable.", self)
            steps.setWordWrap(True)
            steps.setStyleSheet("color: {};".format(COLORS["dim"]))
            layout.addWidget(steps)
            self._toggle = QtWidgets.QPushButton("Start watching", self)
            self._toggle.setCheckable(True)
            self._toggle.setProperty("primary", True)
            self._toggle.toggled.connect(self._toggled)
            layout.addWidget(self._toggle)
            self._raw = QtWidgets.QCheckBox("Raw tree deep scan (Electron / web apps)", self)
            self._raw.setToolTip("Hit-test through container layers down to the smallest element under the cursor. Applies the next time you press Start watching.")
            layout.addWidget(self._raw)
            caption = QtWidgets.QLabel("Element under the cursor:", self)
            caption.setStyleSheet("color: {};".format(COLORS["dim"]))
            right_column.addWidget(caption)
            self._preview = QtWidgets.QLabel("Start watching, then hover a control.", self)
            self._preview.setWordWrap(True)
            self._preview.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            self._preview.setStyleSheet("background: {}; color: {}; border: 1px solid {}; border-radius: 6px; padding: 6px; font-family: Consolas;".format(COLORS["panel3"], COLORS["ok"], COLORS["border"]))
            right_column.addWidget(self._preview)
            action_row = QtWidgets.QHBoxLayout()
            action_label = QtWidgets.QLabel("Action:", self)
            action_label.setStyleSheet("color: {};".format(COLORS["dim"]))
            action_row.addWidget(action_label)
            self._action = QtWidgets.QComboBox(self)
            for label, _template, _prompt in _SPY_ACTIONS:
                self._action.addItem(label)
            self._action.setToolTip("What to do with the element. The line(s) are inserted when you press Space or Insert.")
            self._action.currentIndexChanged.connect(self._refresh_preview)
            action_row.addWidget(self._action, 1)
            layout.addLayout(action_row)
            self._insert = QtWidgets.QPushButton("Insert element + action  (or right-click)", self)
            self._insert.setProperty("primary", True)
            self._insert.setEnabled(False)
            self._insert.clicked.connect(self._capture_element)
            layout.addWidget(self._insert)
            form = QtWidgets.QFormLayout()
            form.setContentsMargins(0, 6, 0, 0)
            self._values = {}
            for field in self._FIELDS:
                value = QtWidgets.QLabel("-", self)
                value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
                value.setWordWrap(True)
                title = QtWidgets.QLabel(field.replace("_", " ") + ":", self)
                title.setStyleSheet("color: {};".format(COLORS["dim"]))
                form.addRow(title, value)
                self._values[field] = value
            right_column.addLayout(form)
            right_column.addStretch(1)
            self._scrape = QtWidgets.QPushButton("Scrape whole active window (3s delay)", self)
            self._scrape.setToolTip("Click, then focus the target window; after 3 seconds every named element is inserted as a variable with a findElement locator.")
            self._scrape.clicked.connect(self._start_scrape)
            layout.addWidget(self._scrape)
            layout.addStretch(1)

        def _toggled(self, active):
            if active:
                self._toggle.setEnabled(False)
                self._toggle.setText("Starting...")
                watch(qt, spawn(self._make_daemon), self._started, self._failed)
            else:
                self._timer.stop()
                daemon = self._daemon
                self._daemon = None
                if daemon is not None:
                    spawn(daemon.stop)
                self._toggle.setText("Start watching")
                self._insert.setEnabled(False)
                self._preview.setText("Start watching, then hover a control.")

        def _make_daemon(self):
            from ..core.inspector.daemon import InspectorDaemon
            return InspectorDaemon(interval=0.25, on_element=lambda element: self._queue.put(element.to_dict()), deep=self._raw.isChecked())

        def _started(self, daemon):
            self._toggle.setEnabled(True)
            if not self._toggle.isChecked():
                spawn(daemon.stop)
                return
            self._daemon = daemon
            daemon.start()
            self._timer.start()
            self._toggle.setText("Watching - hover a control, right-click")
            self._preview.setText("Watching. Hover any control in any app.")

        def _failed(self, exc):
            self._toggle.setEnabled(True)
            self._toggle.setChecked(False)
            self._preview.setText("Inspector unavailable: {}".format(exc))

        def _drain(self):
            hot = right_pressed()
            if hot and not self._hot_prev and self._element:
                self._capture_element()
            self._hot_prev = hot
            data = None
            while True:
                try:
                    data = self._queue.get_nowait()
                except queue.Empty:
                    break
            if data is None:
                return
            self._element = data
            for field in self._FIELDS:
                value = data.get(field)
                self._values[field].setText(str(value) if value not in (None, "", ()) else "-")
            self._refresh_preview()

        def _refresh_preview(self):
            line = self._pending_line()
            if line:
                self._preview.setText(line)
                self._insert.setEnabled(True)
            elif self._element:
                self._preview.setText("This control has no name or id - move onto a labeled one.")
                self._insert.setEnabled(False)
            else:
                self._preview.setText("Start watching, then hover a control.")
                self._insert.setEnabled(False)

        def _action_line(self, var, arg_provider):
            label, template, prompt = _SPY_ACTIONS[self._action.currentIndex()]
            if not template:
                return ""
            arg = arg_provider(prompt) if prompt else ""
            return template.format(v=var, a=arg)

        def _pending_line(self):
            if not self._element:
                return ""
            window = self._window_title(self._element.get("process_id"))
            locator = self._locator(self._element, "findElement", window)
            if not locator:
                return ""
            if not locator.startswith("findElement"):
                return locator
            var = element_var(self._element)
            line = "{} = {}".format(var, locator)
            action = self._action_line(var, lambda prompt: "...")
            return line + "\n" + action if action else line

        @staticmethod
        def _locator(data, call, window=None):
            parts = []
            for key in ("automation_id", "name", "role"):
                value = data.get(key)
                if value:
                    parts.append("{}={!r}".format(key, value))
            if parts:
                if window:
                    parts.append("window={!r}".format(window))
                return "{}({})".format(call, ", ".join(parts))
            box = data.get("bounding_box")
            if box:
                x, y, w, h = box
                return "click(Location({}, {}))".format(x + w // 2, y + h // 2)
            return None

        def _window_title(self, pid):
            if not pid:
                return None
            if pid not in self._pid_window:
                title = None
                try:
                    from ..core.os_facade.base import OSFacadeFactory
                    for handle in OSFacadeFactory.create().list_windows():
                        if handle.pid == pid and handle.title:
                            title = handle.title
                            break
                except Exception:
                    title = None
                self._pid_window[pid] = title
            return self._pid_window[pid]

        def _capture_element(self):
            if not self._element:
                return
            window = self._window_title(self._element.get("process_id"))
            locator = self._locator(self._element, "findElement", window)
            if not locator:
                return
            if not locator.startswith("findElement"):
                self.insertRequested.emit(locator)
                return
            var = element_var(self._element)
            line = "{} = {}".format(var, locator)
            action = self._action_line(var, self._ask_arg)
            if action:
                line = line + "\n" + action
            self.insertRequested.emit(line)
            self._preview.setText("Inserted:  " + line.replace("\n", "   ->   "))

        def _ask_arg(self, prompt):
            text, ok = QtWidgets.QInputDialog.getText(self, "Action value", prompt + ":")
            return text if ok else ""

        def _start_scrape(self):
            if self._scraping:
                return
            self._scraping = True
            self._scrape.setEnabled(False)
            self._scrape.setText("Focus the target window...")
            QtCore.QTimer.singleShot(3000, self._run_scrape)

        def _run_scrape(self):
            self._scrape.setText("Scraping...")
            watch(qt, spawn(self._scrape_job), self._scrape_ok, self._scrape_err)

        def _scrape_job(self):
            from ..core.inspector.base import InspectorFactory
            from ..core.os_facade.base import OSFacadeFactory
            backend = OSFacadeFactory.create()
            active = backend.active_window()
            if active is None:
                raise RuntimeError("no active window found")
            inspector = InspectorFactory.create()
            target = None
            for child in inspector.children(inspector.root()):
                if child is not None and child.process_id == active.pid:
                    target = child
                    break
            if target is None:
                raise RuntimeError("could not reach the active window through accessibility")
            prefix = slugify(active.title, "window")
            lines = []
            seen = {}
            count = 0
            for node in inspector.walk(target, max_depth=24):
                count += 1
                if count > 400 or len(lines) >= 120:
                    break
                label = node.name or node.automation_id
                if not label or node.bounding_box is None:
                    continue
                stem = slugify(label, "", limit=4)
                if not stem:
                    continue
                role_slug = slugify(node.role, "", limit=1)
                if role_slug and not stem.endswith(role_slug):
                    stem = stem + "_" + role_slug
                name = prefix + "_" + stem
                seen[name] = seen.get(name, 0) + 1
                if seen[name] > 1:
                    name = "{}_{}".format(name, seen[name])
                locator = self._locator(node.to_dict(), "findElement", active.title)
                if locator and locator.startswith("findElement"):
                    lines.append("{} = {}".format(name, locator))
            if not lines:
                raise RuntimeError("no named elements found in the active window")
            return "\n".join(lines)

        def _scrape_done(self):
            self._scraping = False
            self._scrape.setEnabled(True)
            self._scrape.setText("Scrape Active Window (3s delay)")

        def _scrape_ok(self, block):
            self._scrape_done()
            self.insertRequested.emit(block)

        def _scrape_err(self, exc):
            self._scrape_done()
            self._values["role"].setText("scrape failed: {}".format(exc))

        def shutdown(self):
            if self._toggle.isChecked():
                self._toggle.setChecked(False)

    class ReferencePanel(QtWidgets.QWidget):
        insertRequested = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)
            row = QtWidgets.QHBoxLayout()
            self._filter = QtWidgets.QLineEdit(self)
            self._filter.setPlaceholderText("Search commands...")
            self._filter.textChanged.connect(self._apply_filter)
            row.addWidget(self._filter, 1)
            for icon, tip, slot in (
                ("expand", "Expand all", lambda: self._tree.expandAll()),
                ("collapse", "Collapse all", lambda: self._tree.collapseAll()),
            ):
                button = QtWidgets.QToolButton(self)
                button.setIcon(make_icon(qt, icon))
                button.setToolTip(tip)
                button.clicked.connect(lambda checked=False, s=slot: s())
                row.addWidget(button)
            layout.addLayout(row)
            self._tree = QtWidgets.QTreeWidget(self)
            self._tree.setHeaderHidden(True)
            self._tree.itemDoubleClicked.connect(self._activated)
            layout.addWidget(self._tree)
            hint = QtWidgets.QLabel("Double-click a command to insert it into the script.", self)
            hint.setWordWrap(True)
            hint.setStyleSheet("color: {};".format(COLORS["dim"]))
            layout.addWidget(hint)
            self._populate()

        def _populate(self):
            for category, entries in API_REFERENCE:
                top = QtWidgets.QTreeWidgetItem([category])
                self._tree.addTopLevelItem(top)
                for name, snippet, description in entries:
                    child = QtWidgets.QTreeWidgetItem([name])
                    child.setToolTip(0, "{}\n\n{}".format(snippet, description))
                    child.setData(0, QtCore.Qt.ItemDataRole.UserRole, snippet)
                    top.addChild(child)
                top.setExpanded(True)

        def _apply_filter(self, text):
            needle = text.strip().lower()
            for i in range(self._tree.topLevelItemCount()):
                top = self._tree.topLevelItem(i)
                visible = 0
                for j in range(top.childCount()):
                    child = top.child(j)
                    match = not needle or needle in child.text(0).lower() or needle in (child.data(0, QtCore.Qt.ItemDataRole.UserRole) or "").lower()
                    child.setHidden(not match)
                    visible += 1 if match else 0
                top.setHidden(visible == 0)

        def _activated(self, item, column):
            snippet = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if snippet:
                self.insertRequested.emit(snippet)

    class ConsolePanel(QtWidgets.QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._fail_count = 0
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            bar = QtWidgets.QHBoxLayout()
            bar.setContentsMargins(4, 2, 4, 2)
            bar.addStretch(1)
            clear = QtWidgets.QToolButton(self)
            clear.setIcon(make_icon(qt, "clear"))
            clear.setToolTip("Clear output")
            clear.clicked.connect(self.clear)
            bar.addWidget(clear)
            layout.addLayout(bar)
            self._view = QtWidgets.QTextBrowser(self)
            self._view.setReadOnly(True)
            self._view.setOpenLinks(False)
            self._view.anchorClicked.connect(self._show_fail)
            font = QtGui.QFont("Consolas")
            font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
            font.setPointSize(10)
            self._view.setFont(font)
            layout.addWidget(self._view)

        def _end_cursor(self):
            cursor = self._view.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            return cursor

        def _trim(self):
            document = self._view.document()
            extra = document.blockCount() - 8000
            if extra <= 0:
                return
            cursor = QtGui.QTextCursor(document)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextBlock, QtGui.QTextCursor.MoveMode.KeepAnchor, extra)
            cursor.removeSelectedText()

        def append(self, text, kind="stdout"):
            cursor = self._end_cursor()
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor(CONSOLE_COLORS.get(kind, COLORS["text"])))
            cursor.insertText(str(text), fmt)
            self._view.setTextCursor(cursor)
            self._trim()

        def append_fail(self, message, image_path=None):
            self.append("[fail] {}\n".format(message), "stderr")
            if not image_path:
                return
            try:
                image = QtGui.QImage(image_path)
                if image.isNull():
                    return
                name = "failshot_{}".format(self._fail_count)
                self._fail_count += 1
                self._view.document().addResource(QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(name), image)
                width = min(360, image.width())
                cursor = self._end_cursor()
                cursor.insertHtml('<a href="rpafail:{}"><img src="{}" width="{}"></a>'.format(name, name, width))
                cursor.insertText("\n")
                self._view.setTextCursor(cursor)
            except Exception:
                pass

        def _show_fail(self, url):
            if url.scheme() != "rpafail":
                return
            image = self._view.document().resource(QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(url.path()))
            if image is None:
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Failure Screenshot")
            layout = QtWidgets.QVBoxLayout(dialog)
            area = QtWidgets.QScrollArea(dialog)
            area.setWidgetResizable(True)
            label = QtWidgets.QLabel(dialog)
            label.setPixmap(QtGui.QPixmap.fromImage(image))
            area.setWidget(label)
            layout.addWidget(area)
            dialog.resize(980, 640)
            dialog.show()

        def clear(self):
            self._view.clear()
            self._fail_count = 0

        def toPlainText(self):
            return self._view.toPlainText()

    class WindowSpyPanel(QtWidgets.QWidget):
        insertRequested = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(4)
            row = QtWidgets.QHBoxLayout()
            refresh = QtWidgets.QPushButton("Refresh windows", self)
            refresh.clicked.connect(self.refresh)
            row.addWidget(refresh)
            hint = QtWidgets.QLabel("Every visible window with process, pid, id, position and size. Double-click a row to insert App(...).", self)
            hint.setWordWrap(True)
            hint.setStyleSheet("color: {};".format(COLORS["dim"]))
            row.addWidget(hint, 1)
            layout.addLayout(row)
            self._table = QtWidgets.QTableWidget(0, 6, self)
            self._table.setHorizontalHeaderLabels(["Title", "Process", "PID", "Window id", "Position", "Size"])
            self._table.horizontalHeader().setStretchLastSection(True)
            self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self._table.verticalHeader().setVisible(False)
            self._table.itemDoubleClicked.connect(self._activated)
            layout.addWidget(self._table)

        def refresh(self):
            def job():
                from ..core.os_facade.base import OSFacadeFactory
                backend = OSFacadeFactory.create()
                rows = []
                for handle in backend.list_windows():
                    try:
                        pname = backend.process_name(handle.pid) if handle.pid else ""
                    except Exception:
                        pname = ""
                    rows.append((handle.title, pname, handle.pid, handle.native_id, handle.rect))
                return rows

            watch(qt, spawn(job), self._fill, lambda exc: self._fill([]))

        def _fill(self, rows):
            self._table.setRowCount(len(rows))
            for i, (title, pname, pid, wid, rect) in enumerate(rows):
                pos = "{}, {}".format(rect.x, rect.y) if rect else "-"
                size = "{} x {}".format(rect.width, rect.height) if rect else "-"
                for col, value in enumerate((title, pname, pid or "-", wid, pos, size)):
                    item = QtWidgets.QTableWidgetItem(str(value))
                    if col == 0:
                        item.setData(QtCore.Qt.ItemDataRole.UserRole, (title, pname))
                    self._table.setItem(i, col, item)
            self._table.resizeColumnsToContents()

        def _activated(self, item):
            first = self._table.item(item.row(), 0)
            title, pname = first.data(QtCore.Qt.ItemDataRole.UserRole) or ("", "")
            target = title or pname
            if target:
                var = slugify(target, "app", limit=3)
                self.insertRequested.emit('{} = App("{}")'.format(var, target))

    class TerminalPanel(QtWidgets.QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._process = None
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self._view = QtWidgets.QPlainTextEdit(self)
            self._view.setReadOnly(True)
            font = QtGui.QFont("Consolas")
            font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
            font.setPointSize(10)
            self._view.setFont(font)
            self._input = QtWidgets.QLineEdit(self)
            self._input.setPlaceholderText("Type a command and press Enter")
            self._input.returnPressed.connect(self._send)
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(self._input, 1)
            external = QtWidgets.QToolButton(self)
            external.setIcon(make_icon(qt, "open"))
            external.setToolTip("Open the system terminal in the project folder")
            external.clicked.connect(lambda: self.open_external(self._workdir))
            row.addWidget(external)
            layout.addWidget(self._view, 1)
            layout.addLayout(row)
            self._workdir = None

        def start(self, workdir=None):
            if workdir:
                self._workdir = workdir
            if self._process is not None:
                return
            proc = QtCore.QProcess(self)
            proc.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
            if workdir and os.path.isdir(workdir):
                proc.setWorkingDirectory(workdir)
            proc.readyReadStandardOutput.connect(self._drain)
            if os.name == "nt":
                shell = os.environ.get("COMSPEC", "cmd.exe")
                args = ["/Q", "/K", "prompt $P$G"]
            else:
                shell = os.environ.get("SHELL", "/bin/sh")
                args = ["-i"]
            try:
                proc.start(shell, args)
                self._process = proc
            except Exception:
                self._process = None

        def showEvent(self, event):
            super().showEvent(event)
            self.start()
            self._input.setFocus()

        def _decode(self, raw):
            for encoding in ("utf-8", "mbcs"):
                try:
                    return raw.decode(encoding)
                except Exception:
                    continue
            return raw.decode("utf-8", "replace")

        def _drain(self):
            if self._process is None:
                return
            text = self._decode(bytes(self._process.readAllStandardOutput()))
            cursor = self._view.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            cursor.insertText(text)
            self._view.setTextCursor(cursor)
            self._view.ensureCursorVisible()
            document = self._view.document()
            extra = document.blockCount() - 4000
            if extra > 0:
                trim = QtGui.QTextCursor(document)
                trim.movePosition(QtGui.QTextCursor.MoveOperation.Start)
                trim.movePosition(QtGui.QTextCursor.MoveOperation.NextBlock, QtGui.QTextCursor.MoveMode.KeepAnchor, extra)
                trim.removeSelectedText()

        def _send(self):
            if self._process is None:
                self.start()
            command = self._input.text()
            self._input.clear()
            if self._process is not None:
                try:
                    ending = "\r\n" if os.name == "nt" else "\n"
                    self._process.write((command + ending).encode("utf-8"))
                except Exception:
                    pass

        def open_external(self, workdir=None):
            folder = workdir if workdir and os.path.isdir(workdir) else os.path.expanduser("~")
            try:
                if os.name == "nt":
                    subprocess_module = __import__("subprocess")
                    subprocess_module.Popen('start cmd /K "cd /d {}"'.format(folder), shell=True)
                else:
                    subprocess_module = __import__("subprocess")
                    subprocess_module.Popen(["x-terminal-emulator"], cwd=folder)
            except Exception:
                pass

        def shutdown(self):
            if self._process is not None:
                try:
                    self._process.kill()
                except Exception:
                    pass
                self._process = None

    class Panels:
        __slots__ = ("FilesPanel", "SpyPanel", "WindowSpyPanel", "TerminalPanel", "ReferencePanel", "ConsolePanel")

        def __init__(self):
            self.FilesPanel = FilesPanel
            self.SpyPanel = SpyPanel
            self.WindowSpyPanel = WindowSpyPanel
            self.TerminalPanel = TerminalPanel
            self.ReferencePanel = ReferencePanel
            self.ConsolePanel = ConsolePanel

    return Panels()
