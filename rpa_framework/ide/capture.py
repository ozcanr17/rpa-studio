from .qt_shim import cached_builder
from .theme import COLORS


def screens_union(qt):
    screens = qt.QtGui.QGuiApplication.screens()
    union = screens[0].geometry()
    for screen in screens[1:]:
        union = union.united(screen.geometry())
    return union


def grab_desktop(qt):
    union = screens_union(qt)
    canvas = qt.QtGui.QPixmap(union.size())
    canvas.fill(qt.QtCore.Qt.GlobalColor.black)
    painter = qt.QtGui.QPainter(canvas)
    for screen in qt.QtGui.QGuiApplication.screens():
        try:
            painter.drawPixmap(screen.geometry().topLeft() - union.topLeft(), screen.grabWindow(0))
        except Exception:
            pass
    painter.end()
    return canvas, union


@cached_builder
def build_capture_class(qt):
    QtCore, QtGui, QtWidgets, Signal = qt.QtCore, qt.QtGui, qt.QtWidgets, qt.Signal

    class CaptureOverlay(QtWidgets.QWidget):
        captured = Signal(object, object, object)
        canceled = Signal()

        def __init__(self, pixmap, union, message="Drag to select an area.", mode="box", allow_offset=False):
            super().__init__(None)
            self._pixmap = pixmap
            self._union = union
            self._message = message
            self._mode = mode
            self._allow_offset = allow_offset
            self._origin = None
            self._current = None
            self._offset_point = None
            self._point = None
            self._dragging = False
            self._committed = False
            self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.Tool)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            self.setGeometry(union)

        def showEvent(self, event):
            super().showEvent(event)
            self.activateWindow()
            self.raise_()
            self.setFocus()
            try:
                self.grabKeyboard()
            except Exception:
                pass

        def _dismiss(self):
            try:
                self.releaseKeyboard()
            except Exception:
                pass
            self.close()

        def _selection(self):
            if self._origin is None or self._current is None:
                return None
            return QtCore.QRect(self._origin, self._current).normalized()

        def _has_line(self):
            return self._origin is not None and self._current is not None and (self._current - self._origin).manhattanLength() > 4

        def _has_box(self):
            selection = self._selection()
            return selection is not None and selection.width() > 4 and selection.height() > 4

        def _draw_marker(self, painter, point, color):
            pen = QtGui.QPen(QtGui.QColor(color))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawEllipse(point, 6, 6)
            painter.drawLine(point + QtCore.QPoint(-10, 0), point + QtCore.QPoint(10, 0))
            painter.drawLine(point + QtCore.QPoint(0, -10), point + QtCore.QPoint(0, 10))

        def _ready(self):
            if self._mode == "line":
                return self._has_line()
            if self._mode == "point":
                return self._point is not None
            return self._has_box()

        def _banner(self, painter):
            if self._ready():
                if self._mode == "point":
                    parts = ["Space or Enter = confirm", "click = move point", "Esc = cancel"]
                elif self._mode == "line":
                    parts = ["Space or Enter = confirm", "drag = redraw", "Esc = cancel"]
                else:
                    parts = ["Space or Enter = confirm", "drag = redraw"]
                    if self._allow_offset:
                        parts.append("right-click = click offset")
                    parts.append("Esc = cancel")
                text = "     ".join(parts)
            else:
                text = self._message
            metrics = painter.fontMetrics()
            width = metrics.horizontalAdvance(text) + 28
            box = QtCore.QRect(0, 0, width, 30)
            box.moveCenter(QtCore.QPoint(self.rect().center().x(), 26))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(COLORS["accent"]))
            painter.drawRoundedRect(box, 6, 6)
            painter.setPen(QtGui.QColor(COLORS["bright"]))
            painter.drawText(box, QtCore.Qt.AlignmentFlag.AlignCenter, text)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            painter.drawPixmap(0, 0, self._pixmap)
            painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 110))
            selection = self._selection()
            if self._mode == "point":
                if self._point is not None:
                    self._draw_marker(painter, self._point, COLORS["warn"])
                    gx = self._point.x() + self._union.x()
                    gy = self._point.y() + self._union.y()
                    painter.setPen(QtGui.QColor(COLORS["bright"]))
                    painter.drawText(self._point + QtCore.QPoint(12, -12), "Location({}, {})".format(gx, gy))
            elif self._mode == "line" and self._origin is not None and self._current is not None:
                pen = QtGui.QPen(QtGui.QColor(COLORS["focus"]))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawLine(self._origin, self._current)
                self._draw_marker(painter, self._origin, COLORS["focus"])
                self._draw_marker(painter, self._current, COLORS["warn"])
                dx = self._current.x() - self._origin.x()
                dy = self._current.y() - self._origin.y()
                painter.setPen(QtGui.QColor(COLORS["bright"]))
                painter.drawText(self._current + QtCore.QPoint(12, -12), "targetOffset({}, {})".format(dx, dy))
            elif self._mode != "line" and selection is not None and selection.width() > 0 and selection.height() > 0:
                painter.drawPixmap(selection, self._pixmap, selection)
                pen = QtGui.QPen(QtGui.QColor(COLORS["focus"]))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawRect(selection)
                label = "{} x {}".format(selection.width(), selection.height())
                painter.setPen(QtGui.QColor(COLORS["bright"]))
                painter.drawText(selection.adjusted(0, -24, 0, 0).topLeft() + QtCore.QPoint(2, 16), label)
                if self._offset_point is not None:
                    self._draw_marker(painter, self._offset_point, COLORS["warn"])
                    painter.setPen(QtGui.QColor(COLORS["warn"]))
                    dx, dy = self._offset_from(selection)
                    painter.drawText(self._offset_point + QtCore.QPoint(12, -12), "offset({}, {})".format(dx, dy))
            self._banner(painter)
            painter.end()

        def mousePressEvent(self, event):
            if self._mode == "point":
                self._point = event.position().toPoint()
                self.update()
                return
            if event.button() == QtCore.Qt.MouseButton.RightButton:
                if self._allow_offset and self._mode != "line" and self._has_box():
                    self._offset_point = event.position().toPoint()
                    self.update()
                return
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
                return
            self._origin = event.position().toPoint()
            self._current = self._origin
            self._offset_point = None
            self._dragging = True
            self.update()

        def mouseMoveEvent(self, event):
            if self._dragging and self._origin is not None:
                self._current = event.position().toPoint()
                self.update()

        def mouseReleaseEvent(self, event):
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
                return
            self._dragging = False
            self.update()

        def keyPressEvent(self, event):
            key = event.key()
            keys = QtCore.Qt.Key
            if key == keys.Key_Escape:
                self._cancel()
            elif key in (keys.Key_Space, keys.Key_Return, keys.Key_Enter):
                self._commit()

        def _offset_from(self, selection):
            if self._offset_point is None:
                return (0, 0)
            center = selection.center()
            return (self._offset_point.x() - center.x(), self._offset_point.y() - center.y())

        def _cancel(self):
            if self._committed:
                return
            self._committed = True
            self._dismiss()
            self.canceled.emit()

        def _commit(self):
            if self._committed:
                return
            if self._mode == "point":
                if self._point is None:
                    return
                self._committed = True
                self._dismiss()
                gx = self._point.x() + self._union.x()
                gy = self._point.y() + self._union.y()
                self.captured.emit(None, QtCore.QRect(gx, gy, 0, 0), None)
                return
            if self._mode == "line":
                if not self._has_line():
                    return
                self._committed = True
                self._dismiss()
                dx = self._current.x() - self._origin.x()
                dy = self._current.y() - self._origin.y()
                box = QtCore.QRect(self._origin, self._current).normalized().translated(self._union.topLeft())
                self.captured.emit(None, box, (dx, dy))
                return
            if not self._has_box():
                return
            selection = self._selection()
            self._committed = True
            self._dismiss()
            crop = self._pixmap.copy(selection).toImage()
            region = selection.translated(self._union.topLeft())
            offset = self._offset_from(selection) if (self._allow_offset and self._offset_point is not None) else None
            self.captured.emit(crop, region, offset)

    class HighlightOverlay(QtWidgets.QWidget):
        def __init__(self, rects, color=None, seconds=1.8):
            super().__init__(None)
            union = screens_union(qt)
            origin = union.topLeft()
            self._rects = [rect.translated(-origin) for rect in rects]
            self._color = color or COLORS["error"]
            self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowTransparentForInput)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            self.setGeometry(union)
            QtCore.QTimer.singleShot(int(seconds * 1000), self.close)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            pen = QtGui.QPen(QtGui.QColor(self._color))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            for rect in self._rects:
                painter.drawRect(rect)
            painter.end()

    class Capture:
        __slots__ = ("Overlay", "Highlight")

        def __init__(self, overlay, highlight):
            self.Overlay = overlay
            self.Highlight = highlight

    return Capture(CaptureOverlay, HighlightOverlay)
