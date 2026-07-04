import threading
import time

from .base import InspectorFactory
from ..os_facade.base import OSFacadeFactory


class InspectorDaemon:
    def __init__(self, inspector=None, pointer=None, interval=0.3, on_element=None, deep=False):
        self._inspector = inspector or InspectorFactory.create()
        self._pointer = pointer or OSFacadeFactory.create()
        self._interval = float(interval)
        self._on_element = on_element
        self._deep = bool(deep)
        self._stop = threading.Event()
        self._thread = None
        self._last = None

    def inspect_point(self, x, y):
        if self._deep:
            try:
                return self._inspector.deepest_at(x, y)
            except Exception:
                pass
        return self._inspector.element_at(x, y)

    def inspect_cursor(self):
        x, y = self._pointer.cursor_position()
        return self.inspect_point(x, y)

    def inspect_focused(self):
        return self._inspector.focused_element()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self):
        while not self._stop.is_set():
            try:
                element = self.inspect_cursor()
            except Exception:
                element = None
            if element is not None:
                key = (element.backend, element.automation_id, element.name, element.role, self._box_key(element))
                if key != self._last:
                    self._last = key
                    self._emit(element)
            self._stop.wait(self._interval)

    def _emit(self, element):
        if self._on_element is not None:
            self._on_element(element)
        else:
            print(element.to_json())

    @staticmethod
    def _box_key(element):
        return element.bounding_box.as_tuple() if element.bounding_box is not None else None


def run_spy(interval=0.3):
    daemon = InspectorDaemon(interval=interval)
    daemon.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        daemon.stop()
