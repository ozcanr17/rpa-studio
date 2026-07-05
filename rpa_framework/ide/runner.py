import asyncio
import os
import sys
import tempfile
import time
import traceback

from .directives import strip_directives


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


def _grab_screenshot():
    try:
        import cv2
        from rpa_framework.compat.sikuli import _screen
        frame = _screen().backend.capture(None)
        handle, image = tempfile.mkstemp(suffix=".png")
        os.close(handle)
        cv2.imwrite(image, frame)
        return image
    except Exception:
        return None


def _script_line(exc, path):
    line = None
    trace = exc.__traceback__
    while trace is not None:
        if trace.tb_frame.f_code.co_filename == path:
            line = trace.tb_lineno
        trace = trace.tb_next
    return line


def _friendly(exc, path):
    name = type(exc).__name__
    text = str(exc)
    line = _script_line(exc, path)
    where = " (script line {})".format(line) if line else ""
    if name == "FindFailed" or name == "ElementNotFoundError":
        if "image not found" in text:
            hint = "The image file is missing. Save the capture next to your script, or check the file name."
        elif "not found on screen" in text:
            hint = "The target is not visible right now. Bring the window to the front, lower .similar(), or use wait/exists with a longer timeout."
        elif "window not found" in text:
            hint = "No window with that title or process exists. Check the name or start the application first."
        else:
            hint = "The element could not be located. Verify the locator with Element Spy."
        return "{}: {}{}. {}".format(name, text, where, hint)
    if name == "VisionError":
        return "VisionError: {}{}. The picture could not be matched; recapture it at the current resolution and theme, or lower the similarity.".format(text, where)
    if name == "OCRError":
        return "OCRError: {}{}. Text reading failed; check Settings.OcrLanguage and that the area really contains text.".format(text, where)
    if name == "BackendError":
        return "BackendError: {}{}. A required system component is unavailable on this machine.".format(text, where)
    if name in ("TypeError", "ValueError", "AttributeError", "NameError", "KeyError", "IndexError"):
        return "{}: {}{}. This is a Python coding mistake in the script; the full traceback is above.".format(name, text, where)
    return "{}: {}{}".format(name, text, where)


def _ensure_root():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.insert(0, root)


def _build_scope(path, queue, pause_event):
    from rpa_framework import core
    from rpa_framework.compat.sikuli import build_scope as sikuli_scope, use_pause_event
    from rpa_framework.packaging.runtime_paths import configured_ocr

    use_pause_event(pause_event)

    def emit(name, payload=None):
        _put(queue, "event", {"name": name, "payload": payload})

    def passed(message=""):
        _put(queue, "pass", str(message))

    def failed(message=""):
        _put(queue, "fail", {"message": str(message), "image": _grab_screenshot()})

    def wait_if_paused(poll=0.05):
        while pause_event.is_set():
            time.sleep(poll)

    async def checkpoint(poll=0.05):
        while pause_event.is_set():
            await asyncio.sleep(poll)

    scope = {"__name__": "__main__", "__file__": path}
    for name in core.__all__:
        scope[name] = getattr(core, name)
    scope.update(sikuli_scope(os.path.dirname(os.path.abspath(path))))
    scope["configured_ocr"] = configured_ocr
    scope["emit"] = emit
    scope["passed"] = passed
    scope["failed"] = failed
    scope["fail"] = failed
    scope["wait_if_paused"] = wait_if_paused
    scope["checkpoint"] = checkpoint
    return scope


async def _execute(path, queue, pause_event):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        source = handle.read()
    code = compile(strip_directives(source), path, "exec")
    scope = _build_scope(path, queue, pause_event)
    exec(code, scope)
    entry = scope.get("main")
    if asyncio.iscoroutinefunction(entry):
        await entry()


def run_script(path, queue, pause_event):
    _ensure_root()
    sys.stdout = QueueStream(queue, "stdout")
    sys.stderr = QueueStream(queue, "stderr")
    _put(queue, "started", path)
    exit_code = 0
    try:
        asyncio.run(_execute(path, queue, pause_event))
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
    except Exception as exc:
        _put(queue, "stderr", traceback.format_exc())
        _put(queue, "fail", {"message": _friendly(exc, path), "image": _grab_screenshot()})
        exit_code = 1
    _put(queue, "finished", exit_code)
    return exit_code
