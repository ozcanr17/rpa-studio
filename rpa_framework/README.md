# RPA Framework

Cross-platform desktop automation that combines native accessibility trees
(Windows UI Automation, Linux AT-SPI) with computer vision (SIFT / ORB + FLANN)
and OCR (Tesseract). Designed to compile to a single zero-install executable.

All four phases are implemented: OS facade and vision, accessibility
inspector and spy daemon, desktop IDE with async execution engine, and Nuitka
standalone packaging. A SikuliX-compatible scripting API lets existing
SikuliX Python scripts run in the IDE. New here? Read TUTORIAL.md first.
See CLAUDE.md for the architecture and the code constraints.

## Quick start
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m rpa_framework.core.inspector 0.3
python -m rpa_framework.ide
python -m rpa_framework.packaging.build

Linux additionally needs the system packages: xdotool, at-spi2-core,
python3-gi, and tesseract-ocr, with accessibility enabled in the session.
Windows needs only the pip packages (UI Automation is built into the OS) plus a
reachable Tesseract binary.

## Public API
from rpa_framework.core import (
    OSFacadeFactory, FeatureMatcher, OCREngine, load_image,
    InspectorFactory, InspectorDaemon, UIElement, Rect,
)
