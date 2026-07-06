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
    raise SystemExit("install PyQt6 or PySide6 before building the GUI (or use --headless)")


def _data_flags(root):
    flags = []
    for source, target in nuitka_flags.VENDOR_DATA:
        path = os.path.join(root, "vendor", source)
        if os.path.isdir(path):
            flags.append("--include-raw-dir={}={}".format(path, target))
    for source, target in nuitka_flags.VENDOR_FILES:
        path = os.path.join(root, "vendor", source)
        if os.path.isfile(path):
            flags.append("--include-data-files={}={}".format(path, target))
    for name in nuitka_flags.DOC_FILES:
        path = os.path.join(root, "rpa_framework", name)
        if os.path.isfile(path):
            flags.append("--include-data-files={}={}".format(path, name))
    samples = os.path.join(root, "rpa_framework", nuitka_flags.EXAMPLES_DIR)
    if os.path.isdir(samples):
        flags.append("--include-raw-dir={}={}".format(samples, nuitka_flags.EXAMPLES_DIR))
    return flags


def build_command(onefile=False, console=False, headless=False):
    root = bundle_root()
    cmd = [sys.executable, "-m", "nuitka"]
    cmd.extend(nuitka_flags.BASE_FLAGS)
    if onefile:
        cmd.append(nuitka_flags.ONEFILE_FLAG)
        if os.name != "nt":
            cmd.append("--onefile-tempdir-spec=" + nuitka_flags.ONEFILE_TEMP_SPEC)
    if headless:
        cmd.append("--include-package=rpa_framework")
        for excluded in ("rpa_framework.ide", "PyQt6", "PySide6"):
            cmd.append("--nofollow-import-to=" + excluded)
    else:
        module, plugin = detect_qt()
        cmd.append("--enable-plugin=" + plugin)
        for package in nuitka_flags.INCLUDE_PACKAGES:
            cmd.append("--include-package=" + package)
        for name in nuitka_flags.QT_MODULES:
            cmd.append("--include-module={}.{}".format(module, name))
    for package in nuitka_flags.OPTIONAL_PACKAGES:
        if importlib.util.find_spec(package) is not None:
            cmd.append("--include-package=" + package)
            if package in nuitka_flags.PACKAGE_DATA:
                cmd.append("--include-package-data=" + package)
    cmd.extend(_data_flags(root))
    if os.name == "nt" and not console and not headless:
        cmd.append(nuitka_flags.WINDOWS_NO_CONSOLE)
    icon = os.path.join(root, *nuitka_flags.APP_ICON)
    if os.name == "nt" and os.path.isfile(icon) and not headless:
        cmd.append("--windows-icon-from-ico=" + icon)
    cmd.append("--output-dir=" + os.path.join(root, nuitka_flags.OUTPUT_DIR))
    if headless:
        cmd.append("--output-filename=" + nuitka_flags.runner_filename())
        cmd.append(os.path.join(root, "rpa_framework", "runner_app.py"))
    else:
        cmd.append("--output-filename=" + nuitka_flags.output_filename())
        cmd.append(os.path.join(root, "rpa_framework", "ide", "app.py"))
    return cmd


def dist_dir(headless=False):
    name = "runner_app" if headless else "app"
    return os.path.join(bundle_root(), nuitka_flags.OUTPUT_DIR, name + ".dist")


def _is_shared_lib(name):
    lowered = name.lower()
    return lowered.endswith((".dll", ".dylib", ".pyd")) or ".so" in lowered


def copy_native_libs(target_root):
    import shutil
    for package, subdir in nuitka_flags.NATIVE_LIB_PACKAGES:
        spec = importlib.util.find_spec(package)
        locations = list(spec.submodule_search_locations or []) if spec else []
        if not locations:
            continue
        source = os.path.join(locations[0], subdir)
        if not os.path.isdir(source):
            continue
        target = os.path.join(target_root, package, subdir)
        os.makedirs(target, exist_ok=True)
        for name in os.listdir(source):
            destination = os.path.join(target, name)
            if not _is_shared_lib(name) or os.path.exists(destination):
                continue
            try:
                shutil.copy2(os.path.join(source, name), destination)
            except Exception:
                pass


def _run_lines(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()
    except Exception:
        return []


def _shared_entries(lines):
    entries = {}
    for line in lines:
        if "=>" not in line:
            continue
        name, _sep, rest = line.partition("=>")
        name = name.strip().split(" (")[0].strip()
        target = rest.strip().split(" (")[0].strip()
        if name and target and target != "not found" and target.startswith("/"):
            entries[name] = target
    return entries


def _lib_skipped(name):
    lowered = name.lower()
    return any(lowered.startswith(skip.lower()) for skip in nuitka_flags.LINUX_LIB_SKIP)


def _qt_wheel_lib_dirs():
    folders = []
    for module, _plugin in nuitka_flags.QT_BINDINGS:
        spec = importlib.util.find_spec(module)
        locations = list(spec.submodule_search_locations or []) if spec else []
        for base in locations:
            for sub in ("Qt6", "Qt"):
                path = os.path.join(base, sub, "lib")
                if os.path.isdir(path):
                    folders.append(path)
    return folders


def _dist_lib_dir(target_root):
    for base, _dirs, files in os.walk(target_root):
        for name in files:
            if name.startswith(nuitka_flags.LINUX_QT_ANCHORS):
                return base
    return None


def _system_lib(name, folders, cache):
    for folder in folders:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return cache.get(name)


def _external_deps(path, root_real):
    found = {}
    for name, target in _shared_entries(_run_lines(["ldd", path])).items():
        try:
            resolved = os.path.realpath(target)
        except Exception:
            continue
        if not resolved.startswith(root_real + os.sep):
            found[name] = target
    return found


def bundle_linux_libs(target_root):
    if os.name == "nt":
        return
    import shutil
    root_real = os.path.realpath(target_root)
    qt_lib_dir = _dist_lib_dir(target_root)
    lib_dir = qt_lib_dir or target_root
    present = set()
    binaries = []
    for base, _dirs, files in os.walk(target_root):
        for name in files:
            present.add(name)
            if ".so" in name or name.endswith(".bin"):
                binaries.append(os.path.join(base, name))
    folders = _qt_wheel_lib_dirs() + list(nuitka_flags.LINUX_LIB_DIRS)
    cache = _shared_entries(_run_lines(["ldconfig", "-p"]))
    queue = []
    if qt_lib_dir is not None:
        for name in nuitka_flags.LINUX_EXTRA_SO:
            path = _system_lib(name, folders, cache)
            if path is not None:
                queue.append((name, path))
            elif name not in present:
                print("linux-libs: MISSING on build machine: " + name)
    for path in binaries:
        queue.extend(_external_deps(path, root_real).items())
    copied = []
    while queue:
        name, path = queue.pop()
        if name in present or _lib_skipped(name):
            continue
        destination = os.path.join(lib_dir, name)
        try:
            shutil.copy2(os.path.realpath(path), destination)
        except Exception:
            continue
        present.add(name)
        copied.append(name)
        queue.extend(_external_deps(destination, root_real).items())
    print("linux-libs: bundled {} into {}".format(len(copied), lib_dir))
    for name in sorted(copied):
        print("linux-libs:   + " + name)


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
    onefile = "--onefile" in args
    console = "--console" in args
    headless = "--headless" in args
    if "--dry-run" in args:
        print(subprocess.list2cmdline(build_command(onefile, console, headless)))
        return 0
    if not headless:
        pregenerate_com_bindings()
        build_app_icon()
    cmd = build_command(onefile, console, headless)
    print(subprocess.list2cmdline(cmd))
    status = subprocess.call(cmd, cwd=bundle_root())
    if status == 0 and not onefile:
        copy_native_libs(dist_dir(headless))
        bundle_linux_libs(dist_dir(headless))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
