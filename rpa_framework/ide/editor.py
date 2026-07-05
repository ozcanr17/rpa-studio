import keyword
import os
import re

from .directives import image_target, strip_directives
from .highlighter import build_highlighter_class
from .qt_shim import cached_builder
from .theme import MONOKAI

_MAX_WIDTH = 360
_PAD = 6
_INDENT = 24
_GUTTER_PAD = 18
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
_CLOSERS = (")", "]", "}")
_DEDENT_WORDS = ("return", "pass", "break", "continue", "raise")
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp")
_IMAGE_SEPARATORS = '"' + "'()=,:"
_BUILTIN_WORDS = (
    "print", "len", "range", "str", "int", "float", "list", "dict", "set", "tuple", "open",
    "abs", "min", "max", "sum", "sorted", "enumerate", "zip", "isinstance", "repr", "round",
    "format", "input", "Exception",
)
_HELPER_WORDS = ("emit", "passed", "failed", "wait_if_paused", "checkpoint", "configured_ocr", "main")
_METHOD_WORDS = (
    "similar", "exact", "targetOffset", "getCenter", "getTarget", "getScore", "getFilename",
    "nearby", "above", "below", "left", "right", "union", "intersection", "grow", "offset",
    "text", "highlight", "read_text", "read_boxes", "locate_text", "getX", "getY", "getW", "getH",
    "click", "doubleClick", "rightClick", "hover", "type", "paste", "getText", "getName",
    "getRole", "region", "setROI", "clear", "setText", "write", "isChecked", "isSelected",
    "isEnabled", "toggle", "check", "uncheck", "child", "expand", "collapse", "selectItem", "select",
    "resolve", "autoScroll", "deepest_at", "getClipboard", "setClipboard", "getMouseLocation",
    "getScreenSize", "getOS", "moveTo", "resize", "setBounds", "maximize", "minimize", "restore",
    "focus", "isRunning", "open",
)


def completion_words():
    words = set(keyword.kwlist)
    words.update(_BUILTIN_WORDS)
    words.update(_HELPER_WORDS)
    words.update(_METHOD_WORDS)
    try:
        from ..compat.sikuli import _EXPORTS
        words.update(_EXPORTS)
    except Exception:
        pass
    try:
        from ..core import __all__ as core_names
        words.update(core_names)
    except Exception:
        pass
    return words


@cached_builder
def build_editor_class(qt):
    QtCore, QtGui, QtWidgets, Signal = qt.QtCore, qt.QtGui, qt.QtWidgets, qt.Signal

    class Gutter(QtWidgets.QWidget):
        def __init__(self, editor):
            super().__init__(editor)
            self._editor = editor

        def paintEvent(self, event):
            self._editor.paint_gutter(self, event)

    class ScriptEditor(QtWidgets.QTextEdit):
        lintChanged = Signal(object)
        imageOpenRequested = Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAcceptRichText(False)
            self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
            self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            self.setStyleSheet("QTextEdit {{ background: {}; color: {}; selection-background-color: {}; }}".format(MONOKAI["bg"], MONOKAI["text"], MONOKAI["selection"]))
            font = QtGui.QFont("Cascadia Code")
            if not QtGui.QFontInfo(font).exactMatch():
                font = QtGui.QFont("Consolas")
            font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
            font.setPointSize(11)
            self.setFont(font)
            self.set_point_size(11)
            self._highlighter = build_highlighter_class(qt)(self.document())
            self._images = {}
            self._base_dir = os.getcwd()
            self._updating = False
            self._sync_timer = QtCore.QTimer(self)
            self._sync_timer.setSingleShot(True)
            self._sync_timer.setInterval(150)
            self._sync_timer.timeout.connect(self._sync_images)
            self._gutter = Gutter(self)
            self._static_words = completion_words()
            self._words_stale = True
            self._completer_model = QtCore.QStringListModel(sorted(self._static_words), self)
            self._completer = QtWidgets.QCompleter(self._completer_model, self)
            self._completer.setWidget(self)
            self._completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
            self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            self._completer.activated.connect(self._apply_completion)
            self._error = None
            self._lint_timer = QtCore.QTimer(self)
            self._lint_timer.setSingleShot(True)
            self._lint_timer.setInterval(500)
            self._lint_timer.timeout.connect(self._lint)
            self.textChanged.connect(self._lint_timer.start)
            self.textChanged.connect(self._mark_words_stale)
            self.textChanged.connect(self._schedule_sync)
            self.textChanged.connect(self._update_gutter)
            self.document().blockCountChanged.connect(self._update_gutter)
            self.verticalScrollBar().valueChanged.connect(self._repaint_gutter)
            self.cursorPositionChanged.connect(self._cursor_moved)
            self._update_gutter()
            self._cursor_moved()
            self.document().setModified(False)

        def _apply_tab_stop(self):
            self.setTabStopDistance(4.0 * self.fontMetrics().horizontalAdvance(" "))

        def set_point_size(self, size):
            self._point_size = int(size)
            font = self.font()
            font.setPointSize(self._point_size)
            self.setFont(font)
            self.setStyleSheet("QTextEdit {{ background: {}; color: {}; selection-background-color: {}; font-size: {}pt; }}".format(MONOKAI["bg"], MONOKAI["text"], MONOKAI["selection"], self._point_size))
            self._apply_tab_stop()
            if getattr(self, "_gutter", None) is not None:
                self._update_gutter()

        def _gutter_width(self):
            digits = max(3, len(str(max(1, self.document().blockCount()))))
            return _GUTTER_PAD + digits * self.fontMetrics().horizontalAdvance("9")

        def _update_gutter(self):
            width = self._gutter_width()
            self.setViewportMargins(width, 0, 0, 0)
            rect = self.contentsRect()
            self._gutter.setGeometry(rect.left(), rect.top(), width, rect.height())
            self._gutter.update()

        def _repaint_gutter(self):
            self._gutter.update()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._update_gutter()

        def paint_gutter(self, widget, event):
            painter = QtGui.QPainter(widget)
            painter.fillRect(event.rect(), QtGui.QColor(MONOKAI["bg"]))
            painter.setFont(self.font())
            layout = self.document().documentLayout()
            dy = float(self.verticalScrollBar().value())
            height = widget.height()
            width = widget.width()
            current = self.textCursor().blockNumber()
            error_line = self._error[0] - 1 if self._error else -1
            block = self.document().firstBlock()
            number = 0
            metrics = self.fontMetrics()
            while block.isValid():
                rect = layout.blockBoundingRect(block)
                top = rect.top() - dy
                if top > height:
                    break
                if top + rect.height() >= 0:
                    if number == error_line:
                        color = MONOKAI["error"]
                    elif number == current:
                        color = MONOKAI["gutterhi"]
                    else:
                        color = MONOKAI["gutter"]
                    painter.setPen(QtGui.QColor(color))
                    painter.drawText(QtCore.QRectF(0, top + 2, width - 10, metrics.height()), QtCore.Qt.AlignmentFlag.AlignRight, str(number + 1))
                block = block.next()
                number += 1
            painter.end()

        def _lint(self):
            source = strip_directives(self.toPlainText())
            error = None
            try:
                compile(source, "<script>", "exec")
            except SyntaxError as exc:
                error = (exc.lineno or 1, exc.msg or "syntax error")
            except Exception:
                error = None
            if error != self._error:
                self._error = error
                self.lintChanged.emit(error)
                self._gutter.update()

        def syntax_error(self):
            return self._error

        def _cursor_moved(self):
            selection = QtWidgets.QTextEdit.ExtraSelection()
            selection.format.setBackground(QtGui.QColor(MONOKAI["line"]))
            selection.format.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            self.setExtraSelections([selection])
            self._gutter.update()

        def _mark_words_stale(self):
            self._words_stale = True

        def _refresh_words(self):
            if not self._words_stale:
                return
            self._words_stale = False
            words = set(self._static_words)
            words.update(_WORD_RE.findall(self.toPlainText()))
            self._completer_model.setStringList(sorted(words))

        def _current_prefix(self):
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
            return cursor.selectedText()

        def _apply_completion(self, text):
            cursor = self.textCursor()
            cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
            cursor.insertText(text)
            self.setTextCursor(cursor)

        def _maybe_complete(self, event):
            typed = event.text()
            if not typed or not (typed.isalnum() or typed == "_"):
                self._completer.popup().hide()
                return
            prefix = self._current_prefix()
            if len(prefix) < 2:
                self._completer.popup().hide()
                return
            self._refresh_words()
            self._completer.setCompletionPrefix(prefix)
            count = self._completer.completionCount()
            if count == 0 or (count == 1 and self._completer.currentCompletion() == prefix):
                self._completer.popup().hide()
                return
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
            rect = self.cursorRect()
            rect.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width())
            self._completer.complete(rect)

        def _auto_indent(self):
            cursor = self.textCursor()
            line = cursor.block().text()[:cursor.positionInBlock()]
            stripped = line.strip()
            indent = line[:len(line) - len(line.lstrip())]
            after = self._char_after(cursor)
            if line.rstrip().endswith(":"):
                indent += "    "
            elif stripped.split(" ")[0] in _DEDENT_WORDS and len(indent) >= 4:
                indent = indent[:-4]
            cursor.beginEditBlock()
            cursor.insertText("\n" + indent)
            if after in (")", "]", "}") and line.rstrip().endswith(("(", "[", "{")):
                cursor.insertText("\n" + indent[:-4] if len(indent) >= 4 else "\n")
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Up)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
            cursor.endEditBlock()
            self.setTextCursor(cursor)

        def _char_after(self, cursor):
            text = cursor.block().text()
            idx = cursor.positionInBlock()
            return text[idx] if idx < len(text) else ""

        def _char_before(self, cursor):
            idx = cursor.positionInBlock()
            text = cursor.block().text()
            return text[idx - 1] if idx > 0 else ""

        def _handle_pairs(self, event):
            typed = event.text()
            if not typed or typed not in _PAIRS and typed not in _CLOSERS:
                return False
            cursor = self.textCursor()
            if cursor.hasSelection() and typed in _PAIRS:
                start = cursor.selectionStart()
                selected = cursor.selectedText().replace(chr(0x2029), "\n")
                cursor.insertText(typed + selected + _PAIRS[typed])
                nc = self.textCursor()
                nc.setPosition(start + 1)
                nc.setPosition(start + 1 + len(selected), QtGui.QTextCursor.MoveMode.KeepAnchor)
                self.setTextCursor(nc)
                return True
            if typed in _CLOSERS and self._char_after(cursor) == typed:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return True
            if typed in _PAIRS:
                after = self._char_after(cursor)
                before = self._char_before(cursor)
                if typed in ('"', "'"):
                    if after == typed:
                        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right)
                        self.setTextCursor(cursor)
                        return True
                    if before.isalnum() or before == typed or after.isalnum():
                        return False
                cursor.insertText(typed + _PAIRS[typed])
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left)
                self.setTextCursor(cursor)
                return True
            return False

        def _delete_pair(self):
            cursor = self.textCursor()
            if cursor.hasSelection():
                return False
            before = self._char_before(cursor)
            if before in _PAIRS and self._char_after(cursor) == _PAIRS[before]:
                cursor.beginEditBlock()
                cursor.deleteChar()
                cursor.deletePreviousChar()
                cursor.endEditBlock()
                return True
            return False

        def _selected_block_range(self):
            cursor = self.textCursor()
            doc = self.document()
            start, end = cursor.selectionStart(), cursor.selectionEnd()
            first = doc.findBlock(start).blockNumber()
            last = doc.findBlock(end).blockNumber()
            if end > start and doc.findBlock(end).position() == end and last > first:
                last -= 1
            return first, last

        def _toggle_comment(self):
            doc = self.document()
            first, last = self._selected_block_range()
            texts = [doc.findBlockByNumber(n).text() for n in range(first, last + 1)]
            body = [t for t in texts if t.strip()]
            commented = bool(body) and all(t.lstrip().startswith("#") for t in body)
            cursor = self.textCursor()
            cursor.beginEditBlock()
            for n in range(first, last + 1):
                block = doc.findBlockByNumber(n)
                text = block.text()
                if not text.strip():
                    continue
                edit = QtGui.QTextCursor(block)
                if commented:
                    idx = text.find("#")
                    remove = 2 if text[idx:idx + 2] == "# " else 1
                    edit.setPosition(block.position() + idx)
                    edit.setPosition(block.position() + idx + remove, QtGui.QTextCursor.MoveMode.KeepAnchor)
                    edit.removeSelectedText()
                else:
                    indent = len(text) - len(text.lstrip())
                    edit.setPosition(block.position() + indent)
                    edit.insertText("# ")
            cursor.endEditBlock()

        def _indent_selection(self, direction):
            cursor = self.textCursor()
            doc = self.document()
            has_selection = cursor.hasSelection()
            first, last = self._selected_block_range()
            cursor.beginEditBlock()
            for n in range(first, last + 1):
                block = doc.findBlockByNumber(n)
                edit = QtGui.QTextCursor(block)
                edit.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                if direction > 0:
                    edit.insertText("    ")
                else:
                    text = block.text()
                    remove = 0
                    while remove < 4 and remove < len(text) and text[remove] == " ":
                        remove += 1
                    if remove:
                        edit.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.KeepAnchor, remove)
                        edit.removeSelectedText()
            cursor.endEditBlock()
            if has_selection:
                nc = self.textCursor()
                nc.setPosition(doc.findBlockByNumber(first).position())
                tail = doc.findBlockByNumber(last)
                nc.setPosition(tail.position() + len(tail.text()), QtGui.QTextCursor.MoveMode.KeepAnchor)
                self.setTextCursor(nc)

        def _duplicate(self):
            cursor = self.textCursor()
            cursor.beginEditBlock()
            if cursor.hasSelection():
                text = cursor.selectedText().replace(chr(0x2029), "\n")
                end = cursor.selectionEnd()
                cursor.setPosition(end)
                cursor.insertText(text)
            else:
                col = cursor.positionInBlock()
                line = cursor.block().text()
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
                cursor.insertText("\n" + line)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right, QtGui.QTextCursor.MoveMode.MoveAnchor, min(col, len(line)))
            cursor.endEditBlock()
            self.setTextCursor(cursor)

        def _delete_line(self):
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            if cursor.atEnd():
                cursor.deletePreviousChar()
            else:
                cursor.deleteChar()
            cursor.endEditBlock()
            self.setTextCursor(cursor)

        def _set_block_text(self, edit, block, text):
            edit.setPosition(block.position())
            edit.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
            edit.insertText(text)

        def _move_line(self, direction):
            cursor = self.textCursor()
            doc = self.document()
            num = cursor.block().blockNumber()
            target = num + direction
            if target < 0 or target >= doc.blockCount():
                return
            col = cursor.positionInBlock()
            cur_text = doc.findBlockByNumber(num).text()
            tgt_text = doc.findBlockByNumber(target).text()
            edit = QtGui.QTextCursor(self.document())
            edit.beginEditBlock()
            self._set_block_text(edit, doc.findBlockByNumber(target), cur_text)
            self._set_block_text(edit, doc.findBlockByNumber(num), tgt_text)
            edit.endEditBlock()
            moved = doc.findBlockByNumber(target)
            nc = self.textCursor()
            nc.setPosition(moved.position() + min(col, len(cur_text)))
            self.setTextCursor(nc)

        def _smart_home(self, extend):
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            indent = len(text) - len(text.lstrip())
            col = cursor.positionInBlock()
            target = block.position() + (0 if col == indent else indent)
            mode = QtGui.QTextCursor.MoveMode.KeepAnchor if extend else QtGui.QTextCursor.MoveMode.MoveAnchor
            cursor.setPosition(target, mode)
            self.setTextCursor(cursor)

        def _image_on_line(self, text):
            cleaned = text
            for ch in _IMAGE_SEPARATORS:
                cleaned = cleaned.replace(ch, " ")
            for token in cleaned.split():
                if token.lower().endswith(_IMAGE_SUFFIXES):
                    return token
            return None

        def _image_path(self, name):
            path = name if os.path.isabs(name) else os.path.join(self._base_dir, name)
            return os.path.normpath(path)

        def _remove_block(self, number):
            block = self.document().findBlockByNumber(number)
            if not block.isValid():
                return
            cursor = QtGui.QTextCursor(block)
            cursor.beginEditBlock()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock, QtGui.QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            if cursor.atEnd():
                cursor.deletePreviousChar()
            else:
                cursor.deleteChar()
            cursor.endEditBlock()

        def _delete_image(self, path, number):
            buttons = QtWidgets.QMessageBox.StandardButton
            question = "Delete the file {} and remove this line?".format(os.path.basename(path))
            if QtWidgets.QMessageBox.question(self, "Delete image", question, buttons.Yes | buttons.No) != buttons.Yes:
                return
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Delete failed", str(exc))
                return
            self._remove_block(number)

        def _rename_image(self, path, number):
            old = os.path.basename(path)
            new, ok = QtWidgets.QInputDialog.getText(self, "Rename image", "New file name:", text=old)
            if not ok or not new.strip():
                return
            new = new.strip()
            if not new.lower().endswith(_IMAGE_SUFFIXES):
                new += os.path.splitext(old)[1] or ".png"
            target = os.path.join(os.path.dirname(path), new)
            try:
                if os.path.isfile(path):
                    os.rename(path, target)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Rename failed", str(exc))
                return
            old_stem = os.path.splitext(old)[0]
            new_stem = os.path.splitext(new)[0]
            source = self.toPlainText()
            updated = re.sub(r"\b" + re.escape(old_stem) + r"\b", new_stem, source)
            if updated == source:
                return
            cursor = QtGui.QTextCursor(self.document())
            cursor.beginEditBlock()
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
            cursor.insertText(updated)
            cursor.endEditBlock()

        def contextMenuEvent(self, event):
            menu = self.createStandardContextMenu(event.pos())
            cursor = self.cursorForPosition(event.pos())
            name = self._image_on_line(cursor.block().text())
            if name:
                number = cursor.blockNumber()
                path = self._image_path(name)
                menu.addSeparator()
                open_action = menu.addAction("Open Image (Asset Tester)")
                open_action.setEnabled(os.path.isfile(path))
                open_action.triggered.connect(lambda checked=False, p=path: self.imageOpenRequested.emit(p))
                rename_action = menu.addAction("Rename Image File...")
                rename_action.triggered.connect(lambda checked=False, p=path, n=number: self._rename_image(p, n))
                delete_action = menu.addAction("Delete Image (file + line)")
                delete_action.triggered.connect(lambda checked=False, p=path, n=number: self._delete_image(p, n))
            menu.exec(event.globalPos())

        def keyPressEvent(self, event):
            keys = QtCore.Qt.Key
            mods = event.modifiers()
            mod = QtCore.Qt.KeyboardModifier
            ctrl = bool(mods & mod.ControlModifier)
            shift = bool(mods & mod.ShiftModifier)
            alt = bool(mods & mod.AltModifier)
            key = event.key()
            if self._completer.popup().isVisible() and key in (keys.Key_Return, keys.Key_Enter, keys.Key_Tab, keys.Key_Backtab, keys.Key_Escape):
                event.ignore()
                return
            if ctrl and not alt:
                if not shift and key == keys.Key_Slash:
                    self._toggle_comment()
                    return
                if not shift and key == keys.Key_D:
                    self._duplicate()
                    return
                if not shift and key == keys.Key_Y:
                    self._delete_line()
                    return
                if shift and key == keys.Key_Z:
                    self.redo()
                    return
            if alt and shift and key in (keys.Key_Up, keys.Key_Down):
                self._move_line(-1 if key == keys.Key_Up else 1)
                return
            if key in (keys.Key_Return, keys.Key_Enter) and not mods:
                self._auto_indent()
                return
            if key == keys.Key_Backtab or (key == keys.Key_Tab and shift):
                self._indent_selection(-1)
                return
            if key == keys.Key_Tab and not ctrl and not alt:
                if self.textCursor().hasSelection():
                    self._indent_selection(1)
                    return
                self.textCursor().insertText("    ")
                return
            if key == keys.Key_Home and not ctrl and not alt:
                self._smart_home(shift)
                return
            if key == keys.Key_Backspace and not mods and self._delete_pair():
                return
            if not mods or mods == mod.ShiftModifier:
                if self._handle_pairs(event):
                    return
            super().keyPressEvent(event)
            self._maybe_complete(event)

        def insert_text(self, text):
            cursor = self.textCursor()
            cursor.insertText(text)
            self.setTextCursor(cursor)
            self.setFocus()

        def wheelEvent(self, event):
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoomIn(1)
                else:
                    self.zoomOut(1)
                self._apply_tab_stop()
                self._update_gutter()
                event.accept()
                return
            super().wheelEvent(event)

        def cursor_place(self):
            cursor = self.textCursor()
            return cursor.blockNumber() + 1, cursor.positionInBlock() + 1

        def go_to_line(self, number):
            block = self.document().findBlockByNumber(max(0, int(number) - 1))
            if block.isValid():
                cursor = self.textCursor()
                cursor.setPosition(block.position())
                self.setTextCursor(cursor)
                self.setFocus()

        def insert_snippet(self, text):
            cursor = self.textCursor()
            cursor.beginEditBlock()
            if cursor.positionInBlock() > 0:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
                cursor.insertText("\n")
            cursor.insertText(text if text.endswith("\n") else text + "\n")
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            self.setFocus()

        def load_file(self, path):
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            self.setPlainText(content)
            self.document().setModified(False)
            self.set_base_dir(os.path.dirname(os.path.abspath(path)))

        def save_file(self, path):
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self.toPlainText())
            self.document().setModified(False)
            self.set_base_dir(os.path.dirname(os.path.abspath(path)))

        def set_base_dir(self, path):
            self._base_dir = path or os.getcwd()
            self._images.clear()
            self._sync_images()

        def base_dir(self):
            return self._base_dir

        def _schedule_sync(self):
            if not self._updating:
                self._sync_timer.start()

        def _resolve_image(self, spec):
            path = spec if os.path.isabs(spec) else os.path.join(self._base_dir, spec)
            path = os.path.normpath(path)
            if path not in self._images:
                image = None
                try:
                    loaded = QtGui.QImage(path)
                    if not loaded.isNull():
                        if loaded.width() > _MAX_WIDTH:
                            loaded = loaded.scaledToWidth(_MAX_WIDTH, QtCore.Qt.TransformationMode.SmoothTransformation)
                        image = loaded
                except Exception:
                    image = None
                self._images[path] = image
            return self._images[path]

        def _block_image(self, block):
            target = image_target(block.text())
            return self._resolve_image(target) if target else None

        def _sync_images(self):
            if self._updating:
                return
            self._updating = True
            try:
                modified = self.document().isModified()
                for path in [key for key, value in self._images.items() if value is None]:
                    del self._images[path]
                cursor = QtGui.QTextCursor(self.document())
                block = self.document().firstBlock()
                while block.isValid():
                    image = self._block_image(block)
                    margin = float(image.height() + 2 * _PAD) if image is not None else 0.0
                    fmt = block.blockFormat()
                    if fmt.bottomMargin() != margin:
                        fmt.setBottomMargin(margin)
                        cursor.setPosition(block.position())
                        cursor.setBlockFormat(fmt)
                    block = block.next()
                self.document().setModified(modified)
            finally:
                self._updating = False
            self.viewport().update()
            self._gutter.update()

        def _draw_guides(self, painter, layout, dx, dy, height):
            space = float(self.fontMetrics().horizontalAdvance(" "))
            if space <= 0:
                return
            painter.setPen(QtGui.QPen(QtGui.QColor(MONOKAI["guide"])))
            carried = 0
            block = self.document().firstBlock()
            while block.isValid():
                text = block.text()
                stripped = text.strip()
                indent = (len(text) - len(text.lstrip(" "))) if stripped else carried
                if stripped:
                    carried = indent
                levels = indent // 4
                if levels:
                    rect = layout.blockBoundingRect(block)
                    top = rect.top() - dy
                    bottom = rect.bottom() - dy
                    if bottom >= 0 and top <= height:
                        for level in range(1, levels + 1):
                            x = rect.left() + space * 4 * level - dx - 1.0
                            painter.drawLine(QtCore.QPointF(x, top), QtCore.QPointF(x, bottom))
                block = block.next()

        def paintEvent(self, event):
            super().paintEvent(event)
            painter = QtGui.QPainter(self.viewport())
            layout = self.document().documentLayout()
            dx = float(self.horizontalScrollBar().value())
            dy = float(self.verticalScrollBar().value())
            height = self.viewport().height()
            try:
                self._draw_guides(painter, layout, dx, dy, height)
            except Exception:
                pass
            block = self.document().firstBlock()
            while block.isValid():
                image = self._block_image(block)
                if image is not None:
                    rect = layout.blockBoundingRect(block)
                    top = rect.bottom() + _PAD - dy
                    if top < height and top + image.height() > 0:
                        painter.drawImage(QtCore.QPointF(rect.left() + _INDENT - dx, top), image)
                block = block.next()
            painter.end()

    return ScriptEditor
