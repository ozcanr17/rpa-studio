import multiprocessing
import queue

from .runner import run_script


class ExecutionEngine:
    __slots__ = ("_context", "_process", "_queue", "_pause")

    def __init__(self):
        self._context = multiprocessing.get_context("spawn")
        self._process = None
        self._queue = None
        self._pause = None

    @property
    def running(self):
        return self._process is not None and self._process.is_alive()

    @property
    def paused(self):
        return self._pause is not None and self._pause.is_set()

    def start(self, script_path):
        if self.running:
            return False
        self._queue = self._context.Queue()
        self._pause = self._context.Event()
        self._process = self._context.Process(target=run_script, args=(script_path, self._queue, self._pause), daemon=True)
        try:
            self._process.start()
        except Exception:
            self._process = None
            return False
        return True

    def stop(self):
        process = self._process
        if process is None:
            return False
        try:
            if process.is_alive():
                process.terminate()
                process.join(timeout=2.0)
        except Exception:
            pass
        return True

    def pause(self):
        if self._pause is not None:
            self._pause.set()

    def resume(self):
        if self._pause is not None:
            self._pause.clear()

    def poll(self, limit=200):
        events = []
        if self._queue is None:
            return events
        for _ in range(limit):
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
            except Exception:
                break
        if not events and self._process is not None and not self._process.is_alive():
            while True:
                try:
                    events.append(self._queue.get(timeout=0.05))
                except Exception:
                    break
            code = self._process.exitcode
            self._process = None
            self._pause = None
            self._queue = None
            events.append({"type": "exit", "data": code})
        return events
