import os
import platform
import signal
import subprocess
import sys
import time

try:
    import cv2
except ImportError:
    cv2 = None

from ..core.exceptions import ElementNotFoundError, VisionError
from ..core.inspector.base import InspectorFactory
from ..core.os_facade.base import OSFacadeFactory, Rect
from ..core.vision.feature_matcher import FeatureMatcher, MatchResult, load_image

_IS_WINDOWS = platform.system() == "Windows"
_UPSCALE_MIN = 90
_UPSCALE_CAP = 4.0
_SCORE_INLIERS = 10.0
_FIND_ALL_LIMIT = 20
_AUTO_SCROLL_PLAN = ((0, -3), (0, -3), (0, -3), (0, -3), (3, 0), (3, 0))

WHEEL_DOWN = 1
WHEEL_UP = -1

_STATE = {"screen": None, "bundle": None, "paths": [], "last": None, "matcher": None, "inspector": None, "pause": None}


def use_pause_event(event):
    _STATE["pause"] = event


def _pause_gate():
    event = _STATE.get("pause")
    while event is not None and event.is_set():
        time.sleep(0.05)


class FindFailed(ElementNotFoundError):
    pass


class Settings:
    MinSimilarity = 0.7
    AutoWaitTimeout = 3.0
    ObserveScanRate = 3.0
    WaitScanRate = 3.0
    MoveMouseDelay = 0.0
    ClickDelay = 0.0
    TypeDelay = 0.0
    SlowMotionDelay = 2.0
    DelayBeforeMouseDown = 0.15
    DelayBeforeDrag = 0.15
    DelayBeforeDrop = 0.15
    DefaultHighlightTime = 2.0
    DefaultHighlightColor = "red"
    OcrLanguage = "eng"


class Key:
    pass


class KeyModifier:
    SHIFT = 1
    CTRL = 2
    META = 4
    WIN = 4
    CMD = 4
    ALT = 8


class Button:
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"


_KEY_DEFS = (
    ("ENTER", "\n", "ENTER", "Return"),
    ("TAB", "\t", "TAB", "Tab"),
    ("ESC", "\x1b", "ESC", "Escape"),
    ("BACKSPACE", "\b", "BACKSPACE", "BackSpace"),
    ("SPACE", " ", None, None),
    ("DELETE", "\ue001", "DELETE", "Delete"),
    ("INSERT", "\ue002", "INSERT", "Insert"),
    ("HOME", "\ue003", "HOME", "Home"),
    ("END", "\ue004", "END", "End"),
    ("PAGE_UP", "\ue005", "PGUP", "Page_Up"),
    ("PAGE_DOWN", "\ue006", "PGDN", "Page_Down"),
    ("UP", "\ue007", "UP", "Up"),
    ("DOWN", "\ue008", "DOWN", "Down"),
    ("LEFT", "\ue009", "LEFT", "Left"),
    ("RIGHT", "\ue00a", "RIGHT", "Right"),
    ("PRINTSCREEN", "\ue00b", "PRTSC", "Print"),
    ("PAUSE", "\ue00c", "PAUSE", "Pause"),
    ("CAPS_LOCK", "\ue00d", "CAPSLOCK", "Caps_Lock"),
    ("NUM_LOCK", "\ue00e", "NUMLOCK", "Num_Lock"),
    ("SCROLL_LOCK", "\ue00f", "SCROLLLOCK", "Scroll_Lock"),
    ("CTRL", "\ue020", "ctrl", "ctrl"),
    ("ALT", "\ue021", "alt", "alt"),
    ("SHIFT", "\ue022", "shift", "shift"),
    ("WIN", "\ue023", "win", "super"),
    ("META", "\ue023", "win", "super"),
    ("CMD", "\ue023", "win", "super"),
)

_MOD_BITS = ((2, "ctrl", "ctrl"), (8, "alt", "alt"), (1, "shift", "shift"), (4, "win", "super"))


def _fkey_defs():
    return tuple(("F{}".format(n), chr(0xE010 + n), "F{}".format(n), "F{}".format(n)) for n in range(1, 13))


def _build_keys():
    mapping = {}
    for name, char, win_name, linux_name in _KEY_DEFS + _fkey_defs():
        setattr(Key, name, char)
        if win_name is not None and char not in mapping:
            mapping[char] = win_name if _IS_WINDOWS else linux_name
    return mapping


_CHAR_TO_KEY = _build_keys()


def _mod_names(modifiers):
    return [win if _IS_WINDOWS else lin for bit, win, lin in _MOD_BITS if modifiers & bit]


def _key_arg(key):
    return _CHAR_TO_KEY.get(key, key)


class Location:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def offset(self, dx, dy):
        return Location(self.x + dx, self.y + dy)

    def above(self, dy):
        return Location(self.x, self.y - dy)

    def below(self, dy):
        return Location(self.x, self.y + dy)

    def left(self, dx):
        return Location(self.x - dx, self.y)

    def right(self, dx):
        return Location(self.x + dx, self.y)

    def __repr__(self):
        return "Location({}, {})".format(self.x, self.y)


def _offset_pair(dx, dy):
    if dy is None and hasattr(dx, "x") and hasattr(dx, "y"):
        return int(dx.x), int(dx.y)
    return int(dx), 0 if dy is None else int(dy)


class Offset:
    __slots__ = ("x", "y")

    def __init__(self, x, y=0):
        if y == 0 and hasattr(x, "x") and hasattr(x, "y"):
            self.x = int(x.x)
            self.y = int(x.y)
        else:
            self.x = int(x)
            self.y = int(y)

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def __repr__(self):
        return "Offset({}, {})".format(self.x, self.y)


class Pattern:
    __slots__ = ("path", "similarity", "dx", "dy")

    def __init__(self, path, similarity=None, dx=0, dy=0):
        self.path = path
        self.similarity = similarity
        self.dx = int(dx)
        self.dy = int(dy)

    def similar(self, value):
        return Pattern(self.path, float(value), self.dx, self.dy)

    def exact(self):
        return self.similar(0.99)

    def targetOffset(self, dx, dy=None):
        ox, oy = _offset_pair(dx, dy)
        return Pattern(self.path, self.similarity, ox, oy)

    def getFilename(self):
        return self.path

    def __repr__(self):
        return "Pattern({!r}, similar={}, offset=({}, {}))".format(self.path, self.similarity, self.dx, self.dy)


def setBundlePath(path):
    _STATE["bundle"] = os.path.abspath(path) if path else None


def getBundlePath():
    return _STATE["bundle"]


def addImagePath(path):
    absolute = os.path.abspath(path)
    if absolute not in _STATE["paths"]:
        _STATE["paths"].append(absolute)


def getImagePath():
    return list(_STATE["paths"])


def getLastMatch():
    return _STATE["last"]


def _resolve_image(path):
    names = [path] if os.path.splitext(path)[1] else [path + ".png", path]
    roots = [r for r in [_STATE["bundle"]] + _STATE["paths"] + [os.getcwd()] if r]
    for name in names:
        if os.path.isabs(name):
            if os.path.isfile(name):
                return name
            continue
        for root in roots:
            candidate = os.path.join(root, name)
            if os.path.isfile(candidate):
                return candidate
    raise FindFailed("image not found: {}".format(path))


def _matcher():
    if _STATE["matcher"] is None:
        _STATE["matcher"] = FeatureMatcher("sift", min_matches=4)
    return _STATE["matcher"]


def _scaled(image, scale):
    if scale == 1.0 or cv2 is None:
        return image
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def _scale_for(template):
    side = min(template.shape[0], template.shape[1])
    if side >= _UPSCALE_MIN:
        return 1.0
    return min(_UPSCALE_CAP, float(_UPSCALE_MIN) / max(1, side))


def _locate_scaled(template, scene, similar):
    scale = _scale_for(template)
    result = _matcher().locate(_scaled(template, scale), _scaled(scene, scale), min_matches=4)
    required = max(4, int(round(similar * _SCORE_INLIERS)))
    if result.inliers < required:
        raise VisionError("{} inliers below required {}".format(result.inliers, required))
    if scale != 1.0:
        cx, cy = result.center
        x, y, w, h = result.bbox
        corners = [[px / scale, py / scale] for px, py in result.corners]
        result = MatchResult((cx / scale, cy / scale), corners, (x / scale, y / scale, w / scale, h / scale), result.inliers)
    return result


def _tile_origins(total, tile, step):
    last = max(total - tile, 0)
    origins = list(range(0, last + 1, step))
    if origins[-1] != last:
        origins.append(last)
    return origins


def _dedupe(matches, tw, th):
    kept = []
    for match in matches:
        center = match.getCenter()
        clones = [k for k in kept if abs(center.x - k.getCenter().x) < tw // 2 and abs(center.y - k.getCenter().y) < th // 2]
        if not clones:
            kept.append(match)
    return kept


def _as_pattern(target):
    if isinstance(target, Pattern):
        return target
    if isinstance(target, str):
        return Pattern(target)
    raise FindFailed("expected an image path or Pattern, got {!r}".format(target))


def _parse_type_args(args):
    items = list(args)
    modifiers = 0
    if items and isinstance(items[-1], int):
        modifiers = items.pop()
    if len(items) == 2:
        return items[0], str(items[1]), modifiers
    if len(items) == 1:
        return None, str(items[0]), modifiers
    raise TypeError("expected (text), (text, modifiers), (target, text) or (target, text, modifiers)")


def _split_keys(text):
    parts = []
    buff = []
    for ch in text:
        key = _CHAR_TO_KEY.get(ch)
        if key is None:
            buff.append(ch)
            continue
        if buff:
            parts.append(("".join(buff), None))
            buff = []
        parts.append((None, key))
    if buff:
        parts.append(("".join(buff), None))
    return parts


def _get_clipboard():
    if _IS_WINDOWS:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                return str(win32clipboard.GetClipboardData())
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return ""
    for tool in (["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
        try:
            done = subprocess.run(tool, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
            if done.returncode == 0:
                return done.stdout.decode("utf-8", "replace")
        except Exception:
            continue
    return ""


def _flash_rect(x, y, w, h, seconds):
    if not _IS_WINDOWS:
        time.sleep(max(0.0, float(seconds)))
        return
    try:
        import win32con
        import win32gui
        dc = win32gui.GetDC(0)
        pen = win32gui.CreatePen(win32con.PS_SOLID, 3, 0x0000FF)
        old_pen = win32gui.SelectObject(dc, pen)
        old_brush = win32gui.SelectObject(dc, win32gui.GetStockObject(win32con.NULL_BRUSH))
        deadline = time.time() + max(0.2, float(seconds))
        while time.time() < deadline:
            win32gui.Rectangle(dc, int(x), int(y), int(x + w), int(y + h))
            time.sleep(0.1)
        win32gui.SelectObject(dc, old_pen)
        win32gui.SelectObject(dc, old_brush)
        win32gui.DeleteObject(pen)
        win32gui.ReleaseDC(0, dc)
        win32gui.InvalidateRect(0, None, True)
    except Exception:
        pass


class Env:
    @staticmethod
    def getOS():
        return platform.system()

    @staticmethod
    def getOSVersion():
        return platform.version()

    @staticmethod
    def isWindows():
        return _IS_WINDOWS

    @staticmethod
    def isLinux():
        return platform.system() == "Linux"

    @staticmethod
    def isMac():
        return platform.system() == "Darwin"

    @staticmethod
    def getMouseLocation():
        x, y = _screen().backend.cursor_position()
        return Location(x, y)

    @staticmethod
    def getScreenSize():
        width, height = _screen()._bounds()
        return Region(0, 0, width, height)

    @staticmethod
    def getClipboard():
        return _get_clipboard()

    @staticmethod
    def setClipboard(text):
        return _set_clipboard(str(text))


def _set_clipboard(text):
    if _IS_WINDOWS:
        try:
            import win32clipboard
            import win32con
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception:
            return False
    for tool in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            done = subprocess.run(tool, input=text.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if done.returncode == 0:
                return True
        except Exception:
            continue
    return False


class Region:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = int(x)
        self.y = int(y)
        self.w = int(w)
        self.h = int(h)

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def getW(self):
        return self.w

    def getH(self):
        return self.h

    def getCenter(self):
        return Location(self.x + self.w // 2, self.y + self.h // 2)

    def getTarget(self):
        return self.getCenter()

    def getLastMatch(self):
        return _STATE["last"]

    def offset(self, dx, dy):
        return Region(self.x + dx, self.y + dy, self.w, self.h)

    def grow(self, pixels):
        return Region(self.x - pixels, self.y - pixels, self.w + 2 * pixels, self.h + 2 * pixels)

    def _bounds(self):
        screen = _screen()
        try:
            if screen.w == 0:
                screen._capture()
        except Exception:
            pass
        return (screen.w or 100000, screen.h or 100000)

    def nearby(self, range_px=50):
        return self.grow(int(range_px))

    def above(self, range_px=None):
        height = int(range_px) if range_px is not None else max(0, self.y)
        return Region(self.x, self.y - height, self.w, height)

    def below(self, range_px=None):
        height = int(range_px) if range_px is not None else max(0, self._bounds()[1] - self.y - self.h)
        return Region(self.x, self.y + self.h, self.w, height)

    def left(self, range_px=None):
        width = int(range_px) if range_px is not None else max(0, self.x)
        return Region(self.x - width, self.y, width, self.h)

    def right(self, range_px=None):
        width = int(range_px) if range_px is not None else max(0, self._bounds()[0] - self.x - self.w)
        return Region(self.x + self.w, self.y, width, self.h)

    def union(self, other):
        x = min(self.x, other.x)
        y = min(self.y, other.y)
        w = max(self.x + self.w, other.x + other.w) - x
        h = max(self.y + self.h, other.y + other.h) - y
        return Region(x, y, w, h)

    def intersection(self, other):
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        w = min(self.x + self.w, other.x + other.w) - x
        h = min(self.y + self.h, other.y + other.h) - y
        return Region(x, y, w, h) if w > 0 and h > 0 else None

    def setROI(self, x, y, w, h):
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)
        return self

    def highlight(self, seconds=None):
        _flash_rect(self.x, self.y, self.w, self.h, Settings.DefaultHighlightTime if seconds is None else float(seconds))
        return self

    def _capture_rect(self):
        return Rect(self.x, self.y, self.w, self.h) if self.w > 0 and self.h > 0 else None

    def _capture(self):
        return _screen().backend.capture(self._capture_rect())

    def _to_match(self, result, pattern):
        x, y, w, h = result.bbox
        cx, cy = result.center
        score = min(1.0, result.inliers / _SCORE_INLIERS)
        target = Location(self.x + cx + pattern.dx, self.y + cy + pattern.dy)
        return Match(self.x + x, self.y + y, w, h, score, target)

    def _find_once(self, pattern):
        template = load_image(_resolve_image(pattern.path))
        scene = self._capture()
        similar = Settings.MinSimilarity if pattern.similarity is None else pattern.similarity
        return self._to_match(_locate_scaled(template, scene, similar), pattern)

    def _poll(self, pattern, timeout, want_present):
        deadline = time.time() + max(0.0, float(timeout))
        while True:
            _pause_gate()
            try:
                found = self._find_once(pattern)
            except VisionError:
                found = None
            if want_present and found is not None:
                _STATE["last"] = found
                return found
            if not want_present and found is None:
                return True
            if time.time() >= deadline:
                return None if want_present else False
            time.sleep(1.0 / max(0.5, Settings.ObserveScanRate))

    def find(self, target):
        return self.wait(target)

    def wait(self, target, timeout=None, autoScroll=False):
        pattern = _as_pattern(target)
        found = self._poll(pattern, Settings.AutoWaitTimeout if timeout is None else timeout, True)
        if found is None and autoScroll:
            found = self._scroll_hunt(pattern)
        if found is None:
            raise FindFailed("not found on screen: {}".format(pattern.path))
        return found

    def _scroll_hunt(self, pattern):
        backend = _screen().backend
        for dx, dy in _AUTO_SCROLL_PLAN:
            try:
                backend.scroll(dx, dy)
            except Exception:
                return None
            time.sleep(0.35)
            found = self._poll(pattern, 0.0, True)
            if found is not None:
                return found
        return None

    def exists(self, target, timeout=0.0):
        return self._poll(_as_pattern(target), timeout, True)

    def waitVanish(self, target, timeout=None):
        return self._poll(_as_pattern(target), Settings.AutoWaitTimeout if timeout is None else timeout, False)

    def findAll(self, target):
        pattern = _as_pattern(target)
        template = load_image(_resolve_image(pattern.path))
        scene = self._capture()
        similar = Settings.MinSimilarity if pattern.similarity is None else pattern.similarity
        matches = self._collect_masked(template, scene, similar, pattern)
        if not matches:
            matches = self._collect_tiled(template, scene, similar, pattern)
        if not matches:
            raise FindFailed("not found on screen: {}".format(pattern.path))
        return matches

    def _collect_masked(self, template, scene, similar, pattern):
        matches = []
        work = scene.copy()
        for _ in range(_FIND_ALL_LIMIT):
            try:
                result = _locate_scaled(template, work, similar)
            except VisionError:
                break
            matches.append(self._to_match(result, pattern))
            x, y, w, h = [int(round(v)) for v in result.bbox]
            x, y = max(0, x), max(0, y)
            if w < 2 or h < 2:
                break
            work[y:y + h, x:x + w] = 0
        return _dedupe(matches, template.shape[1], template.shape[0])

    def _collect_tiled(self, template, scene, similar, pattern):
        th, tw = template.shape[:2]
        sh, sw = scene.shape[:2]
        tile_h = min(sh, max(2 * th, 160))
        tile_w = min(sw, max(2 * tw, 160))
        found = []
        for oy in _tile_origins(sh, tile_h, max(1, tile_h // 2)):
            for ox in _tile_origins(sw, tile_w, max(1, tile_w // 2)):
                crop = scene[oy:oy + tile_h, ox:ox + tile_w]
                if crop.shape[0] < th or crop.shape[1] < tw:
                    continue
                try:
                    result = _locate_scaled(template, crop, similar)
                except VisionError:
                    continue
                found.append(Region(self.x + ox, self.y + oy, 0, 0)._to_match(result, pattern))
        return _dedupe(found, tw, th)

    def _locate_target(self, target, auto_scroll=False):
        if target is None:
            return self.getCenter()
        if isinstance(target, Location):
            return target
        if isinstance(target, Region):
            return target.getTarget()
        if isinstance(target, (tuple, list)) and len(target) == 2:
            return Location(target[0], target[1])
        return self.wait(target, autoScroll=auto_scroll).getTarget()

    def hover(self, target=None):
        loc = self._locate_target(target)
        _screen().backend.move_mouse(loc.x, loc.y)
        if Settings.MoveMouseDelay:
            time.sleep(Settings.MoveMouseDelay)
        return loc

    def _click(self, target, button, clicks, modifiers, auto_scroll=False):
        _pause_gate()
        loc = self._locate_target(target, auto_scroll)
        backend = _screen().backend
        if Settings.ClickDelay:
            time.sleep(Settings.ClickDelay)
        names = _mod_names(modifiers)
        for name in names:
            backend.key_down(name)
        try:
            backend.click(loc.x, loc.y, button=button, clicks=clicks)
        finally:
            for name in reversed(names):
                backend.key_up(name)
        return 1

    def click(self, target=None, modifiers=0, autoScroll=False):
        return self._click(target, Button.LEFT, 1, modifiers, autoScroll)

    def doubleClick(self, target=None, modifiers=0):
        return self._click(target, Button.LEFT, 2, modifiers)

    def rightClick(self, target=None, modifiers=0):
        return self._click(target, Button.RIGHT, 1, modifiers)

    def dragDrop(self, source, dest):
        start = self._locate_target(source)
        end = self._locate_target(dest)
        backend = _screen().backend
        backend.move_mouse(start.x, start.y)
        time.sleep(max(0.0, Settings.DelayBeforeMouseDown))
        backend.mouse_down(Button.LEFT)
        time.sleep(max(0.0, Settings.DelayBeforeDrag))
        backend.move_mouse(end.x, end.y)
        time.sleep(max(0.0, Settings.DelayBeforeDrop))
        backend.mouse_up(Button.LEFT)
        return 1

    def wheel(self, *args):
        items = list(args)
        target = items.pop(0) if len(items) == 3 else None
        direction, steps = int(items[0]), int(items[1])
        if target is not None:
            self.hover(target)
        _screen().backend.scroll(0, -direction * steps)
        return 1

    def type(self, *args):
        _pause_gate()
        target, text, modifiers = _parse_type_args(args)
        if target is not None:
            self.click(target)
        backend = _screen().backend
        if modifiers:
            names = _mod_names(modifiers)
            for ch in text:
                backend.key_press(*(names + [_key_arg(ch)]))
            return 1
        for literal, key in _split_keys(text):
            if key is None:
                backend.type_text(literal)
            else:
                backend.key_press(key)
            if Settings.TypeDelay:
                time.sleep(Settings.TypeDelay)
        return 1

    def paste(self, *args):
        target, text, _ = _parse_type_args(args)
        if target is not None:
            self.click(target)
        backend = _screen().backend
        if _set_clipboard(text):
            backend.key_press("ctrl", "v")
        else:
            backend.type_text(text)
        return 1

    def text(self):
        try:
            from ..packaging.runtime_paths import configured_ocr
            return configured_ocr(lang=Settings.OcrLanguage).read_text(self._capture())
        except Exception:
            return ""

    def __repr__(self):
        return "Region({}, {}, {}, {})".format(self.x, self.y, self.w, self.h)


class Match(Region):
    __slots__ = ("score", "target")

    def __init__(self, x, y, w, h, score, target):
        super().__init__(x, y, w, h)
        self.score = float(score)
        self.target = target

    def getScore(self):
        return self.score

    def getTarget(self):
        return self.target

    def __repr__(self):
        return "Match({}, {}, {}, {}, score={:.2f})".format(self.x, self.y, self.w, self.h, self.score)


class Screen(Region):
    __slots__ = ("_backend",)

    def __init__(self, backend=None):
        super().__init__(0, 0, 0, 0)
        self._backend = backend

    @property
    def backend(self):
        if self._backend is None:
            self._backend = OSFacadeFactory.create()
        return self._backend

    def _capture(self):
        frame = self.backend.capture(self._capture_rect())
        if self.w == 0 and frame is not None:
            self.h, self.w = int(frame.shape[0]), int(frame.shape[1])
        return frame

    def capture(self, region=None):
        if region is None:
            return self._capture()
        rect = region if isinstance(region, Rect) else Rect(region.x, region.y, region.w, region.h)
        return self.backend.capture(rect)


class WindowRegion(Region):
    __slots__ = ("title", "pid")

    def __init__(self, title, pid=None):
        super().__init__(0, 0, 0, 0)
        self.title = title
        self.pid = pid
        self._sync()

    def _window_handle(self):
        return _app_window(self.title, self.pid)

    def _need_handle(self):
        handle = self._window_handle()
        if handle is None:
            raise FindFailed("window not found: {!r}".format(self.title))
        return handle

    def _sync(self):
        handle = self._window_handle()
        rect = None
        if handle is not None:
            try:
                rect = _screen().backend.window_rect(handle)
            except Exception:
                rect = handle.rect
        if rect is not None:
            self.setROI(rect.x, rect.y, rect.width, rect.height)
        return self

    def _capture(self):
        self._sync()
        return super()._capture()

    def getCenter(self):
        self._sync()
        return super().getCenter()

    def focus(self):
        try:
            _screen().backend.focus_window(self._need_handle())
        except FindFailed:
            raise
        except Exception:
            pass
        return self._sync()

    def moveTo(self, x, y):
        _screen().backend.move_window(self._need_handle(), x, y)
        return self._sync()

    def resize(self, width, height):
        _screen().backend.move_window(self._need_handle(), None, None, width, height)
        return self._sync()

    def setBounds(self, x, y, width, height):
        _screen().backend.move_window(self._need_handle(), x, y, width, height)
        return self._sync()

    def maximize(self):
        _screen().backend.window_state(self._need_handle(), "maximize")
        return self._sync()

    def minimize(self):
        _screen().backend.window_state(self._need_handle(), "minimize")
        return self._sync()

    def restore(self):
        _screen().backend.window_state(self._need_handle(), "restore")
        return self._sync()

    def __repr__(self):
        return "WindowRegion({!r}, {}, {}, {}, {})".format(self.title, self.x, self.y, self.w, self.h)


class App:
    __slots__ = ("title", "command", "pid")

    def __init__(self, title, command=None, pid=None):
        self.title = title
        self.command = command or title
        self.pid = pid

    def _handle(self):
        return _app_window(self.title, self.pid)

    def open(self, wait=5):
        self.pid = _launch(self.command)
        if self.pid is None:
            return False
        deadline = time.time() + max(0.0, float(wait))
        while time.time() < deadline:
            if self._handle() is not None:
                break
            time.sleep(0.25)
        return self

    def isRunning(self):
        return self._handle() is not None

    def focus(self):
        handle = self._handle()
        if handle is None:
            return False
        try:
            _screen().backend.focus_window(handle)
            return True
        except Exception:
            return False

    def close(self):
        handle = self._handle()
        pid = self.pid or (handle.pid if handle else None)
        if not pid:
            return False
        try:
            os.kill(int(pid), signal.SIGTERM)
            return True
        except Exception:
            return False

    def window(self, index=0):
        return WindowRegion(self.title, self.pid)

    def __repr__(self):
        return "App({!r}, pid={})".format(self.title, self.pid)


def windowRegion(title):
    return WindowRegion(title)


def _screen():
    if _STATE["screen"] is None:
        _STATE["screen"] = Screen()
    return _STATE["screen"]


def use_screen(screen):
    _STATE["screen"] = screen
    _STATE["last"] = None


def use_inspector(inspector):
    _STATE["inspector"] = inspector


def _inspector():
    if _STATE["inspector"] is None:
        _STATE["inspector"] = InspectorFactory.create()
    return _STATE["inspector"]


class Element:
    __slots__ = ("_node",)

    def __init__(self, node):
        self._node = node

    def __getattr__(self, item):
        return getattr(object.__getattribute__(self, "_node"), item)

    def _box(self):
        box = self._node.bounding_box
        if box is None:
            raise FindFailed("element has no bounding box: {!r}".format(self._node))
        return box

    def getCenter(self):
        x, y = self._box().center
        return Location(x, y)

    def getTarget(self):
        return self.getCenter()

    def region(self):
        box = self._box()
        return Region(box.x, box.y, box.width, box.height)

    def getName(self):
        return self._node.name

    def getRole(self):
        return self._node.role

    def getText(self):
        return self._node.value or self._node.name or ""

    def click(self, modifiers=0):
        return _screen()._click(self.getCenter(), Button.LEFT, 1, modifiers)

    def doubleClick(self, modifiers=0):
        return _screen()._click(self.getCenter(), Button.LEFT, 2, modifiers)

    def rightClick(self, modifiers=0):
        return _screen()._click(self.getCenter(), Button.RIGHT, 1, modifiers)

    def hover(self):
        return _screen().hover(self.getCenter())

    def type(self, text, modifiers=0):
        return _screen().type(self.getCenter(), str(text), modifiers) if modifiers else _screen().type(self.getCenter(), str(text))

    def paste(self, text):
        return _screen().paste(self.getCenter(), str(text))

    def clear(self):
        self.click()
        backend = _screen().backend
        backend.key_press("ctrl", "a")
        backend.key_press("delete")
        return self

    def setText(self, text):
        self.clear()
        _screen().type(str(text))
        return self

    write = setText

    def isChecked(self):
        return "checked" in self._node.states

    def isSelected(self):
        return "selected" in self._node.states

    def isEnabled(self):
        return "IsEnabled" in self._node.states

    def toggle(self):
        self.click()
        return self

    def check(self):
        if not self.isChecked():
            self.click()
        return self

    def uncheck(self):
        if self.isChecked():
            self.click()
        return self

    def child(self, role=None, name=None, automation_id=None):
        node = _inspector().find(role=role, name=name, automation_id=automation_id, element=self._node)
        return Element(node)

    def find(self, role=None, name=None, automation_id=None):
        return self.child(role=role, name=name, automation_id=automation_id)

    def expand(self):
        if "expanded" not in self._node.states:
            self.click()
        return self

    def collapse(self):
        if "expanded" in self._node.states:
            self.click()
        return self

    def selectItem(self, item):
        Element(_inspector().find(name=item, element=self._node)).click()
        return self

    def select(self, item):
        self.click()
        time.sleep(0.3)
        try:
            node = _inspector().find(name=item, role="item")
        except Exception:
            node = _inspector().find(name=item)
        Element(node).click()
        return self

    def highlight(self, seconds=None):
        box = self._box()
        _flash_rect(box.x, box.y, box.width, box.height, Settings.DefaultHighlightTime if seconds is None else float(seconds))
        return self

    def __repr__(self):
        return "Element({!r})".format(self._node)


def _window_node(inspector, window):
    needle = str(window).lower()
    for child in inspector.children(inspector.root()):
        if child is not None and needle in (child.name or "").lower():
            return child
    return None


def _in_region(node, region):
    box = node.bounding_box
    if box is None:
        return False
    cx, cy = box.center
    return region.x <= cx <= region.x + region.w and region.y <= cy <= region.y + region.h


def findElement(role=None, name=None, automation_id=None, window=None, region=None, timeout=0):
    inspector = _inspector()
    deadline = time.time() + max(0.0, float(timeout))
    while True:
        scope = _window_node(inspector, window) if window else inspector.root()
        if scope is not None:
            for node in inspector.walk(scope):
                if node.matches(role=role, name=name, automation_id=automation_id) and (region is None or _in_region(node, region)):
                    return Element(node)
        if time.time() >= deadline:
            break
        time.sleep(0.3)
    where = " in window {!r}".format(window) if window else ""
    raise FindFailed("no element role={!r} name={!r} id={!r}{}".format(role, name, automation_id, where))


def clickElement(role=None, name=None, automation_id=None, button=Button.LEFT, clicks=1, window=None, region=None, timeout=0):
    element = findElement(role=role, name=name, automation_id=automation_id, window=window, region=region, timeout=timeout)
    loc = element.getCenter()
    _screen().backend.click(loc.x, loc.y, button=button, clicks=clicks)
    return element


_HEALED = {}
_ANCHOR_ORDER = ("element", "image", "text")


class Target:
    __slots__ = ("name", "role", "automation_id", "window", "region", "image", "text", "dx", "dy")

    def __init__(self, name=None, role=None, automation_id=None, window=None, region=None, image=None, text=None, dx=0, dy=0):
        self.name = name
        self.role = role
        self.automation_id = automation_id
        self.window = window
        self.region = region
        self.image = image
        self.text = text
        self.dx = int(dx)
        self.dy = int(dy)

    def targetOffset(self, dx, dy=None):
        ox, oy = _offset_pair(dx, dy)
        return Target(self.name, self.role, self.automation_id, self.window, self.region, self.image, self.text, ox, oy)

    def _key(self):
        return (self.automation_id, self.name, self.role, self.window, self.image, self.text)

    def _scope(self):
        if isinstance(self.region, Region):
            return self.region
        if self.window:
            return WindowRegion(self.window)
        return _screen()

    def _by_element(self):
        if not (self.automation_id or self.name or self.role):
            return None
        scoped = self.region if isinstance(self.region, Region) else None
        found = findElement(role=self.role, name=self.name, automation_id=self.automation_id, window=self.window, region=scoped)
        return found.getCenter()

    def _by_image(self):
        if not self.image:
            return None
        found = self._scope().exists(Pattern(self.image), 0)
        return found.getTarget() if found is not None else None

    def _by_text(self):
        if not self.text:
            return None
        from ..packaging.runtime_paths import configured_ocr
        scope = self._scope()
        box = configured_ocr().locate_text(scope._capture(), self.text)
        if box is None:
            return None
        cx, cy = box.center
        return Location(scope.x + cx, scope.y + cy)

    def resolve(self):
        order = list(_ANCHOR_ORDER)
        healed = _HEALED.get(self._key())
        if healed in order:
            order.remove(healed)
            order.insert(0, healed)
        for strategy in order:
            try:
                loc = getattr(self, "_by_" + strategy)()
            except Exception:
                loc = None
            if loc is not None:
                _HEALED[self._key()] = strategy
                return Location(loc.x + self.dx, loc.y + self.dy)
        raise FindFailed("no anchor resolved {!r}".format(self))

    def exists(self):
        try:
            return self.resolve()
        except FindFailed:
            return None

    def click(self, modifiers=0):
        return _screen()._click(self.resolve(), Button.LEFT, 1, modifiers)

    def doubleClick(self, modifiers=0):
        return _screen()._click(self.resolve(), Button.LEFT, 2, modifiers)

    def rightClick(self, modifiers=0):
        return _screen()._click(self.resolve(), Button.RIGHT, 1, modifiers)

    def hover(self):
        return _screen().hover(self.resolve())

    def __repr__(self):
        return "Target(name={!r}, id={!r}, window={!r}, image={!r}, text={!r})".format(self.name, self.automation_id, self.window, self.image, self.text)


def findUI(kind="any", text=None, region=None):
    from ..core.vision.ui_finder import find_ui
    scope = region if isinstance(region, Region) else _screen()
    frame = scope._capture()
    ocr = None
    if text:
        from ..packaging.runtime_paths import configured_ocr
        ocr = configured_ocr()
    boxes = find_ui(frame, kind, text, ocr)
    return [Region(scope.x + box.x, scope.y + box.y, box.width, box.height) for box in boxes]


def _delegate(name):
    def call(*args, **kwargs):
        return getattr(_screen(), name)(*args, **kwargs)
    call.__name__ = name
    return call


_DELEGATES = ("find", "findAll", "exists", "wait", "waitVanish", "click", "doubleClick", "rightClick", "hover", "dragDrop", "wheel", "type", "paste", "capture")

for _name in _DELEGATES:
    globals()[_name] = _delegate(_name)


def sleep(seconds):
    deadline = time.time() + max(0.0, float(seconds))
    while True:
        _pause_gate()
        remaining = deadline - time.time()
        if remaining <= 0:
            return
        time.sleep(min(0.1, remaining))


def mouseMove(target=None):
    return _screen().hover(target)


def mouseDown(button=Button.LEFT):
    _screen().backend.mouse_down(button)


def mouseUp(button=Button.LEFT):
    _screen().backend.mouse_up(button)


def keyDown(key):
    _screen().backend.key_down(_key_arg(key))


def keyUp(key):
    _screen().backend.key_up(_key_arg(key))


def popup(message, title="RPA Studio"):
    if _IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0)
            return
        except Exception:
            pass
    print("[popup] {}: {}".format(title, message))


def _command_stem(command):
    first = str(command or "").strip().strip('"')
    if not first:
        return ""
    first = first.split(" ")[0]
    return os.path.splitext(os.path.basename(first))[0].lower()


def _launch(command):
    try:
        if isinstance(command, str):
            if _IS_WINDOWS:
                try:
                    return subprocess.Popen(command).pid
                except Exception:
                    return subprocess.Popen(command, shell=True).pid
            return subprocess.Popen(command, shell=True).pid
        return subprocess.Popen(list(command)).pid
    except Exception:
        return None


def _app_window(title=None, pid=None, contains=True):
    backend = _screen().backend
    needle = str(title or "").lower()
    stem = "" if " " in needle else _command_stem(needle)
    if len(stem) < 3:
        stem = ""
    best = None
    best_rank = 99
    try:
        windows = backend.list_windows()
    except Exception:
        return None
    for handle in windows:
        if pid and handle.pid == pid:
            return handle
        text = (handle.title or "").lower()
        rank = None
        if needle and text == needle:
            rank = 0
        elif needle and contains and needle in text:
            rank = 1
        elif stem and contains and handle.pid:
            try:
                pname = backend.process_name(handle.pid)
            except Exception:
                pname = ""
            if pname and stem in pname:
                rank = 2
        if rank is not None and rank < best_rank:
            best = handle
            best_rank = rank
    return best


def openApp(command, wait=5):
    app = App(_command_stem(command) or str(command), command)
    return app if app.open(wait) else False


def switchApp(title, contains=True):
    handle = _app_window(title, None, contains)
    if handle is None:
        return False
    try:
        _screen().backend.focus_window(handle)
        return True
    except Exception:
        return False


def closeApp(title, contains=True):
    handle = _app_window(title, None, contains)
    if handle is None or not handle.pid:
        return False
    try:
        os.kill(int(handle.pid), signal.SIGTERM)
        return True
    except Exception:
        return False


_EXPORTS = (
    "App", "Button", "Element", "Env", "FindFailed", "Key", "KeyModifier", "Location", "Match", "Offset", "Pattern", "Region", "Screen", "Settings", "Target",
    "WHEEL_DOWN", "WHEEL_UP", "windowRegion",
    "addImagePath", "capture", "click", "clickElement", "closeApp", "doubleClick", "dragDrop", "exists", "find",
    "findAll", "findElement", "findUI", "getBundlePath", "getImagePath", "getLastMatch", "hover", "keyDown", "keyUp",
    "mouseDown", "mouseMove", "mouseUp", "openApp", "paste", "popup", "rightClick", "setBundlePath", "sleep",
    "switchApp", "type", "wait", "waitVanish", "wheel",
)


def build_scope(script_dir=None):
    if script_dir:
        setBundlePath(script_dir)
    module = sys.modules[__name__]
    return {name: getattr(module, name) for name in _EXPORTS}
