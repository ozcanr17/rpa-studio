# RPA Framework - Build Handoff (Claude Code)

Commercial-grade, cross-platform RPA framework. Reliability comes from a
layered strategy: native accessibility trees are the primary interaction path,
with AI vision (offline ONNX UI detection), computer vision, and OCR as the
visual fallbacks. The final artifact is a zero-install standalone portable
FOLDER built with Nuitka (onefile was dropped; --onefile remains as a legacy
opt-in). The folder must run fully offline on a fresh air-gapped Windows or
Linux machine: framework, onnxruntime, model weights, Tesseract, and every
OS shared library (.dll/.so) ship inside it.

## NON-NEGOTIABLE CODE CONSTRAINTS
These apply to every Python file you add or edit. Violations are rejected.
1. No comments. No docstrings. No inline explanations of any kind.
2. No type hints or annotations anywhere.
3. ASCII only. Every character in every file (code, string literals,
   identifiers, filenames) must be within the 7-bit ASCII range. No accented,
   non-Latin, or smart-punctuation characters anywhere.
4. Extreme DRY. Share helpers; do not copy-paste. Reuse
   core.os_facade.base.Rect and the existing factory + registry patterns.
5. Match the established style: 4-space indentation, __slots__ on data classes,
   thin backend classes, and a broad try/except around every native
   OS / COM / AT-SPI call so failures degrade gracefully.

## STATUS
- Phase 1 COMPLETE: OS facade (Linux xdotool, Windows win32 + pywinauto) plus
  vision (SIFT / ORB + FLANN, no matchTemplate) plus OCR (pytesseract, custom
  .traineddata through tessdata-dir).
- Phase 2 COMPLETE: cross-platform accessibility inspector and spy daemon
  (Linux AT-SPI through gi.repository.Atspi, Windows UIA through comtypes).
  Extracts role, name, AutomationId, class, bounding box, states, and pid, and
  serializes to JSON.
- Phase 3 COMPLETE: PyQt6 / PySide6 IDE (single qt_shim compatibility layer,
  editor with inline IMAGE directive rendering, syntax highlighter) plus async
  execution engine (spawn multiprocessing child, asyncio entry point, queue
  bridged to the GUI through a QTimer, cooperative pause through an Event).
- Phase 4 COMPLETE: Nuitka standalone plus onefile packaging (build.py with
  Qt plugin autodetection, runtime_paths.py bundle-root and OCR path helpers,
  conditional vendor/tessdata and vendor/tesseract data bundling).
- EXTRA COMPLETE: compat/sikuli.py, a SikuliX-compatible scripting API
  (find/click/type/wait/Pattern/Region/Key and friends) injected into every
  script by ide/runner.py, so existing SikuliX .py scripts run in the IDE.
  Docs: TUTORIAL.md (user guide), examples/ (runnable samples).
- AI VISION COMPLETE: core/vision/ui_detector.py (UIDetector + Detection,
  lazy onnxruntime, YOLO v5/v8 output parsing, letterbox + NMS, labels from
  model metadata / <model>.labels / DEFAULT_LABELS). find_ui/find_ui_regions
  take an optional detector and fall back to the contour heuristic;
  sikuli.findUI wires runtime_paths.configured_detector (cached, returns None
  when no model), and Target gained a fourth "ui" anchor that only activates
  when a model is bundled (and, for single-class models, only with text= -
  role alone cannot discriminate). Model files live in vendor/models/*.onnx;
  a <model>.json sidecar overrides min_score/iou defaults. BUNDLED MODEL:
  OmniParser icon-detect (ui_detect.onnx, 12 MB, single class "element",
  AGPL-3.0 weights - license note in BUILDING.md); single-class models bypass
  the kind filter. Element Spy insert trigger is F8 or Insert
  (panels.insert_pressed: GetAsyncKeyState on Windows, Xlib query_keymap on
  Linux - right_pressed is gone).
- PACKAGING NOW FOLDER-FIRST: build.py defaults to --standalone (no onefile);
  copy_native_libs() post-copies onnxruntime/capi shared libs Nuitka misses;
  scripts stage dist/rpa-studio-windows(+.zip), dist/rpa-run-windows,
  dist/rpa-studio-linux(+.tar.gz), dist/rpa-run-linux(+.tar.gz).
- LINUX SELF-CONTAINMENT: bundle_linux_libs() in build.py runs after every
  Linux folder build - copies the dlopen'ed Qt 6.5+ xcb family
  (libxcb-cursor.so.0 etc., LINUX_EXTRA_SO) plus every externally resolved
  .so found by a recursive ldd fixpoint into the Qt lib dir, excluding glibc
  and GPU drivers (LINUX_LIB_SKIP - never bundle those). build_linux.sh
  writes run.sh (LD_LIBRARY_PATH export + wayland fallback - the documented
  launcher) and diagnose.sh (target-side missing-lib report) into the stage.

## LAYOUT
rpa_framework/
  requirements.txt
  README.md
  CLAUDE.md
  core/
    __init__.py            public API surface
    exceptions.py          RPAError hierarchy
    os_facade/             input, screen capture, window control
      base.py              OSBackend ABC, OSFacadeFactory, Rect, WindowHandle
      linux_backend.py     xdotool + mss
      windows_backend.py   win32gui + pywinauto + mss
    vision/
      feature_matcher.py   FeatureMatcher, MatchResult, load_image
      ocr_engine.py        OCREngine, TextBox
      ui_detector.py       UIDetector, Detection (lazy onnxruntime, YOLO onnx)
      ui_finder.py         find_ui, find_ui_regions, detect_ui (AI + heuristic)
    inspector/
      base.py              AccessibilityInspector ABC, UIElement, InspectorFactory
      linux_inspector.py   AtspiInspector
      windows_inspector.py UIAInspector
      daemon.py            InspectorDaemon, run_spy
      __main__.py          python -m rpa_framework.core.inspector
  compat/
    __init__.py            build_scope re-export
    sikuli.py              SikuliX-style API: Screen, Region, Pattern, Key...
  packaging/
    __init__.py            runtime path helpers re-export
    __main__.py            python -m rpa_framework.packaging
    runtime_paths.py       bundle_root, tesseract_cmd, tessdata_dir, configured_ocr
    nuitka_flags.py        static flag data for the build
    build.py               assembles and runs the Nuitka command
  examples/                runnable sample scripts (not a package)
  ide/
    __init__.py            ExecutionEngine, load_qt, lazy main()
    __main__.py            python -m rpa_framework.ide
    qt_shim.py             load_qt (PyQt6 then PySide6), cached_builder
    directives.py          IMAGE_PATTERN, image_target, strip_directives
    highlighter.py         build_highlighter_class (PythonHighlighter)
    editor.py              build_editor_class (ScriptEditor, inline images)
    engine.py              ExecutionEngine (spawn process, queue, pause Event)
    runner.py              run_script child target, API injection
    app.py                 build_main_window_class, main() entry point

## PUBLIC API
from rpa_framework.core import (
    OSFacadeFactory, FeatureMatcher, OCREngine, load_image,
    InspectorFactory, InspectorDaemon, UIElement, Rect,
)
backend = OSFacadeFactory.create()          auto-select by platform
inspector = InspectorFactory.create()
element = inspector.element_at(x, y)
print(element.to_json())

## ARCHITECTURE RULES
- Every module imports on any OS. Native libraries load lazily inside the
  factories, never at import time. Missing libraries raise BackendError only on
  create(), which keeps CI green and Nuitka analysis deterministic. Preserve
  this invariant in Phase 3 and Phase 4.
- New OS or inspector backends register through the existing decorators
  (register_backend, register_inspector) and are lazy-imported by the factory
  _load methods. Do not import platform modules at package top level.

## SYSTEM DEPENDENCIES
Linux:  xdotool, at-spi2-core, gir1.2-atspi-2.0, python3-gi (PyGObject),
        tesseract-ocr, and an active AT-SPI bus (accessibility enabled in the
        session).
Windows: UI Automation is built into the OS. pip installs comtypes, pywin32,
        pywinauto. A Tesseract binary must be reachable through PATH or through
        OCREngine(tesseract_cmd=...).
Both:   Python 3.10 or newer.

## SETUP
python -m venv .venv
. .venv/bin/activate           Windows: .venv\Scripts\activate
pip install -r requirements.txt

## RUN THE SPY DAEMON
The parent directory of rpa_framework must be on sys.path, so run from the
directory that contains the rpa_framework folder:
python -m rpa_framework.core.inspector 0.3
Move the cursor. The element under it prints as JSON whenever it changes.

## RUN THE IDE
python -m rpa_framework.ide
Open a .py automation script, press F5 to run, F6 to pause or resume, Shift+F5
to stop. Lines of the form IMAGE: relative/or/absolute/path.png render the
referenced image inline beneath the line (resolved against the script's
directory). The runner strips IMAGE lines before execution, injects the public
core API plus emit(name, payload), wait_if_paused(), and await checkpoint()
into the script globals, and awaits a top-level async def main() if the script
defines one.

## PHASE 3 SPEC (implemented)
New package: rpa_framework/ide/
Deliver a PyQt6 desktop IDE, falling back to PySide6 if PyQt6 is unavailable.
Keep the Qt import behind a single compatibility shim so both bindings work.
- ide/app.py: QApplication bootstrap, main window, menu bar, and a Run / Stop
  toolbar. Wire actions to the engine.
- ide/editor.py: a QPlainTextEdit (or QTextEdit) subclass with Python syntax
  highlighting and native inline image rendering. Inline images: the script
  author writes a directive line, for example
      IMAGE: assets/login_button.png
  The editor detects such lines and paints the referenced image inline directly
  beneath that line (custom block painting in paintEvent, or a
  QTextObjectInterface), so visual targets are visible next to the code that
  uses them. The document stays plain text on disk.
- ide/highlighter.py: QSyntaxHighlighter for keywords, strings, numbers, and
  comment-style tokens.
- ide/engine.py: async execution engine. Run the user's automation script in a
  separate process (multiprocessing.Process) so a crash or infinite loop never
  freezes the UI. Bridge child stdout, stderr, and structured events back to the
  GUI thread through a multiprocessing.Queue drained by a QTimer, or a QThread
  that blocks on the queue and re-emits Qt signals. Wrap the child entry point
  in asyncio.run so scripts may await framework calls. Expose start, stop
  (terminate the process), and a cooperative pause through an Event.
- ide/runner.py: the child-process target. Sets up sys.path, injects the public
  API into the script globals, executes the target file, and streams events back
  over the queue.
- Hard rule: never block the Qt event loop. No native OS call that can hang runs
  on the GUI thread. All automation executes in the child process.
Acceptance: open a .py automation file, see inline images for IMAGE lines, press
Run, watch live output stream in, press Stop mid-run, and the UI stays
responsive throughout.

## PHASE 4 SPEC (implement last)
New package: rpa_framework/packaging/
- packaging/build.py: invoke Nuitka in standalone plus onefile mode against the
  IDE entry point (rpa_framework/ide/app.py). Enable the PyQt6 (or PySide6)
  plugin. Include OpenCV and numpy. Bundle the Tesseract binary and a tessdata
  folder as data through --include-data-dir / --include-data-files so the
  executable is zero-install.
- packaging/runtime_paths.py: a helper that returns the bundle root whether the
  process runs from source or from the onefile build (detect the compiled state
  and resolve relative to the executable). The OCR engine and any data lookup
  must go through this helper. At runtime, set OCREngine(tesseract_cmd=...) and
  tessdata_dir to the bundled paths.
- packaging/nuitka.conf (or a py file holding the flag list). Suggested flags:
  --standalone --onefile --enable-plugin=pyqt6
  --include-package=rpa_framework
  --include-data-dir=vendor/tessdata=tessdata
  --include-data-files=vendor/tesseract=tesseract
  --output-dir=dist --assume-yes-for-downloads
Acceptance: the dist output runs on a clean machine with no Python, no OpenCV,
and no Tesseract installed.

## KNOWN GAPS TO FILL
- Windows UIAInspector currently leaves value empty. Add ValuePattern and
  TextPattern extraction through GetCurrentPattern when value is needed.
- Linux hit-testing walks the tree with pruning by extents. If a toolkit
  implements Component.get_accessible_at_point reliably, prefer it for speed.
- If higher-level key APIs are added, unify cross-platform key names (Linux uses
  xdotool keysyms, Windows uses VK_ names).
- Add a stable-locator layer on top of UIElement (search by role/name/id path)
  for resilient element selection inside automation scripts.
