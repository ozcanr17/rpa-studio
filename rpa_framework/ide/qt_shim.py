import importlib

from ..core.exceptions import BackendError

_BINDINGS = ("PyQt6", "PySide6")
_STATE = {}


class QtApi:
    __slots__ = ("binding", "QtCore", "QtGui", "QtWidgets", "Signal", "Slot")

    def __init__(self, binding, core, gui, widgets):
        self.binding = binding
        self.QtCore = core
        self.QtGui = gui
        self.QtWidgets = widgets
        self.Signal = getattr(core, "pyqtSignal", None) or getattr(core, "Signal", None)
        self.Slot = getattr(core, "pyqtSlot", None) or getattr(core, "Slot", None)


def load_qt():
    api = _STATE.get("api")
    if api is not None:
        return api
    errors = []
    for name in _BINDINGS:
        try:
            core = importlib.import_module(name + ".QtCore")
            gui = importlib.import_module(name + ".QtGui")
            widgets = importlib.import_module(name + ".QtWidgets")
        except Exception as exc:
            errors.append("{}: {}".format(name, exc))
            continue
        api = QtApi(name, core, gui, widgets)
        _STATE["api"] = api
        return api
    raise BackendError("no Qt binding available ({})".format("; ".join(errors)))


def cached_builder(builder):
    cache = {}

    def factory(qt=None):
        api = qt or load_qt()
        cls = cache.get(api.binding)
        if cls is None:
            cls = builder(api)
            cache[api.binding] = cls
        return cls

    factory.__name__ = builder.__name__
    return factory
