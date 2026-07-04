import os

APP_NAME = "RPAStudio"
OUTPUT_DIR = "dist"
BASE_FLAGS = ("--standalone", "--assume-yes-for-downloads")
ONEFILE_FLAG = "--onefile"
QT_BINDINGS = (("PyQt6", "pyqt6"), ("PySide6", "pyside6"))
QT_MODULES = ("QtCore", "QtGui", "QtWidgets")
INCLUDE_PACKAGES = ("rpa_framework",)
OPTIONAL_PACKAGES = ("comtypes", "pywinauto", "mss", "pytesseract")
VENDOR_DATA = (("tessdata", "tessdata"), ("tesseract", "tesseract"), ("icons", "icons"))
VENDOR_FILES = (("logo2.png", "logo2.png"),)
DOC_FILES = ("TUTORIAL.md", "KILAVUZ.md")
EXAMPLES_DIR = "examples"
WINDOWS_NO_CONSOLE = "--windows-console-mode=disable"
APP_ICON = ("vendor", "app_icon.ico")


def output_filename():
    return APP_NAME + (".exe" if os.name == "nt" else ".bin")
