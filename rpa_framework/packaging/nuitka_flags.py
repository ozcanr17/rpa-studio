import os

APP_NAME = "RPAStudio"
RUNNER_NAME = "rpa-run"
OUTPUT_DIR = "dist"
BASE_FLAGS = ("--standalone", "--assume-yes-for-downloads")
ONEFILE_FLAG = "--onefile"
ONEFILE_TEMP_SPEC = "{CACHE_DIR}/RPAStudio"
QT_BINDINGS = (("PyQt6", "pyqt6"), ("PySide6", "pyside6"))
QT_MODULES = ("QtCore", "QtGui", "QtWidgets")
INCLUDE_PACKAGES = ("rpa_framework",)
OPTIONAL_PACKAGES = ("comtypes", "pywinauto", "mss", "pytesseract", "onnxruntime")
PACKAGE_DATA = ("onnxruntime",)
NATIVE_LIB_PACKAGES = (("onnxruntime", "capi"),)
OPTIONAL_PLUGINS = (("gi", "gi"),)
LINUX_QT_ANCHORS = ("libQt6XcbQpa.so", "libQt6Core.so")
LINUX_GI_SO = ("libatspi.so.0",)
LINUX_EXTRA_SO = (
    "libxcb-cursor.so.0",
    "libxkbcommon.so.0",
    "libxkbcommon-x11.so.0",
    "libxcb-icccm.so.4",
    "libxcb-image.so.0",
    "libxcb-keysyms.so.1",
    "libxcb-render-util.so.0",
    "libxcb-shape.so.0",
    "libxcb-xkb.so.1",
    "libxcb-randr.so.0",
    "libxcb-render.so.0",
    "libxcb-shm.so.0",
    "libxcb-sync.so.1",
    "libxcb-xfixes.so.0",
)
LINUX_LIB_SKIP = (
    "ld-linux", "linux-vdso", "libc.so", "libm.so", "libdl.so", "libpthread.so",
    "librt.so", "libutil.so", "libresolv.so", "libnsl.so", "libanl.so",
    "libgcc_s.so", "libstdc++.so",
    "libGL.so", "libGLX", "libGLdispatch", "libEGL", "libOpenGL",
    "libdrm", "libgbm", "libvulkan", "libcuda", "libnvidia", "libwayland-",
)
LINUX_LIB_DIRS = (
    "/usr/lib64", "/usr/lib/x86_64-linux-gnu", "/usr/lib/aarch64-linux-gnu",
    "/usr/lib", "/lib64", "/lib",
)
VENDOR_DATA = (("tessdata", "tessdata"), ("tesseract", "tesseract"), ("icons", "icons"), ("models", "models"))
VENDOR_FILES = (("logo2.png", "logo2.png"),)
DOC_FILES = ("TUTORIAL.md", "KILAVUZ.md", "LINUX.md")
EXAMPLES_DIR = "examples"
WINDOWS_NO_CONSOLE = "--windows-console-mode=disable"
APP_ICON = ("vendor", "app_icon.ico")


def output_filename():
    return APP_NAME + (".exe" if os.name == "nt" else ".bin")


def runner_filename():
    return RUNNER_NAME + (".exe" if os.name == "nt" else ".bin")
