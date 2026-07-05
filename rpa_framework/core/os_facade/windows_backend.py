import warnings

from .base import OSBackend, Rect, WindowHandle, mss_grab, prepare_com_codegen, register_backend
from ..exceptions import BackendError

warnings.filterwarnings("ignore", message="Revert to STA COM threading mode")

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    prepare_com_codegen()
    from pywinauto import mouse as pw_mouse
    from pywinauto import keyboard as pw_keyboard
except Exception:
    win32gui = None
    win32con = None
    win32api = None
    win32process = None
    pw_mouse = None
    pw_keyboard = None

try:
    import numpy as np
    import mss
except ImportError:
    np = None
    mss = None

_BUTTONS = {"left": "left", "middle": "middle", "right": "right"}


@register_backend("windows")
class WindowsBackend(OSBackend):
    _VK = {
        "ctrl": "VK_CONTROL",
        "control": "VK_CONTROL",
        "alt": "VK_MENU",
        "menu": "VK_MENU",
        "shift": "VK_SHIFT",
        "win": "VK_LWIN",
        "super": "VK_LWIN",
        "cmd": "VK_LWIN",
    }

    def __init__(self):
        if win32gui is None or pw_mouse is None:
            raise BackendError("pywin32 and pywinauto are required on Windows")

    def move_mouse(self, x, y):
        win32api.SetCursorPos((int(x), int(y)))

    def click(self, x=None, y=None, button="left", clicks=1):
        coords = (int(x), int(y)) if x is not None and y is not None else self.cursor_position()
        for _ in range(max(1, int(clicks))):
            pw_mouse.click(button=_BUTTONS.get(button, "left"), coords=coords)

    def mouse_down(self, button="left"):
        pw_mouse.press(button=_BUTTONS.get(button, "left"), coords=self.cursor_position())

    def mouse_up(self, button="left"):
        pw_mouse.release(button=_BUTTONS.get(button, "left"), coords=self.cursor_position())

    def scroll(self, dx, dy):
        if int(dy):
            pw_mouse.scroll(coords=self.cursor_position(), wheel_dist=int(dy))
        if int(dx):
            try:
                win32api.mouse_event(0x1000, 0, 0, int(dx) * 120, 0)
            except Exception:
                pass

    def type_text(self, text):
        pw_keyboard.send_keys(self._escape(text), with_spaces=True, pause=0)

    def key_press(self, *keys):
        if not keys:
            return
        if len(keys) == 1:
            pw_keyboard.send_keys(self._token(keys[0]), pause=0)
            return
        mods = keys[:-1]
        seq = "".join("{" + self._VK.get(m.lower(), m.upper()) + " down}" for m in mods)
        seq += self._token(keys[-1])
        seq += "".join("{" + self._VK.get(m.lower(), m.upper()) + " up}" for m in reversed(mods))
        pw_keyboard.send_keys(seq, pause=0)

    def key_down(self, key):
        pw_keyboard.send_keys("{" + self._VK.get(key.lower(), key.upper()) + " down}", pause=0)

    def key_up(self, key):
        pw_keyboard.send_keys("{" + self._VK.get(key.lower(), key.upper()) + " up}", pause=0)

    def capture(self, region=None):
        if mss is None or np is None:
            raise BackendError("mss and numpy are required for capture")
        return mss_grab(region)

    def list_windows(self):
        handles = []

        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                handles.append(self._build_handle(hwnd))
            return True

        win32gui.EnumWindows(_cb, None)
        return handles

    def active_window(self):
        hwnd = win32gui.GetForegroundWindow()
        return self._build_handle(hwnd) if hwnd else None

    @staticmethod
    def _hwnd(handle):
        return int(handle.native_id if isinstance(handle, WindowHandle) else handle)

    def window_rect(self, handle):
        left, top, right, bottom = win32gui.GetWindowRect(self._hwnd(handle))
        return Rect(left, top, right - left, bottom - top)

    def focus_window(self, handle):
        hwnd = self._hwnd(handle)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)

    def move_window(self, handle, x=None, y=None, width=None, height=None):
        hwnd = self._hwnd(handle)
        rect = self.window_rect(hwnd)
        nx = rect.x if x is None else int(x)
        ny = rect.y if y is None else int(y)
        nw = rect.width if width is None else int(width)
        nh = rect.height if height is None else int(height)
        try:
            win32gui.MoveWindow(hwnd, nx, ny, nw, nh, True)
            return True
        except Exception:
            return False

    def window_state(self, handle, state):
        codes = {"maximize": win32con.SW_MAXIMIZE, "minimize": win32con.SW_MINIMIZE, "restore": win32con.SW_RESTORE}
        try:
            win32gui.ShowWindow(self._hwnd(handle), codes.get(str(state).lower(), win32con.SW_RESTORE))
            return True
        except Exception:
            return False

    def process_name(self, pid):
        if not pid:
            return ""
        try:
            proc = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, int(pid))
        except Exception:
            return ""
        path = ""
        try:
            try:
                path = win32process.GetModuleFileNameEx(proc, 0)
            except Exception:
                path = ""
        finally:
            try:
                proc.Close()
            except Exception:
                pass
        return path.replace("\\", "/").rsplit("/", 1)[-1].lower()

    def cursor_position(self):
        return win32api.GetCursorPos()

    def _build_handle(self, hwnd):
        title = win32gui.GetWindowText(hwnd)
        try:
            rect = self.window_rect(hwnd)
        except Exception:
            rect = None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pid = None
        return WindowHandle(int(hwnd), title, rect, pid)

    @staticmethod
    def _token(key):
        return key if len(key) == 1 else "{" + key.upper() + "}"

    @staticmethod
    def _escape(text):
        specials = set("^+%~(){}[]")
        return "".join("{" + ch + "}" if ch in specials else ch for ch in text)
