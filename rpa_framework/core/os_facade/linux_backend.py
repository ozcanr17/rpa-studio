import shutil
import subprocess

try:
    import mss
    import numpy as np
except ImportError:
    mss = None
    np = None

from .base import OSBackend, Rect, WindowHandle, mss_grab, register_backend
from ..exceptions import BackendError

_BUTTONS = {"left": 1, "middle": 2, "right": 3}


def _run(args, capture=True):
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError:
        raise BackendError("binary not found: {}".format(args[0]))
    if result.returncode != 0:
        raise BackendError("{} failed: {}".format(args[0], result.stderr.decode("utf-8", "replace").strip()))
    return result.stdout.decode("utf-8", "replace") if capture else ""


def _parse_shell(text):
    data = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            data[key.strip()] = value.strip()
    return data


@register_backend("linux")
class LinuxBackend(OSBackend):
    def __init__(self):
        if shutil.which("xdotool") is None:
            raise BackendError("xdotool is required on Linux")

    def move_mouse(self, x, y):
        _run(["xdotool", "mousemove", str(int(x)), str(int(y))], capture=False)

    def click(self, x=None, y=None, button="left", clicks=1):
        if x is not None and y is not None:
            self.move_mouse(x, y)
        _run(["xdotool", "click", "--repeat", str(max(1, int(clicks))), str(_BUTTONS.get(button, 1))], capture=False)

    def mouse_down(self, button="left"):
        _run(["xdotool", "mousedown", str(_BUTTONS.get(button, 1))], capture=False)

    def mouse_up(self, button="left"):
        _run(["xdotool", "mouseup", str(_BUTTONS.get(button, 1))], capture=False)

    def scroll(self, dx, dy):
        steps = abs(int(dy))
        if steps:
            _run(["xdotool", "click", "--repeat", str(steps), "4" if dy > 0 else "5"], capture=False)
        side = abs(int(dx))
        if side:
            _run(["xdotool", "click", "--repeat", str(side), "7" if dx > 0 else "6"], capture=False)

    def type_text(self, text):
        _run(["xdotool", "type", "--clearmodifiers", "--", text], capture=False)

    def key_press(self, *keys):
        if keys:
            _run(["xdotool", "key", "+".join(keys)], capture=False)

    def key_down(self, key):
        _run(["xdotool", "keydown", key], capture=False)

    def key_up(self, key):
        _run(["xdotool", "keyup", key], capture=False)

    def capture(self, region=None):
        if mss is None or np is None:
            raise BackendError("mss and numpy are required for capture")
        return mss_grab(region)

    def list_windows(self):
        out = _run(["xdotool", "search", "--onlyvisible", "--name", ""])
        return [self._build_handle(wid) for wid in out.split()]

    def active_window(self):
        wid = _run(["xdotool", "getactivewindow"]).strip()
        return self._build_handle(wid) if wid else None

    def window_rect(self, handle):
        wid = handle.native_id if isinstance(handle, WindowHandle) else handle
        data = _parse_shell(_run(["xdotool", "getwindowgeometry", "--shell", str(wid)]))
        return Rect(data.get("X", 0), data.get("Y", 0), data.get("WIDTH", 0), data.get("HEIGHT", 0))

    def focus_window(self, handle):
        wid = handle.native_id if isinstance(handle, WindowHandle) else handle
        _run(["xdotool", "windowactivate", "--sync", str(wid)], capture=False)

    def move_window(self, handle, x=None, y=None, width=None, height=None):
        wid = str(handle.native_id if isinstance(handle, WindowHandle) else handle)
        try:
            rect = self.window_rect(wid)
        except Exception:
            rect = Rect(0, 0, 800, 600)
        try:
            if x is not None or y is not None:
                nx = rect.x if x is None else int(x)
                ny = rect.y if y is None else int(y)
                _run(["xdotool", "windowmove", wid, str(nx), str(ny)], capture=False)
            if width is not None or height is not None:
                nw = rect.width if width is None else int(width)
                nh = rect.height if height is None else int(height)
                _run(["xdotool", "windowsize", wid, str(nw), str(nh)], capture=False)
            return True
        except Exception:
            return False

    def window_state(self, handle, state):
        wid = str(handle.native_id if isinstance(handle, WindowHandle) else handle)
        wanted = str(state).lower()
        try:
            if wanted == "minimize":
                _run(["xdotool", "windowminimize", wid], capture=False)
            elif wanted == "maximize":
                _run(["xdotool", "windowmove", wid, "0", "0"], capture=False)
                _run(["xdotool", "windowsize", wid, "100%", "100%"], capture=False)
            else:
                _run(["xdotool", "windowactivate", wid], capture=False)
            return True
        except Exception:
            return False

    def process_name(self, pid):
        try:
            with open("/proc/{}/comm".format(int(pid)), "r", encoding="utf-8", errors="replace") as handle:
                return handle.read().strip().lower()
        except Exception:
            return ""

    def cursor_position(self):
        data = _parse_shell(_run(["xdotool", "getmouselocation", "--shell"]))
        return (int(data.get("X", 0)), int(data.get("Y", 0)))

    def _build_handle(self, wid):
        name = self._safe(["xdotool", "getwindowname", str(wid)])
        pid_raw = self._safe(["xdotool", "getwindowpid", str(wid)])
        try:
            rect = self.window_rect(wid)
        except BackendError:
            rect = None
        try:
            pid = int(pid_raw) if pid_raw else None
        except ValueError:
            pid = None
        return WindowHandle(str(wid), name, rect, pid)

    @staticmethod
    def _safe(args):
        try:
            return _run(args).strip()
        except BackendError:
            return ""
