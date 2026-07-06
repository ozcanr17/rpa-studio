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
