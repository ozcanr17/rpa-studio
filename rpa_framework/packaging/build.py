import importlib.util
import os
import subprocess
import sys

from . import nuitka_flags
from .runtime_paths import bundle_root


def detect_qt():
    for module, plugin in nuitka_flags.QT_BINDINGS:
        if importlib.util.find_spec(module) is not None:
            return module, plugin
    raise SystemExit("install PyQt6 or PySide6 before building")


def build_command(onefile=True, console=False):
    root = bundle_root()
    module, plugin = detect_qt()
    cmd = [sys.executable, "-m", "nuitka"]
    cmd.extend(nuitka_flags.BASE_FLAGS)
    if onefile:
        cmd.append(nuitka_flags.ONEFILE_FLAG)
    cmd.append("--enable-plugin=" + plugin)
    for package in nuitka_flags.INCLUDE_PACKAGES:
        cmd.append("--include-package=" + package)
    for package in nuitka_flags.OPTIONAL_PACKAGES:
        if importlib.util.find_spec(package) is not None:
            cmd.append("--include-package=" + package)
    for name in nuitka_flags.QT_MODULES:
        cmd.append("--include-module={}.{}".format(module, name))
    for source, target in nuitka_flags.VENDOR_DATA:
        path = os.path.join(root, "vendor", source)
        if os.path.isdir(path):
            cmd.append("--include-raw-dir={}={}".format(path, target))
    for source, target in nuitka_flags.VENDOR_FILES:
        path = os.path.join(root, "vendor", source)
        if os.path.isfile(path):
            cmd.append("--include-data-files={}={}".format(path, target))
    for name in nuitka_flags.DOC_FILES:
        path = os.path.join(root, "rpa_framework", name)
        if os.path.isfile(path):
            cmd.append("--include-data-files={}={}".format(path, name))
    samples = os.path.join(root, "rpa_framework", nuitka_flags.EXAMPLES_DIR)
    if os.path.isdir(samples):
        cmd.append("--include-raw-dir={}={}".format(samples, nuitka_flags.EXAMPLES_DIR))
    if os.name == "nt" and not console:
        cmd.append(nuitka_flags.WINDOWS_NO_CONSOLE)
    icon = os.path.join(root, *nuitka_flags.APP_ICON)
    if os.name == "nt" and os.path.isfile(icon):
        cmd.append("--windows-icon-from-ico=" + icon)
    cmd.append("--output-dir=" + os.path.join(root, nuitka_flags.OUTPUT_DIR))
    cmd.append("--output-filename=" + nuitka_flags.output_filename())
    cmd.append(os.path.join(root, "rpa_framework", "ide", "app.py"))
    return cmd


def pregenerate_com_bindings():
    if os.name != "nt":
        return
    snippet = "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"
    try:
        subprocess.call([sys.executable, "-c", snippet])
    except Exception:
        pass


def build_app_icon():
    root = bundle_root()
    target = os.path.join(root, *nuitka_flags.APP_ICON)
    png = target[:-4] + ".png"
    snippet = (
        "import os, sys\n"
        "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
        "sys.path.insert(0, {root!r})\n"
        "from rpa_framework.ide.qt_shim import load_qt\n"
        "qt = load_qt()\n"
        "app = qt.QtWidgets.QApplication([])\n"
        "from rpa_framework.ide.theme import logo_pixmap\n"
        "logo_pixmap(qt, 256).save({png!r})\n"
        "from PIL import Image\n"
        "Image.open({png!r}).save({target!r}, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])\n"
    ).format(root=root, png=png, target=target)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        subprocess.call([sys.executable, "-c", snippet])
    except Exception:
        pass


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    onefile = "--no-onefile" not in args
    console = "--console" in args
    if "--dry-run" in args:
        print(subprocess.list2cmdline(build_command(onefile, console)))
        return 0
    pregenerate_com_bindings()
    build_app_icon()
    cmd = build_command(onefile, console)
    print(subprocess.list2cmdline(cmd))
    return subprocess.call(cmd, cwd=bundle_root())


if __name__ == "__main__":
    raise SystemExit(main())
