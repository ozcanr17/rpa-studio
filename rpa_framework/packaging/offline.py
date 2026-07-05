import os
import subprocess
import sys

from .runtime_paths import bundle_root

DEFAULT_DIR = "wheelhouse"


def _requirements(gui):
    root = bundle_root()
    names = ["requirements-linux.txt"] if not gui else ["requirements-linux.txt", "requirements-gui.txt"]
    found = []
    for name in names:
        path = os.path.join(root, "rpa_framework", name)
        if not os.path.isfile(path):
            path = os.path.join(root, name)
        if os.path.isfile(path):
            found.append(path)
    return found


def download(dest=None, gui=False, extra=None):
    dest = dest or os.path.join(bundle_root(), DEFAULT_DIR)
    os.makedirs(dest, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "download", "-d", dest]
    for req in _requirements(gui):
        cmd.extend(["-r", req])
    if extra:
        cmd.extend(extra)
    print(subprocess.list2cmdline(cmd))
    return subprocess.call(cmd)


def install(source=None, gui=False, target=None):
    source = source or os.path.join(bundle_root(), DEFAULT_DIR)
    cmd = [sys.executable, "-m", "pip", "install", "--no-index", "--find-links", source]
    if target:
        cmd.extend(["--target", target])
    for req in _requirements(gui):
        cmd.extend(["-r", req])
    print(subprocess.list2cmdline(cmd))
    return subprocess.call(cmd)


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    gui = "--gui" in args
    rest = [a for a in args if a != "--gui"]
    action = rest[0] if rest else "help"
    where = rest[1] if len(rest) > 1 else None
    if action == "download":
        return download(where, gui)
    if action == "install":
        return install(where, gui)
    print("usage: python -m rpa_framework.packaging.offline [download|install] [dir] [--gui]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
