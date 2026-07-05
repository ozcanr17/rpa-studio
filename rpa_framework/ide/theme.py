import os
import tempfile

from .qt_shim import load_qt

COLORS = {
    "bg": "#1e1e1e",
    "panel": "#252526",
    "panel2": "#2d2d30",
    "panel3": "#333333",
    "border": "#3f3f46",
    "accent": "#5b5fe0",
    "accenthi": "#6e72ea",
    "focus": "#8286f0",
    "text": "#d4d4d4",
    "bright": "#ffffff",
    "dim": "#8a8a8a",
    "selection": "#3b3d63",
    "hover": "#2a2d2e",
    "active": "#37373d",
    "error": "#f48771",
    "ok": "#4ec9b0",
    "warn": "#dcdcaa",
    "info": "#569cd6",
    "line": "#232323",
    "gutter": "#6e7681",
    "gutterhi": "#c6c6c6",
}

MONOKAI = {
    "bg": "#272822",
    "text": "#f8f8f2",
    "line": "#3e3d32",
    "gutter": "#90908a",
    "gutterhi": "#f8f8f2",
    "selection": "#49483e",
    "error": "#f92672",
    "guide": "#3c3d35",
}

LOGO_STOPS = ((0.0, "#22d3ee"), (0.5, "#3b82f6"), (1.0, "#8b5cf6"))
_LOGO_HEX = ((16, 3), (27.3, 9.5), (27.3, 22.5), (16, 29), (4.7, 22.5), (4.7, 9.5))
_LOGO_STROKES = (
    ((10, 11), (10, 21.5)),
    ((10, 11), (13.6, 11), (13.6, 14.6), (10, 14.6)),
    ((11.5, 14.6), (14.2, 21.5)),
    ((22, 11), (18, 11), (18, 16.2), (22, 16.2), (22, 21.5), (17.8, 21.5)),
)
_LOGO_DOTS = ((10, 11), (13.6, 11), (13.6, 14.6), (10, 21.5), (14.2, 21.5), (22, 11), (18, 11), (22, 16.2), (17.8, 21.5))

_QSS = """
QMainWindow, QDialog { background: $bg; }
QWidget { color: $text; font-size: 13px; }
QMenuBar { background: $panel2; border-bottom: 1px solid $border; padding: 2px; }
QMenuBar::item { padding: 5px 10px; background: transparent; border-radius: 4px; }
QMenuBar::item:selected { background: $active; }
QMenu { background: $panel2; border: 1px solid $border; padding: 4px; }
QMenu::item { padding: 5px 28px 5px 20px; border-radius: 4px; }
QMenu::item:selected { background: $accent; color: $bright; }
QMenu::item:disabled { color: $dim; }
QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }
QToolBar { background: $panel2; border: none; border-bottom: 1px solid $border; padding: 3px 6px; spacing: 2px; }
QToolBar::separator { width: 1px; background: $border; margin: 4px 6px; }
QToolButton { background: transparent; border: none; border-radius: 6px; padding: 5px; }
QToolButton:hover { background: $active; }
QToolButton:pressed { background: $accent; }
QToolButton:disabled { background: transparent; }
QTabWidget::pane { border: none; background: $bg; }
QTabBar { background: $panel; }
QTabBar::tab { background: $panel; color: $dim; padding: 7px 14px; border: none; border-right: 1px solid $bg; min-width: 90px; }
QTabBar::tab:selected { background: $bg; color: $bright; border-top: 1px solid $focus; }
QTabBar::tab:hover:!selected { background: $hover; }
QDockWidget { color: $text; titlebar-close-icon: none; titlebar-normal-icon: none; }
QDockWidget::title { background: $panel; padding: 6px 10px; border-bottom: 1px solid $border; text-transform: uppercase; }
QTreeView, QTreeWidget, QListWidget { background: $panel; border: none; outline: none; }
QTreeView::item, QTreeWidget::item, QListWidget::item { padding: 3px 4px; border-radius: 3px; }
QTreeView::item:hover, QTreeWidget::item:hover, QListWidget::item:hover { background: $hover; }
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { background: $selection; color: $bright; }
QHeaderView::section { background: $panel2; border: none; padding: 4px; }
QLineEdit { background: $panel3; border: 1px solid $border; border-radius: 6px; padding: 5px 8px; selection-background-color: $selection; }
QLineEdit:focus { border-color: $focus; }
QPushButton { background: $accent; color: $bright; border: none; border-radius: 6px; padding: 6px 16px; }
QPushButton:hover { background: $accenthi; }
QPushButton:pressed { background: $focus; }
QPushButton:disabled { background: $panel3; color: $dim; }
QPushButton:checked { background: $focus; }
QPlainTextEdit, QTextEdit, QTextBrowser { background: $bg; border: none; selection-background-color: $selection; }
QStatusBar { background: $accent; color: $bright; }
QStatusBar QLabel { color: $bright; padding: 2px 8px; }
QStatusBar::item { border: none; }
QSplitter::handle { background: $border; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #424242; border-radius: 5px; min-height: 24px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #4f4f4f; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #424242; border-radius: 5px; min-width: 24px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #4f4f4f; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { background: $panel2; color: $text; border: 1px solid $border; padding: 4px 6px; }
QFormLayout QLabel { padding: 1px; }
QMessageBox, QInputDialog { background: $panel2; }
QSpinBox, QDoubleSpinBox { background: $panel3; border: 1px solid $border; border-radius: 6px; padding: 3px 6px; }
QSpinBox:focus, QDoubleSpinBox:focus { border-color: $focus; }
QSlider::groove:horizontal { height: 4px; background: $panel3; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; background: $focus; margin: -6px 0; border-radius: 7px; }
"""


def _draw_close(qt, p, c):
    p.setPen(_pen(qt, c, 1.9))
    p.drawLine(qt.QtCore.QPointF(5, 5), qt.QtCore.QPointF(11, 11))
    p.drawLine(qt.QtCore.QPointF(11, 5), qt.QtCore.QPointF(5, 11))


def _draw_arrow_up(qt, p, c):
    path = qt.QtGui.QPainterPath()
    path.moveTo(8, 4.5)
    path.lineTo(12.5, 11)
    path.lineTo(3.5, 11)
    path.closeSubpath()
    p.fillPath(path, qt.QtGui.QColor(c))


def _draw_arrow_down(qt, p, c):
    path = qt.QtGui.QPainterPath()
    path.moveTo(8, 11.5)
    path.lineTo(12.5, 5)
    path.lineTo(3.5, 5)
    path.closeSubpath()
    p.fillPath(path, qt.QtGui.QColor(c))


def _png_icon(qt, draw, color, key, size=16):
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    pm = qt.QtGui.QPixmap(size, size)
    pm.fill(qt.QtCore.Qt.GlobalColor.transparent)
    painter = qt.QtGui.QPainter(pm)
    painter.setRenderHint(qt.QtGui.QPainter.RenderHint.Antialiasing)
    draw(qt, painter, color)
    painter.end()
    path = os.path.join(tempfile.gettempdir(), "rpastudio_" + key + ".png")
    try:
        pm.save(path, "PNG")
    except Exception:
        pass
    url = path.replace("\\", "/")
    _CACHE[key] = url
    return url


def _close_button_qss():
    qt = load_qt()
    normal = _png_icon(qt, _draw_close, COLORS["dim"], "close_dim")
    hover = _png_icon(qt, _draw_close, COLORS["bright"], "close_hi")
    up = _png_icon(qt, _draw_arrow_up, COLORS["text"], "spin_up")
    down = _png_icon(qt, _draw_arrow_down, COLORS["text"], "spin_down")
    rules = (
        "QTabBar::close-button { image: url('%s'); subcontrol-position: right; margin: 3px; padding: 1px; border-radius: 3px; }"
        "QTabBar::close-button:hover { image: url('%s'); background: %s; }"
        "QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; border: none; background: transparent; }"
        "QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; border: none; background: transparent; }"
        "QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: %s; }"
        "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url('%s'); width: 9px; height: 9px; }"
        "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url('%s'); width: 9px; height: 9px; }"
    )
    return rules % (normal, hover, COLORS["active"], COLORS["active"], up, down)


def stylesheet():
    qss = _QSS
    for key in sorted(COLORS, key=len, reverse=True):
        qss = qss.replace("$" + key, COLORS[key])
    try:
        qss += _close_button_qss()
    except Exception:
        pass
    return qss


def _pen(qt, color, width=2.4):
    pen = qt.QtGui.QPen(qt.QtGui.QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(qt.QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(qt.QtCore.Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_run(qt, p, c):
    path = qt.QtGui.QPainterPath()
    path.moveTo(11, 8)
    path.lineTo(24, 16)
    path.lineTo(11, 24)
    path.closeSubpath()
    p.fillPath(path, qt.QtGui.QColor(c))


def _draw_pause(qt, p, c):
    p.fillRect(qt.QtCore.QRectF(10, 8, 4.5, 16), qt.QtGui.QColor(c))
    p.fillRect(qt.QtCore.QRectF(18, 8, 4.5, 16), qt.QtGui.QColor(c))


def _draw_stop(qt, p, c):
    p.fillRect(qt.QtCore.QRectF(10, 10, 12, 12), qt.QtGui.QColor(c))


def _draw_new(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawRoundedRect(qt.QtCore.QRectF(10, 7, 12, 18), 2, 2)
    p.drawLine(qt.QtCore.QPointF(13, 16), qt.QtCore.QPointF(19, 16))
    p.drawLine(qt.QtCore.QPointF(16, 13), qt.QtCore.QPointF(16, 19))


def _draw_open(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(7, 24), qt.QtCore.QPointF(7, 10), qt.QtCore.QPointF(13, 10), qt.QtCore.QPointF(15, 12), qt.QtCore.QPointF(23, 12), qt.QtCore.QPointF(23, 15)])
    p.drawPolygon([qt.QtCore.QPointF(7, 24), qt.QtCore.QPointF(11, 15), qt.QtCore.QPointF(26, 15), qt.QtCore.QPointF(22, 24)])


def _draw_save(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawRoundedRect(qt.QtCore.QRectF(8, 8, 16, 16), 2, 2)
    p.drawRect(qt.QtCore.QRectF(12, 8, 8, 5))
    p.drawRect(qt.QtCore.QRectF(12, 17, 8, 7))


def _draw_camera(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawRoundedRect(qt.QtCore.QRectF(7, 11, 18, 13), 2, 2)
    p.drawEllipse(qt.QtCore.QRectF(13, 14, 6, 6))
    p.drawLine(qt.QtCore.QPointF(12, 11), qt.QtCore.QPointF(14, 8))
    p.drawLine(qt.QtCore.QPointF(14, 8), qt.QtCore.QPointF(18, 8))
    p.drawLine(qt.QtCore.QPointF(18, 8), qt.QtCore.QPointF(20, 11))


def _draw_spy(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawEllipse(qt.QtCore.QRectF(10, 10, 12, 12))
    p.drawLine(qt.QtCore.QPointF(16, 5), qt.QtCore.QPointF(16, 10))
    p.drawLine(qt.QtCore.QPointF(16, 22), qt.QtCore.QPointF(16, 27))
    p.drawLine(qt.QtCore.QPointF(5, 16), qt.QtCore.QPointF(10, 16))
    p.drawLine(qt.QtCore.QPointF(22, 16), qt.QtCore.QPointF(27, 16))


def _draw_ocr(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(11, 6), qt.QtCore.QPointF(6, 6), qt.QtCore.QPointF(6, 11)])
    p.drawPolyline([qt.QtCore.QPointF(21, 6), qt.QtCore.QPointF(26, 6), qt.QtCore.QPointF(26, 11)])
    p.drawPolyline([qt.QtCore.QPointF(11, 26), qt.QtCore.QPointF(6, 26), qt.QtCore.QPointF(6, 21)])
    p.drawPolyline([qt.QtCore.QPointF(21, 26), qt.QtCore.QPointF(26, 26), qt.QtCore.QPointF(26, 21)])
    p.drawLine(qt.QtCore.QPointF(10, 13), qt.QtCore.QPointF(22, 13))
    p.drawLine(qt.QtCore.QPointF(10, 17), qt.QtCore.QPointF(22, 17))
    p.drawLine(qt.QtCore.QPointF(10, 21), qt.QtCore.QPointF(17, 21))


def _draw_build(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolygon([qt.QtCore.QPointF(16, 5), qt.QtCore.QPointF(26, 10), qt.QtCore.QPointF(16, 15), qt.QtCore.QPointF(6, 10)])
    p.drawPolyline([qt.QtCore.QPointF(6, 10), qt.QtCore.QPointF(6, 21), qt.QtCore.QPointF(16, 26), qt.QtCore.QPointF(26, 21), qt.QtCore.QPointF(26, 10)])
    p.drawLine(qt.QtCore.QPointF(16, 15), qt.QtCore.QPointF(16, 26))


def _draw_region(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(11, 6), qt.QtCore.QPointF(6, 6), qt.QtCore.QPointF(6, 11)])
    p.drawPolyline([qt.QtCore.QPointF(21, 6), qt.QtCore.QPointF(26, 6), qt.QtCore.QPointF(26, 11)])
    p.drawPolyline([qt.QtCore.QPointF(11, 26), qt.QtCore.QPointF(6, 26), qt.QtCore.QPointF(6, 21)])
    p.drawPolyline([qt.QtCore.QPointF(21, 26), qt.QtCore.QPointF(26, 26), qt.QtCore.QPointF(26, 21)])
    p.drawRect(qt.QtCore.QRectF(11, 11, 10, 10))


def _draw_offset(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawEllipse(qt.QtCore.QRectF(6, 19, 6, 6))
    p.drawEllipse(qt.QtCore.QRectF(21, 7, 5, 5))
    p.drawLine(qt.QtCore.QPointF(11.5, 19.5), qt.QtCore.QPointF(20.5, 11.5))
    p.drawLine(qt.QtCore.QPointF(20.5, 11.5), qt.QtCore.QPointF(15.5, 12.5))
    p.drawLine(qt.QtCore.QPointF(20.5, 11.5), qt.QtCore.QPointF(19.5, 16.5))


def _draw_folder(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(6, 24), qt.QtCore.QPointF(6, 9), qt.QtCore.QPointF(13, 9), qt.QtCore.QPointF(15, 12), qt.QtCore.QPointF(26, 12), qt.QtCore.QPointF(26, 24), qt.QtCore.QPointF(6, 24)])
    p.drawLine(qt.QtCore.QPointF(16, 15), qt.QtCore.QPointF(16, 21))
    p.drawLine(qt.QtCore.QPointF(13, 18), qt.QtCore.QPointF(19, 18))


def _draw_refresh(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawArc(qt.QtCore.QRectF(8, 8, 16, 16), 40 * 16, 280 * 16)
    p.drawLine(qt.QtCore.QPointF(21, 5), qt.QtCore.QPointF(21.5, 10.5))
    p.drawLine(qt.QtCore.QPointF(26.5, 9), qt.QtCore.QPointF(21.5, 10.5))


def _draw_collapse(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(10, 15), qt.QtCore.QPointF(16, 9), qt.QtCore.QPointF(22, 15)])
    p.drawPolyline([qt.QtCore.QPointF(10, 23), qt.QtCore.QPointF(16, 17), qt.QtCore.QPointF(22, 23)])


def _draw_expand(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(10, 9), qt.QtCore.QPointF(16, 15), qt.QtCore.QPointF(22, 9)])
    p.drawPolyline([qt.QtCore.QPointF(10, 17), qt.QtCore.QPointF(16, 23), qt.QtCore.QPointF(22, 17)])


def _draw_window(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawRoundedRect(qt.QtCore.QRectF(6, 7, 20, 18), 2, 2)
    p.drawLine(qt.QtCore.QPointF(6, 12), qt.QtCore.QPointF(26, 12))
    p.drawEllipse(qt.QtCore.QRectF(8.4, 8.6, 2.2, 2.2))


def _draw_terminal(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawRoundedRect(qt.QtCore.QRectF(5, 7, 22, 18), 2, 2)
    p.drawPolyline([qt.QtCore.QPointF(9, 12), qt.QtCore.QPointF(13, 16), qt.QtCore.QPointF(9, 20)])
    p.drawLine(qt.QtCore.QPointF(15, 20), qt.QtCore.QPointF(22, 20))


def _draw_search(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawEllipse(qt.QtCore.QRectF(7, 7, 13, 13))
    p.drawLine(qt.QtCore.QPointF(18.5, 18.5), qt.QtCore.QPointF(25, 25))


def _draw_image(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawRoundedRect(qt.QtCore.QRectF(6, 8, 20, 16), 2, 2)
    p.drawEllipse(qt.QtCore.QRectF(10, 11, 4, 4))
    p.drawPolyline([qt.QtCore.QPointF(8, 21), qt.QtCore.QPointF(14, 15), qt.QtCore.QPointF(18, 19), qt.QtCore.QPointF(22, 14), qt.QtCore.QPointF(25, 17)])


def _panel_shape(qt, p, c, side):
    p.setPen(_pen(qt, c, 1.8))
    p.setBrush(qt.QtCore.Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(qt.QtCore.QRectF(6, 8, 20, 16), 2, 2)
    p.setPen(qt.QtCore.Qt.PenStyle.NoPen)
    p.setBrush(qt.QtGui.QColor(c))
    if side == "left":
        p.drawRect(qt.QtCore.QRectF(7.5, 9.5, 5.5, 13))
    elif side == "right":
        p.drawRect(qt.QtCore.QRectF(19, 9.5, 5.5, 13))
    else:
        p.drawRect(qt.QtCore.QRectF(7.5, 17, 17, 5.5))


def _draw_panel_left(qt, p, c):
    _panel_shape(qt, p, c, "left")


def _draw_panel_bottom(qt, p, c):
    _panel_shape(qt, p, c, "bottom")


def _draw_panel_right(qt, p, c):
    _panel_shape(qt, p, c, "right")


def _draw_location(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawEllipse(qt.QtCore.QRectF(10, 6, 12, 12))
    p.drawLine(qt.QtCore.QPointF(11.5, 15.5), qt.QtCore.QPointF(16, 26))
    p.drawLine(qt.QtCore.QPointF(20.5, 15.5), qt.QtCore.QPointF(16, 26))
    p.setPen(qt.QtCore.Qt.PenStyle.NoPen)
    p.setBrush(qt.QtGui.QColor(c))
    p.drawEllipse(qt.QtCore.QRectF(14, 10, 4, 4))


def _draw_timer(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawEllipse(qt.QtCore.QRectF(8, 10, 16, 16))
    p.drawLine(qt.QtCore.QPointF(13, 6), qt.QtCore.QPointF(19, 6))
    p.drawLine(qt.QtCore.QPointF(16, 6), qt.QtCore.QPointF(16, 10))
    p.drawLine(qt.QtCore.QPointF(16, 18), qt.QtCore.QPointF(16, 13))
    p.drawLine(qt.QtCore.QPointF(16, 18), qt.QtCore.QPointF(20, 18))


def _draw_clear(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawEllipse(qt.QtCore.QRectF(8, 8, 16, 16))
    p.drawLine(qt.QtCore.QPointF(11, 21), qt.QtCore.QPointF(21, 11))


def _draw_book(qt, p, c):
    p.setPen(_pen(qt, c))
    p.drawPolyline([qt.QtCore.QPointF(16, 9), qt.QtCore.QPointF(13, 7), qt.QtCore.QPointF(7, 7), qt.QtCore.QPointF(7, 23), qt.QtCore.QPointF(13, 23), qt.QtCore.QPointF(16, 25)])
    p.drawPolyline([qt.QtCore.QPointF(16, 9), qt.QtCore.QPointF(19, 7), qt.QtCore.QPointF(25, 7), qt.QtCore.QPointF(25, 23), qt.QtCore.QPointF(19, 23), qt.QtCore.QPointF(16, 25)])
    p.drawLine(qt.QtCore.QPointF(16, 9), qt.QtCore.QPointF(16, 25))


_ICONS = {
    "run": (_draw_run, "ok"),
    "pause": (_draw_pause, "warn"),
    "stop": (_draw_stop, "error"),
    "new": (_draw_new, "text"),
    "open": (_draw_open, "text"),
    "save": (_draw_save, "text"),
    "camera": (_draw_camera, "info"),
    "spy": (_draw_spy, "info"),
    "ocr": (_draw_ocr, "info"),
    "region": (_draw_region, "info"),
    "offset": (_draw_offset, "warn"),
    "location": (_draw_location, "info"),
    "timer": (_draw_timer, "info"),
    "folder": (_draw_folder, "text"),
    "refresh": (_draw_refresh, "text"),
    "collapse": (_draw_collapse, "text"),
    "expand": (_draw_expand, "text"),
    "window": (_draw_window, "info"),
    "terminal": (_draw_terminal, "text"),
    "search": (_draw_search, "text"),
    "image": (_draw_image, "warn"),
    "panel_left": (_draw_panel_left, "text"),
    "panel_bottom": (_draw_panel_bottom, "text"),
    "panel_right": (_draw_panel_right, "text"),
    "build": (_draw_build, "warn"),
    "clear": (_draw_clear, "text"),
    "book": (_draw_book, "text"),
}

_CACHE = {}


def _logo_gradient(qt):
    gradient = qt.QtGui.QLinearGradient(4, 3, 28, 29)
    for offset, color in LOGO_STOPS:
        gradient.setColorAt(offset, qt.QtGui.QColor(color))
    return gradient


def python_icon(qt):
    if "__python__" in _CACHE:
        return _CACHE["__python__"]
    icon = None
    try:
        from ..packaging.runtime_paths import resource_path
        source = resource_path("icons", "python.svg")
        if os.path.isfile(source):
            with open(source, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            if "fill=" not in text:
                text = text.replace("<path ", '<path fill="#4b8bbe" ', 1)
            target = os.path.join(tempfile.gettempdir(), "rpastudio_python.svg")
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text)
            candidate = qt.QtGui.QIcon(target)
            icon = candidate if not candidate.isNull() else None
    except Exception:
        icon = None
    _CACHE["__python__"] = icon
    return icon


def _logo_file():
    try:
        from ..packaging.runtime_paths import logo_path
        return logo_path()
    except Exception:
        return None


def logo_pixmap(qt, size=256):
    path = _logo_file()
    if path:
        try:
            pm = qt.QtGui.QPixmap(path)
            if not pm.isNull():
                return pm.scaled(size, size, qt.QtCore.Qt.AspectRatioMode.KeepAspectRatio, qt.QtCore.Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
    pm = qt.QtGui.QPixmap(size, size)
    pm.fill(qt.QtCore.Qt.GlobalColor.transparent)
    painter = qt.QtGui.QPainter(pm)
    painter.setRenderHint(qt.QtGui.QPainter.RenderHint.Antialiasing)
    painter.scale(size / 32.0, size / 32.0)
    gradient = _logo_gradient(qt)
    pen = qt.QtGui.QPen(qt.QtGui.QBrush(gradient), 1.8)
    pen.setCapStyle(qt.QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(qt.QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(qt.QtCore.Qt.BrushStyle.NoBrush)
    painter.drawPolygon(qt.QtGui.QPolygonF([qt.QtCore.QPointF(x, y) for x, y in _LOGO_HEX]))
    pen.setWidthF(1.5)
    painter.setPen(pen)
    for stroke in _LOGO_STROKES:
        painter.drawPolyline([qt.QtCore.QPointF(x, y) for x, y in stroke])
    painter.setPen(qt.QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(qt.QtGui.QBrush(gradient))
    for x, y in _LOGO_DOTS:
        painter.drawEllipse(qt.QtCore.QRectF(x - 1.0, y - 1.0, 2.0, 2.0))
    painter.end()
    return pm


def logo_icon(qt):
    cached = _CACHE.get("__logo__")
    if cached is not None:
        return cached
    icon = qt.QtGui.QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(qt, size))
    _CACHE["__logo__"] = icon
    return icon


def make_icon(qt, kind):
    cached = _CACHE.get(kind)
    if cached is not None:
        return cached
    draw, color_key = _ICONS[kind]
    pm = qt.QtGui.QPixmap(32, 32)
    pm.fill(qt.QtCore.Qt.GlobalColor.transparent)
    painter = qt.QtGui.QPainter(pm)
    painter.setRenderHint(qt.QtGui.QPainter.RenderHint.Antialiasing)
    draw(qt, painter, COLORS[color_key])
    painter.end()
    icon = qt.QtGui.QIcon(pm)
    _CACHE[kind] = icon
    return icon


def apply_theme(app):
    qt = load_qt()
    app.setStyle("Fusion")
    palette = qt.QtGui.QPalette()
    roles = qt.QtGui.QPalette.ColorRole
    palette.setColor(roles.Window, qt.QtGui.QColor(COLORS["bg"]))
    palette.setColor(roles.WindowText, qt.QtGui.QColor(COLORS["text"]))
    palette.setColor(roles.Base, qt.QtGui.QColor(COLORS["panel"]))
    palette.setColor(roles.AlternateBase, qt.QtGui.QColor(COLORS["panel2"]))
    palette.setColor(roles.Text, qt.QtGui.QColor(COLORS["text"]))
    palette.setColor(roles.Button, qt.QtGui.QColor(COLORS["panel2"]))
    palette.setColor(roles.ButtonText, qt.QtGui.QColor(COLORS["text"]))
    palette.setColor(roles.Highlight, qt.QtGui.QColor(COLORS["selection"]))
    palette.setColor(roles.HighlightedText, qt.QtGui.QColor(COLORS["bright"]))
    palette.setColor(roles.Link, qt.QtGui.QColor(COLORS["focus"]))
    palette.setColor(roles.ToolTipBase, qt.QtGui.QColor(COLORS["panel2"]))
    palette.setColor(roles.ToolTipText, qt.QtGui.QColor(COLORS["text"]))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet())
    return app
