import os

from ..core.os_facade.base import frozen_build


def is_compiled():
    return frozen_build()


def bundle_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(*parts):
    return os.path.join(bundle_root(), *parts)


def _resource_or_vendor(name, checker):
    for candidate in (resource_path(name), os.path.join(bundle_root(), "vendor", name)):
        if checker(candidate):
            return candidate
    return None


def tesseract_cmd():
    name = "tesseract.exe" if os.name == "nt" else "tesseract"
    folder = _resource_or_vendor("tesseract", os.path.isdir)
    path = os.path.join(folder, name) if folder else None
    return path if path and os.path.isfile(path) else None


def tessdata_dir():
    return _resource_or_vendor("tessdata", os.path.isdir)


def logo_path():
    return _resource_or_vendor("logo2.png", os.path.isfile)


def configured_ocr(**kwargs):
    from ..core.vision.ocr_engine import OCREngine
    kwargs.setdefault("tesseract_cmd", tesseract_cmd())
    kwargs.setdefault("tessdata_dir", tessdata_dir())
    return OCREngine(**kwargs)


def _bundled_or_source(name, checker):
    bundled = resource_path(name)
    if checker(bundled):
        return bundled
    source = os.path.join(bundle_root(), "rpa_framework", name)
    return source if checker(source) else None


def docs_path(name):
    return _bundled_or_source(name, os.path.isfile)


def examples_dir():
    return _bundled_or_source("examples", os.path.isdir)
