import os
import sys
import traceback

from ..directives import strip_directives
from ..scripting import build_scope, friendly_error, grab_screenshot, run_compiled


class QueueStream:
    __slots__ = ("_queue", "_kind")

    def __init__(self, queue, kind):
        self._queue = queue
        self._kind = kind

    def write(self, text):
        if text:
            _put(self._queue, self._kind, text)
        return len(text)

    def flush(self):
        return None

    def isatty(self):
        return False


def _put(queue, kind, data):
    try:
        queue.put({"type": kind, "data": data})
    except Exception:
        pass


def _ensure_root():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.insert(0, root)


def _sink(queue):
    def emit(kind, data):
        _put(queue, kind, data)
    return emit


def run_script(path, queue, pause_event):
    _ensure_root()
    sys.stdout = QueueStream(queue, "stdout")
    sys.stderr = QueueStream(queue, "stderr")
    _put(queue, "started", path)
    exit_code = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            source = handle.read()
        code = compile(strip_directives(source), path, "exec")
        scope = build_scope(path, _sink(queue), pause_event)
        run_compiled(code, scope)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
    except Exception as exc:
        _put(queue, "stderr", traceback.format_exc())
        _put(queue, "fail", {"message": friendly_error(exc, path), "image": grab_screenshot()})
        exit_code = 1
    _put(queue, "finished", exit_code)
    return exit_code
