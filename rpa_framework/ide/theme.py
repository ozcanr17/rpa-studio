import os
import tempfile

from .qt_shim import load_qt

COLORS = {
    "bg": "#15161b",
    "panel": "#191a20",
    "panel2": "#1e1f27",
    "panel3": "#23252e",
    "border": "#2b2d38",
    "divider": "#21232c",
    "accent": "#4f46e5",
    "accenthi": "#5b52ee",
    "focus": "#818cf8",
    "text": "#e5e6ec",
    "bright": "#ffffff",
    "dim": "#9a9db0",
    "faint": "#6a6d80",
    "selection": "#2e2f57",
    "hover": "#20222b",
    "active": "#282a35",
    "error": "#f2777a",
    "ok": "#5ec9a3",
    "warn": "#d9b26a",
    "info": "#7aa2f7",
    "line": "#1b1d24",
    "gutter": "#565a70",
    "gutterhi": "#c7c9d6",
}

MONOKAI = {
    "bg": "#191a20",
    "text": "#e8e9ef",
    "line": "#20222b",
    "gutter": "#565a70",
    "gutterhi": "#c7c9d6",
    "selection": "#2e2f57",
    "error": "#f2777a",
    "guide": "#262833",
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
QWidget { color: $text; font-size: 12px; }
QMenuBar { background: $bg; border-bottom: 1px solid $divider; padding: 2px 4px; }
QMenuBar::item { padding: 5px 10px; background: transparent; border-radius: 6px; color: $dim; }
QMenuBar::item:selected { background: $active; color: $text; }
QMenu { background: $panel2; border: 1px solid $border; border-radius: 8px; padding: 5px; }
QMenu::item { padding: 6px 28px 6px 14px; border-radius: 5px; }
QMenu::item:selected { background: $accent; color: $bright; }
QMenu::item:disabled { color: $faint; }
QMenu::separator { height: 1px; background: $border; margin: 5px 10px; }
QToolBar { background: $bg; border: none; border-bottom: 1px solid $divider; padding: 4px 8px; spacing: 2px; }
QToolBar::separator { width: 1px; background: $border; margin: 5px 6px; }
QToolButton { background: transparent; border: none; border-radius: 6px; padding: 5px; color: $dim; }
QToolButton:hover { background: $active; color: $text; }
QToolButton:pressed { background: $panel3; }
QToolButton:checked { background: $selection; }
QToolButton:disabled { background: transparent; }
QTabWidget::pane { border: none; background: $bg; }
QTabBar { background: $panel; }
QTabBar::tab { background: transparent; color: $dim; padding: 7px 14px; border: none; border-top: 2px solid transparent; min-width: 80px; }
QTabBar::tab:selected { background: $bg; color: $bright; border-top: 2px solid $accent; }
QTabBar::tab:hover:!selected { background: $hover; color: $text; }
QDockWidget { color: $text; titlebar-close-icon: none; titlebar-normal-icon: none; }
QDockWidget::title { background: $panel; padding: 6px 12px; border-bottom: 1px solid $divider; text-transform: uppercase; font-size: 10px; color: $faint; }
QTreeView, QTreeWidget, QListWidget { background: $panel; border: none; outline: none; }
QTreeView::item, QTreeWidget::item, QListWidget::item { padding: 4px 5px; border-radius: 5px; }
QTreeView::item:hover, QTreeWidget::item:hover, QListWidget::item:hover { background: $hover; }
QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected { background: $selection; color: $bright; }
QTableWidget, QTableView { background: $panel; border: none; gridline-color: $divider; selection-background-color: $selection; selection-color: $bright; alternate-background-color: $panel2; }
QHeaderView::section { background: $panel; border: none; border-bottom: 1px solid $border; padding: 6px 8px; color: $faint; font-size: 10px; text-transform: uppercase; }
QLineEdit { background: $panel3; border: 1px solid $border; border-radius: 6px; padding: 6px 9px; selection-background-color: $selection; }
QLineEdit:focus { border-color: $accent; }
QLineEdit:disabled { color: $faint; }
QPushButton { background: $panel3; color: $text; border: 1px solid $border; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: $active; border-color: #3a3d4c; }
QPushButton:pressed { background: $panel2; }
QPushButton:disabled { background: $panel2; color: $faint; border-color: $divider; }
QPushButton:checked { background: $selection; border-color: $accent; }
QPushButton[primary="true"] { background: $accent; color: $bright; border: none; padding: 7px 15px; }
QPushButton[primary="true"]:hover { background: $accenthi; }
QPushButton[primary="true"]:pressed { background: #443dc4; }
QPushButton[primary="true"]:disabled { background: $panel3; color: $faint; }
QDialogButtonBox QPushButton { min-width: 76px; }
QComboBox { background: $panel3; border: 1px solid $border; border-radius: 6px; padding: 5px 9px; }
QComboBox:hover { border-color: #3a3d4c; }
QComboBox:focus { border-color: $accent; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: $panel2; border: 1px solid $border; border-radius: 6px; selection-background-color: $selection; outline: none; }
QPlainTextEdit, QTextEdit, QTextBrowser { background: $bg; border: none; selection-background-color: $selection; }
QStatusBar { background: $accent; color: $bright; font-size: 11px; }
QStatusBar QLabel { color: $bright; padding: 2px 8px; }
QStatusBar::item { border: none; }
QSplitter::handle { background: $divider; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #2f3140; border-radius: 5px; min-height: 24px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #3c3f52; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #2f3140; border-radius: 5px; min-width: 24px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #3c3f52; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { background: $panel2; color: $text; border: 1px solid $border; border-radius: 6px; padding: 5px 8px; }
QFormLayout QLabel { padding: 1px; }
QMessageBox, QInputDialog { background: $panel2; }
QSpinBox, QDoubleSpinBox { background: $panel3; border: 1px solid $border; border-radius: 6px; padding: 4px 6px; }
QSpinBox:focus, QDoubleSpinBox:focus { border-color: $accent; }
QCheckBox { spacing: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid $border; border-radius: 4px; background: $panel3; }
QCheckBox::indicator:hover { border-color: $focus; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; }
QSlider::groove:horizontal { height: 4px; background: $panel3; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; background: $bright; margin: -6px 0; border-radius: 7px; }
"""


def _draw_close(qt, p, c):
    p.setPen(_pen(qt, c, 1.9))
    p.drawLine(qt.QtCore.QPointF(5, 5), qt.QtCore.QPointF(11, 11))
    p.drawLine(qt.QtCore.QPointF(11, 5), qt.QtCore.QPointF(5, 11))


def _draw_check(qt, p, c):
    p.setPen(_pen(qt, c, 2.0))
    p.drawPolyline([qt.QtCore.QPointF(3.5, 8.5), qt.QtCore.QPointF(6.5, 11.5), qt.QtCore.QPointF(12.5, 4.5)])


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
    check = _png_icon(qt, _draw_check, COLORS["bright"], "check_mark")
    rules = (
        "QTabBar::close-button { image: url('%s'); subcontrol-position: right; margin: 3px; padding: 1px; border-radius: 3px; }"
        "QTabBar::close-button:hover { image: url('%s'); background: %s; }"
        "QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 16px; border: none; background: transparent; }"
        "QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; border: none; background: transparent; }"
        "QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: %s; }"
        "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url('%s'); width: 9px; height: 9px; }"
        "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url('%s'); width: 9px; height: 9px; }"
        "QCheckBox::indicator:checked { image: url('%s'); }"
        "QComboBox::down-arrow { image: url('%s'); width: 9px; height: 9px; }"
    )
    return rules % (normal, hover, COLORS["active"], COLORS["active"], up, down, check, down)


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
    "new": (_draw_new, "dim"),
    "open": (_draw_open, "dim"),
    "save": (_draw_save, "dim"),
    "camera": (_draw_camera, "dim"),
    "spy": (_draw_spy, "dim"),
    "ocr": (_draw_ocr, "dim"),
    "region": (_draw_region, "dim"),
    "offset": (_draw_offset, "dim"),
    "location": (_draw_location, "dim"),
    "timer": (_draw_timer, "dim"),
    "folder": (_draw_folder, "dim"),
    "refresh": (_draw_refresh, "dim"),
    "collapse": (_draw_collapse, "dim"),
    "expand": (_draw_expand, "dim"),
    "window": (_draw_window, "dim"),
    "terminal": (_draw_terminal, "dim"),
    "search": (_draw_search, "dim"),
    "image": (_draw_image, "warn"),
    "panel_left": (_draw_panel_left, "dim"),
    "panel_bottom": (_draw_panel_bottom, "dim"),
    "panel_right": (_draw_panel_right, "dim"),
    "build": (_draw_build, "dim"),
    "clear": (_draw_clear, "dim"),
    "book": (_draw_book, "dim"),
}

_CACHE = {}

_LUCIDE = {
    "run": "play",
    "pause": "pause",
    "stop": "square",
    "new": "file-plus",
    "open": "folder-open",
    "save": "save",
    "camera": "camera",
    "timer": "timer",
    "ocr": "scan-text",
    "region": "square-dashed",
    "location": "crosshair",
    "offset": "move",
    "spy": "target",
    "build": "package",
    "clear": "eraser",
    "book": "book-open",
    "folder": "folder",
    "refresh": "refresh-cw",
    "collapse": "chevrons-down-up",
    "expand": "chevrons-up-down",
    "window": "app-window",
    "terminal": "terminal",
    "search": "search",
    "image": "image",
    "panel_left": "panel-left",
    "panel_bottom": "panel-bottom",
    "panel_right": "panel-right",
}


def _lucide_file(name):
    try:
        from ..packaging.runtime_paths import bundle_root, resource_path
        bundled = resource_path("icons", "lucide", name + ".svg")
        if os.path.isfile(bundled):
            return bundled
        vendored = os.path.join(bundle_root(), "vendor", "icons", "lucide", name + ".svg")
        if os.path.isfile(vendored):
            return vendored
    except Exception:
        pass
    return None


def _lucide_icon(qt, kind, color):
    name = _LUCIDE.get(kind)
    if name is None:
        return None
    source = _lucide_file(name)
    if source is None:
        return None
    try:
        with open(source, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        text = text.replace("currentColor", color)
        target = os.path.join(tempfile.gettempdir(), "rpastudio_lc_{}_{}.svg".format(name, color.lstrip("#")))
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
        icon = qt.QtGui.QIcon(target)
        return icon if not icon.isNull() else None
    except Exception:
        return None


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
    icon = _lucide_icon(qt, kind, COLORS[color_key])
    if icon is None:
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
