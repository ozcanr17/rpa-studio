import abc
import platform

from ..exceptions import BackendError

_REGISTRY = {}
_ALIASES = {"Linux": "linux", "Windows": "windows"}


def frozen_build():
    return "__compiled__" in globals()


def prepare_com_codegen():
    if not frozen_build():
        return
    try:
        import comtypes.client
        comtypes.client.gen_dir = None
    except Exception:
        pass


def register_backend(name):
    def decorator(cls):
        _REGISTRY[name] = cls
        return cls
    return decorator


def mss_grab(region):
    import numpy as np
    import mss
    with mss.mss() as sct:
        if region is None:
            box = sct.monitors[0]
        else:
            r = region if isinstance(region, Rect) else Rect(*region)
            box = {"left": r.x, "top": r.y, "width": r.width, "height": r.height}
        frame = np.array(sct.grab(box))
    return frame[:, :, :3].copy()


def screen_origin():
    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[0]
        return (int(monitor["left"]), int(monitor["top"]))
    except Exception:
        return (0, 0)


class Rect:
    __slots__ = ("x", "y", "width", "height")

    def __init__(self, x, y, width, height):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)

    @property
    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    def contains(self, px, py):
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def as_tuple(self):
        return (self.x, self.y, self.width, self.height)

    def __repr__(self):
        return "Rect({}, {}, {}, {})".format(self.x, self.y, self.width, self.height)


class WindowHandle:
    __slots__ = ("native_id", "title", "rect", "pid")

    def __init__(self, native_id, title="", rect=None, pid=None):
        self.native_id = native_id
        self.title = title
        self.rect = rect
        self.pid = pid

    def __repr__(self):
        return "WindowHandle({}, {!r})".format(self.native_id, self.title)


class OSBackend(abc.ABC):
    @abc.abstractmethod
    def move_mouse(self, x, y):
        raise NotImplementedError

    @abc.abstractmethod
    def click(self, x=None, y=None, button="left", clicks=1):
        raise NotImplementedError

    @abc.abstractmethod
    def mouse_down(self, button="left"):
        raise NotImplementedError

    @abc.abstractmethod
    def mouse_up(self, button="left"):
        raise NotImplementedError

    @abc.abstractmethod
    def scroll(self, dx, dy):
        raise NotImplementedError

    @abc.abstractmethod
    def type_text(self, text):
        raise NotImplementedError

    @abc.abstractmethod
    def key_press(self, *keys):
        raise NotImplementedError

    @abc.abstractmethod
    def key_down(self, key):
        raise NotImplementedError

    @abc.abstractmethod
    def key_up(self, key):
        raise NotImplementedError

    @abc.abstractmethod
    def capture(self, region=None):
        raise NotImplementedError

    @abc.abstractmethod
    def list_windows(self):
        raise NotImplementedError

    @abc.abstractmethod
    def active_window(self):
        raise NotImplementedError

    @abc.abstractmethod
    def window_rect(self, handle):
        raise NotImplementedError

    @abc.abstractmethod
    def focus_window(self, handle):
        raise NotImplementedError

    @abc.abstractmethod
    def cursor_position(self):
        raise NotImplementedError

    def origin(self):
        return screen_origin()

    def process_name(self, pid):
        return ""

    def move_window(self, handle, x=None, y=None, width=None, height=None):
        return False

    def window_state(self, handle, state):
        return False


class OSFacadeFactory:
    @classmethod
    def create(cls, backend=None):
        key = backend or _ALIASES.get(platform.system())
        if key is None:
            raise BackendError("unsupported platform: {}".format(platform.system()))
        cls._load(key)
        impl = _REGISTRY.get(key)
        if impl is None:
            raise BackendError("no backend registered for '{}'".format(key))
        return impl()

    @staticmethod
    def _load(key):
        if key == "linux":
            from . import linux_backend
        elif key == "windows":
            from . import windows_backend
        else:
            raise BackendError("no loader for backend '{}'".format(key))
