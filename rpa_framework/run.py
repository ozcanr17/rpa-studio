import argparse
import os
import sys

_COLORS = {
    "started": "\033[36m",
    "event": "\033[36m",
    "pass": "\033[32m",
    "fail": "\033[31m",
    "finished": "\033[34m",
    "info": "\033[90m",
}
_RESET = "\033[0m"


class Console:
    __slots__ = ("_color", "_verbose")

    def __init__(self, color, verbose):
        self._color = color
        self._verbose = verbose

    def _line(self, kind, text):
        prefix = _COLORS.get(kind, "") if self._color else ""
        suffix = _RESET if self._color and prefix else ""
        sys.stdout.write("{}{}{}\n".format(prefix, text, suffix))
        sys.stdout.flush()

    def info(self, text):
        self._line("info", text)

    def sink(self, kind, data):
        if kind == "started":
            self._line("started", "[run] {}".format(data))
        elif kind == "event":
            if self._verbose:
                self._line("event", "[event] {}: {}".format(data.get("name"), data.get("payload")))
        elif kind == "pass":
            self._line("pass", "[PASS] {}".format(data) if data else "[PASS]")
        elif kind == "fail":
            message = data.get("message") if isinstance(data, dict) else data
            self._line("fail", "[FAIL] {}".format(message))
            image = data.get("image") if isinstance(data, dict) else None
            if image:
                self._line("fail", "       screenshot: {}".format(image))
        elif kind == "finished":
            tag = "pass" if data == 0 else "fail"
            self._line(tag, "[done] exit code {}".format(data))


def _list_commands():
    from .scripting import build_scope
    handle, tmp = _dummy_script()
    try:
        scope = build_scope(tmp)
    finally:
        os.remove(tmp)
    names = sorted(k for k in scope if not k.startswith("__"))
    return names


def _dummy_script():
    import tempfile
    handle, tmp = tempfile.mkstemp(suffix=".py")
    os.close(handle)
    return handle, tmp


def _parse_args(argv):
    parser = argparse.ArgumentParser(prog="rpa-run", add_help=True, description="Run RPA / SikuliX automation scripts headlessly.")
    parser.add_argument("scripts", nargs="*", help=".sikuli folder, .py file, or a directory")
    parser.add_argument("-r", "--run", action="append", default=[], metavar="SCRIPT", help="script to run (SikuliX compatible flag; repeatable)")
    parser.add_argument("-c", "--continue-on-error", action="store_true", help="keep running the remaining scripts if one fails")
    parser.add_argument("-v", "--verbose", action="store_true", help="print event messages as well")
    parser.add_argument("--no-color", action="store_true", help="disable colored output")
    parser.add_argument("--list", action="store_true", help="list every command available inside scripts and exit")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else list(argv))
    use_color = not args.no_color and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    console = Console(use_color, args.verbose)

    if args.version:
        from . import __version__
        console.info("rpa-run {}".format(__version__))
        return 0
    if args.list:
        for name in _list_commands():
            sys.stdout.write(name + "\n")
        return 0

    targets = list(args.run) + list(args.scripts)
    if not targets:
        console.info("no script given. Usage: rpa-run test.sikuli")
        return 2

    from .scripting import run_path

    worst = 0
    for target in targets:
        if not os.path.exists(target):
            console.sink("fail", {"message": "path not found: {}".format(target)})
            worst = 1
            if not args.continue_on_error:
                return worst
            continue
        try:
            code = run_path(target, sink=console.sink)
        except KeyboardInterrupt:
            console.info("interrupted")
            return 130
        worst = worst or code
        if code != 0 and not args.continue_on_error:
            return code
    return worst


if __name__ == "__main__":
    sys.exit(main())
