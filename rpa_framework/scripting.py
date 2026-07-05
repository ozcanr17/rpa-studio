import asyncio
import os
import sys
import tempfile
import threading
import time

from .directives import strip_directives

SIKULI_SUFFIX = ".sikuli"


def _noop_sink(kind, data):
    return None


def resolve_script(path):
    target = os.path.abspath(path)
    if os.path.isdir(target):
        return _resolve_dir(target)
    if os.path.isfile(target):
        return target, os.path.dirname(target)
    raise IOError("script path not found: {}".format(path))


def _resolve_dir(folder):
    base = os.path.basename(folder.rstrip("/\\"))
    if base.endswith(SIKULI_SUFFIX):
        stem = base[: -len(SIKULI_SUFFIX)]
        candidate = os.path.join(folder, stem + ".py")
        if os.path.isfile(candidate):
            return candidate, folder
    for name in ("main.py", "__main__.py"):
        candidate = os.path.join(folder, name)
        if os.path.isfile(candidate):
            return candidate, folder
    scripts = sorted(n for n in os.listdir(folder) if n.endswith(".py"))
    if len(scripts) == 1:
        return os.path.join(folder, scripts[0]), folder
    if not scripts:
        raise IOError("no .py script found in {}".format(folder))
    raise IOError("multiple scripts in {}; specify one of {}".format(folder, scripts))


def grab_screenshot():
    try:
        import cv2
        from .compat.sikuli import _screen
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


def friendly_error(exc, path):
    name = type(exc).__name__
    text = str(exc)
    line = _script_line(exc, path)
    where = " (script line {})".format(line) if line else ""
    if name in ("FindFailed", "ElementNotFoundError"):
        if "image not found" in text:
            hint = "The image file is missing. Put the capture next to your script, or check the file name."
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


def build_scope(path, sink=None, pause_event=None):
    from . import core
    from .compat.sikuli import build_scope as sikuli_scope, use_pause_event
    from .packaging.runtime_paths import configured_ocr

    emit = sink or _noop_sink
    if pause_event is not None:
        use_pause_event(pause_event)

    def notify(name, payload=None):
        emit("event", {"name": name, "payload": payload})

    def passed(message=""):
        emit("pass", str(message))

    def failed(message=""):
        emit("fail", {"message": str(message), "image": grab_screenshot()})

    def wait_if_paused(poll=0.05):
        while pause_event is not None and pause_event.is_set():
            time.sleep(poll)

    async def checkpoint(poll=0.05):
        while pause_event is not None and pause_event.is_set():
            await asyncio.sleep(poll)

    scope = {"__name__": "__main__", "__file__": path}
    for name in core.__all__:
        scope[name] = getattr(core, name)
    scope.update(sikuli_scope(os.path.dirname(os.path.abspath(path))))
    scope["configured_ocr"] = configured_ocr
    scope["emit"] = notify
    scope["passed"] = passed
    scope["failed"] = failed
    scope["fail"] = failed
    scope["wait_if_paused"] = wait_if_paused
    scope["checkpoint"] = checkpoint
    return scope


async def _execute(code, scope):
    exec(code, scope)
    entry = scope.get("main")
    if asyncio.iscoroutinefunction(entry):
        await entry()


def run_compiled(code, scope):
    asyncio.run(_execute(code, scope))


def run_path(path, sink=None, pause_event=None, argv=None):
    script_path, bundle = resolve_script(path)
    if pause_event is None:
        pause_event = threading.Event()
    with open(script_path, "r", encoding="utf-8", errors="replace") as handle:
        source = handle.read()
    code = compile(strip_directives(source), script_path, "exec")
    scope = build_scope(script_path, sink, pause_event)
    saved_argv = list(sys.argv)
    sys.argv = [script_path] + list(argv or [])
    if sink:
        sink("started", script_path)
    exit_code = 0
    try:
        run_compiled(code, scope)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 0 if exc.code is None else 1
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        import traceback
        sys.stdout.flush()
        sys.stderr.write(traceback.format_exc())
        if sink:
            sink("fail", {"message": friendly_error(exc, script_path), "image": grab_screenshot()})
        exit_code = 1
    finally:
        sys.argv = saved_argv
    if sink:
        sink("finished", exit_code)
    return exit_code
