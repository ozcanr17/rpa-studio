# RPA Framework - Project Handoff

Last updated: 2026-07-04 (session 8: window-scoped findElement, editor image
context menu, CLAHE+edge theme-proof matching, DPI scale, unified mss capture,
Target multi-anchor self-healing, raw deep tree spy, VDI findUI, autoScroll;
session 7: failed() rename, UIA value/toggle state,
rich Element actions (clear/setText/check/select/child), PyCharm editor
features, Element Spy action picker;
session 6: BitBlt capture fix, Offset class, Location
tool, variable-prompt codegen for every capture tool, Element Spy live preview;
session 5: capture/spy UX rework - instant vs delayed
capture, Space-commit overlay, variable-assignment codegen, usable Element
proxy, visible tab close buttons, Asset Tester red-rectangle; session 4: branding
+ capture suite + spy hotkey/
scraper + pass/fail console + Monokai/lint + .sikuli + asset tester).
This document is the single source of truth for picking up the project cold.
Read it top to bottom before touching code.

---

## 1. Project Overview

### Purpose
A commercial-grade, cross-platform **Robotic Process Automation (RPA)**
framework plus a desktop **IDE** (branded "RPA Studio") for writing and running
automation scripts. It drives the mouse, keyboard, and screen of a real desktop
to automate GUI workflows.

### Reliability philosophy (the core design idea)
Automation targets are located two ways, and the combination is what makes it
robust:
1. **Native accessibility trees (primary)** - ask the OS directly "what control
   is here, what is it called, where is it": Windows UI Automation (UIA via
   `comtypes`), Linux AT-SPI (via `gi.repository.Atspi`). Fast and exact.
2. **Computer vision + OCR (fallback)** - find a cropped screenshot on screen
   using feature matching (OpenCV SIFT/ORB + FLANN, deliberately *not*
   `matchTemplate`), and read on-screen text with Tesseract OCR.

### Final artifact
A single, zero-install executable produced by **Nuitka** (standalone + onefile).
It embeds the Python runtime, PyQt6, OpenCV, numpy, and all framework code. The
current build `dist/RPAStudio.exe` is ~74 MB and runs on a clean Windows machine
with nothing preinstalled (except the near-ubiquitous VC runtime).

### Technology stack
- **Language:** Python 3.10+ (tested/run on 3.13; built with 3.14).
- **GUI:** PyQt6, with a compatibility shim that also supports PySide6.
- **Vision:** opencv-contrib-python (SIFT/ORB, FLANN), numpy.
- **OCR:** pytesseract (needs a Tesseract binary; can be bundled).
- **Screen capture:** mss.
- **Windows input/windows:** pywin32 (win32gui/api/con/process), pywinauto.
- **Windows accessibility:** comtypes (UIAutomationCore).
- **Linux input:** xdotool (subprocess); **Linux accessibility:** PyGObject/AT-SPI.
- **Packaging:** Nuitka + ziglang C backend (auto-downloaded).

### Architecture rule that must never be broken
**Every module must import on any OS.** Native libraries load lazily *inside*
factory `create()` methods, never at module top level. Missing libraries raise
`BackendError` only at `create()` time. This keeps CI/tests green on any
platform and keeps Nuitka's static analysis deterministic. Backends/inspectors
register via decorators (`register_backend`, `register_inspector`) and are
lazy-imported by the factory `_load` methods.

---

## 2. Completed Work

The project was built in 4 sequential phases (all complete) plus two large
follow-on efforts (SikuliX compatibility, and a full IDE redesign that is nearly
complete). Source lives under `C:\Users\Elessar\Desktop\workspace\rpa_framework\`.

### Phase 1 - Core OS Facade + Vision (COMPLETE, pre-existing)
- `core/exceptions.py` - `RPAError` hierarchy: `BackendError`,
  `ElementNotFoundError`, `VisionError`, `OCRError`.
- `core/os_facade/base.py` - `OSBackend` ABC, `OSFacadeFactory`, `Rect`,
  `WindowHandle`, `register_backend`. `Rect` has `.center`, `.contains`,
  `.as_tuple`.
- `core/os_facade/linux_backend.py` - `LinuxBackend` (xdotool + mss).
- `core/os_facade/windows_backend.py` - `WindowsBackend` (win32 + pywinauto + mss).
- `core/vision/feature_matcher.py` - `FeatureMatcher` (SIFT/ORB + FLANN,
  ratio test, homography), `MatchResult`, `load_image`. NOTE: cv2/numpy import
  is now guarded (was fixed during Phase 3 to preserve the import-anywhere rule).
- `core/vision/ocr_engine.py` - `OCREngine` (pytesseract, Otsu preprocess,
  `--tessdata-dir` support), `TextBox`.

### Phase 2 - Native UI Inspector Daemon (COMPLETE, pre-existing)
- `core/inspector/base.py` - `AccessibilityInspector` ABC, `UIElement`
  (role/name/automation_id/class_name/value/states/bounding_box/process_id, with
  `to_dict`/`to_json`/`matches`), `InspectorFactory`, `walk`/`find`/`find_all`.
- `core/inspector/linux_inspector.py` - `AtspiInspector`.
- `core/inspector/windows_inspector.py` - `UIAInspector` (comtypes).
- `core/inspector/daemon.py` - `InspectorDaemon` (threaded cursor-follow spy,
  dedupe by element key, `on_element` callback), `run_spy`.
- `core/inspector/__main__.py` - `python -m rpa_framework.core.inspector [interval]`.

### Phase 3 - IDE + Async Execution Engine (COMPLETE, then REDESIGNED)
Original engine/editor (still in use, engine unchanged):
- `ide/qt_shim.py` - `load_qt()` (tries PyQt6 then PySide6, raises BackendError
  only on call), `QtApi` wrapper, `cached_builder` decorator (builds
  Qt-dependent classes lazily, cached per binding). **All Qt access goes
  through this shim; nothing imports PyQt6 at module top level.**
- `ide/directives.py` - `IMAGE_PATTERN`, `image_target`, `strip_directives`
  (turns `IMAGE: path.png` lines into `pass` before exec, preserving line
  numbers).
- `ide/highlighter.py` - `build_highlighter_class` (Python syntax highlighter,
  incl. triple-quoted string state machine and IMAGE directive coloring).
- `ide/engine.py` - `ExecutionEngine`: spawn-context `multiprocessing.Process`
  + `Queue` + pause `Event`. Methods `start/stop/pause/resume/poll`. `poll()`
  drains child events and synthesizes an `exit` event when the process ends.
  **This is the crash/hang isolation boundary - scripts run in a child process,
  so the UI can never freeze.**
- `ide/runner.py` - `run_script` child entry point. Redirects stdout/stderr
  into the queue, strips IMAGE directives, injects the API into script globals,
  runs under `asyncio.run`, and awaits a top-level `async def main()` if present.
- `ide/__init__.py`, `ide/__main__.py` - `python -m rpa_framework.ide`.

### Phase 4 - Standalone Packaging (COMPLETE)
- `packaging/runtime_paths.py` - `is_compiled`, `bundle_root`, `resource_path`,
  `tesseract_cmd`, `tessdata_dir`, `configured_ocr(**kwargs)`, and (added in the
  redesign) `docs_path(name)` and `examples_dir()` which resolve either the
  bundled copy or the source-tree copy.
- `packaging/nuitka_flags.py` - static flag/data lists (APP_NAME=`RPAStudio`,
  Qt binding autodetect table, VENDOR_DATA for tessdata/tesseract, DOC_FILES,
  EXAMPLES_DIR, `--windows-console-mode=disable`).
- `packaging/build.py` - `detect_qt()`, `build_command(onefile, console)`,
  `main()`. Assembles and runs the Nuitka command; supports `--dry-run`,
  `--no-onefile`, `--console`. Now also bundles TUTORIAL.md, KILAVUZ.md, and
  examples/ as data files.
- `packaging/__init__.py`, `packaging/__main__.py` -
  `python -m rpa_framework.packaging.build`.
- **A real onefile build succeeded** with `.venv-build` (see Dependencies).
  `dist/RPAStudio.exe` was rebuilt 2026-07-04 from the redesigned UI, with
  TUTORIAL.md, KILAVUZ.md, and examples/ bundled (examples via
  `--include-raw-dir` - see Section 3).

### Follow-on A - SikuliX Compatibility Layer (COMPLETE)
- `compat/sikuli.py` - a full SikuliX-style scripting API so existing SikuliX
  Python scripts run mostly unchanged. Classes: `Location`, `Pattern`,
  `Region`, `Match`, `Screen`, `Settings`, `Key`, `KeyModifier`, `Button`,
  `FindFailed`. Functions: `find/findAll/exists/wait/waitVanish`,
  `click/doubleClick/rightClick/hover/dragDrop/wheel`, `type/paste`,
  `mouseMove/mouseDown/mouseUp/keyDown/keyUp`, `openApp/switchApp/closeApp`,
  `popup`, `sleep`, `setBundlePath/addImagePath/getBundlePath/getImagePath/
  getLastMatch`, and (added during redesign) `findElement/clickElement` (native
  accessibility search). Backend and inspector are injectable via
  `use_screen()`/`use_inspector()` for headless testing. `build_scope(dir)`
  returns the dict of names injected into scripts.
  - Feature-matching specifics: small templates are upscaled before matching
    (`_scale_for`/`_locate_scaled`); `findAll` masks found regions and falls
    back to tiled scanning; special keys use private-use Unicode codepoints
    written as `\uXXXX` escapes (ASCII-clean) mapped to per-OS key names.
- `compat/__init__.py` - re-exports `build_scope`.
- `runner.py` merges `build_scope(script_dir)` + `configured_ocr` into every
  script's globals, so all SikuliX commands and the core API are available with
  no imports in user scripts.

### Follow-on B - IDE Redesign (NEARLY COMPLETE - the active work)
The user rejected the original bare-bones window as "terrible / not usable."
Decision (recorded): **keep Qt, redesign the whole interface** VS Code-style.
Rationale: Qt is what commercial IDEs use; Electron would kill the single-file
zero-install exe and duplicate the runtime; C#/WPF would drop Linux. The
ugliness was missing design, not a Qt limitation.
- `ide/theme.py` (NEW) - VS Code "Dark+" palette (`COLORS`), full application
  `stylesheet()`, 12 programmatic vector icons drawn with QPainter (no binary
  assets - keeps everything ASCII/text and bundle-friendly), `make_icon`,
  `apply_theme(app)` (Fusion style + QPalette + QSS).
- `ide/editor.py` (REWRITTEN) - `ScriptEditor` now has a line-number gutter,
  current-line highlight (ExtraSelection), Ctrl+wheel zoom, `insert_snippet`,
  `cursor_place`, `base_dir`, and keeps inline IMAGE rendering. Uses
  Cascadia Code/Consolas monospace.
- `ide/panels.py` (NEW) - `FilesPanel` (QFileSystemModel tree),
  `SpyPanel` (live InspectorDaemon feed on a background thread, shows
  role/name/id/box/pid, inserts `clickElement(...)`), `ReferencePanel`
  (searchable categorized command list, double-click inserts snippet),
  `ConsolePanel` (colored output + clear). Also `API_REFERENCE` data (25+
  documented commands) and `spawn`/`watch` thread helpers.
- `ide/capture.py` (NEW) - `grab_desktop` (multi-monitor union grab),
  `build_capture_class` -> `CaptureOverlay` (fullscreen drag-to-select overlay
  used for both image-target capture and OCR region selection).
- `ide/app.py` (REWRITTEN) - `MainWindow` with: tabbed editors (closable,
  movable, modified-star), four dockable panels (Explorer/Element Spy/Commands/
  Output), an icon toolbar, full menu bar (File/Run/Tools/View/Help),
  Open Recent + Open Example menus, drag-and-drop .py open, status bar
  (state / path / Ln,Col), screenshot-capture-to-PNG tool that auto-inserts an
  IMAGE+click snippet, OCR-read-region tool, one-click EXE build via QProcess
  streaming to the console, Help dialogs that render TUTORIAL.md / KILAVUZ.md
  via QTextBrowser markdown, and QSettings geometry/state persistence.
  `main()` applies the theme and opens a file passed on argv.

### Documentation + Examples (COMPLETE)
- `TUTORIAL.md` (English) - full plain-language user guide, updated for the
  redesigned IDE.
- `KILAVUZ.md` (Turkish, ASCII-substituted) - mirrors TUTORIAL.md plus the
  new-IDE tour and a library-usage section.
- `README.md`, `CLAUDE.md` (inside rpa_framework) - updated to reflect all phases.
- `requirements.txt` - added `PyQt6>=6.5`.
- `examples/` - `hello_flow.py`, `notepad_typing.py`, `find_on_screen.py`,
  `spy_under_cursor.py`, `read_screen_text.py` (all run clean or degrade
  gracefully; verified through the engine).

### Verification already done
- Constraint checker passes on **all 39 Python files** (ASCII, no comments/
  docstrings/annotations; IMAGE lines exempt).
- Phase 3 engine tests: run-to-completion with API injection, cooperative
  pause/resume, mid-run stop, crash->stderr.
- Offscreen Qt tests for the original editor/window, plus GUI acceptance
  (open->run->stream->stop).
- SikuliX layer: 18 tests with a FakeBackend + synthetic SIFT scenes (find,
  small-icon upscaling, click centering, targetOffset, modifier chords, type
  splitting, wheel, dragDrop, region-scoped coords, findAll of two copies,
  waitVanish, build_scope, runtime_paths, build command).
- Injection test: sikuli + core + OCR factory reach scripts in the child process.

---

## 3. Current Status

**Where we are (2026-07-04): ALL 14 TASKS COMPLETE.** The IDE redesign is
verified, documented in two languages, and shipped as a rebuilt exe.

Completed in the 2026-07-04 session:
- #13 DONE: `rpa_framework/KILAVUZ.md` written (Turkish, ASCII-substituted, no
  accented characters). It mirrors TUTORIAL.md and adds the new-IDE tour and a
  library-usage section. TUTORIAL.md was also updated: the old two-pane "IDE in
  one paragraph" section became "A tour of the IDE" (tabs, four docks, capture/
  OCR tools, one-click build), the command table gained findElement/clickElement,
  and "Working with images" now leads with the Ctrl+Shift+C capture tool.
- #14 DONE: full verification pass, all green - constraint checker (39 py files
  + 5 docs), engine tests (run/injection, async main, pause/resume, stop mid-run,
  crash->stderr), 20 SikuliX tests, and a clean END-TO-END `test_ui_v2.py` run
  including GUI acceptance (open -> run -> stream -> finish, and run -> stop).
  The prior "hang" never reproduced in foreground runs.
- Exe REBUILT from the redesigned UI with `.venv-build`, launched, and
  screenshot captured to `workspace\rpa_studio_redesign.png` - the VS Code-style
  window renders correctly, Explorer shows the five bundled examples.

**Bug found and fixed during the rebuild:** Nuitka's `--include-data-dir`
silently skips `.py` files (it only prints "No data files in directory ...
examples"), so the examples were never actually inside the old exe.
`packaging/build.py` now uses `--include-raw-dir` for `examples/`. When
touching the build, always check the log for "Included data file 'examples\..."
lines.

**Session 3 (2026-07-04, later): the compiled exe actually works now, plus a
feature wave.** The user reported every command/example failing in the exe,
plus dead OCR and Element Spy. Root causes found and fixed:
- `comtypes.client.GetModule` generates COM binding code at runtime; under
  Nuitka this crashed ("list index out of range"), which broke `import
  pywinauto` too, which nuked ALL backend commands and the UIA inspector.
  Fix (two layers): `packaging/build.py` pre-generates the UIAutomationClient
  bindings into the build venv's `comtypes/gen` before every build
  (`pregenerate_com_bindings`), so the compiled app imports them without any
  codegen; and `core/os_facade/base.py:prepare_com_codegen` sets
  `comtypes.client.gen_dir = None` when frozen as a fallback. NEVER remove the
  pregen step. `comtypes/pywinauto/mss/pytesseract` are also force-included
  (OPTIONAL_PACKAGES in nuitka_flags).
- Nuitka's `--include-data-dir` silently skips .exe/.dll (like .py before):
  vendor dirs now go through `--include-raw-dir` as well.
- OCR: Tesseract 5.4 (UB-Mannheim, installed via winget on this machine) was
  copied into `vendor/tesseract` (exe + 51 DLLs) and `vendor/tessdata`
  (eng, osd, tur + configs). `runtime_paths` finds vendor/ in source mode too.
  OCR works out of the box, source AND compiled; `configured_ocr(lang="tur")`
  reads Turkish.
- New diagnostics: `RPAStudio.exe --selftest report.txt` probes every import,
  backend, inspector, capture, OCR, docs, examples; writes ok/fail lines.
  ALL PROBES PASS in the compiled exe. An end-to-end smoke test also passed:
  driving the exe GUI via the source framework (focus window, F5) showed the
  status bar go Idle -> Running -> Idle with a sikuli `sleep(3)` script, so
  the multiprocessing child + API injection work inside the onefile binary.

IDE feature wave (all in the exe, all tested offscreen):
- Editor autocompletion (QCompleter): sikuli `_EXPORTS` + core API + runner
  helpers + Python keywords + document words; popup after 2 chars, Enter/Tab
  accepts; auto-indent on Enter (extra level after ":").
- Tools > Insert Region From Screen (Ctrl+Shift+G): drag on screen, inserts
  `Region(x, y, w, h)` at the cursor (new "region" icon; 13 icons now).
- SikuliX dynamic regions in `compat/sikuli.py`: nearby/above/below/left/
  right (no-arg extends to screen edge), union, intersection, setROI -
  chainable off Match. Listed in the Commands panel ("Dynamic regions").
- Explorer file management: right-click New File/Folder, Rename (F2, inline),
  Delete (Del, confirm), Copy/Paste (Ctrl+C/V, auto-unique names),
  Choose Folder; model is writable now.
- requirements.txt: added explicit `comtypes`.

`dist/RPAStudio.exe` is now ~128 MB (Tesseract payload) and fully
self-contained. Screenshot: `workspace/rpa_studio_v2.png`.

**Session 4 (2026-07-04): branding + IDE feature wave 2.** All verified
offscreen + compiled selftest + screenshot (`rpa_studio_v3.png`):
- Logo: hexagon RS circuit mark drawn programmatically in `ide/theme.py`
  (`logo_pixmap`/`logo_icon`, gradient LOGO_STOPS) - window/taskbar icon,
  About dialog, and the exe file icon (build.py `build_app_icon()` renders
  vendor/app_icon.ico via offscreen Qt + PIL, passed with
  --windows-icon-from-ico).
- Capture suite: toolbar QDoubleSpinBox delay (default 2 s) feeds
  `_begin_overlay`; capture prompts for a Pattern name (.png auto-appended)
  and inserts `click(Pattern("x.png").similar(0.95))` (no more IMAGE lines
  from the tool); right-click during the drag sets a target offset marker
  and appends `.targetOffset(dx, dy)`; new "Draw Target Offset"
  (Ctrl+Shift+T) uses CaptureOverlay mode="line" and inserts the measured
  offset inline at the cursor (editor.insert_text). CaptureOverlay.captured
  is now a 3-arg signal (image, region, offset).
- Dynamic window regions: `WindowRegion` in compat/sikuli.py re-syncs
  x/y/w/h from the backend window rect on every _capture/getCenter;
  `windowRegion(title)` + `App(title)` (.open/.focus/.close/.window) exported.
- Element Spy: F8 (polled via GetAsyncKeyState in the drain timer) inserts
  the hovered element's locator instantly; "Scrape Active Window (3s delay)"
  walks the UIA tree of the active window and inserts
  `<window>_<label>_<role> = findElement(...)` lines; `slugify()` in
  panels.py transliterates Turkish chars (via \uXXXX escapes) to clean
  lowercase underscore names.
- Pass/fail: runner injects `passed(msg)` (green) and `fail(msg)` (red +
  auto screenshot via backend capture -> temp png -> event); ConsolePanel is
  now a QTextBrowser that embeds the screenshot inline as a clickable image
  (filename hidden; click opens a full-size dialog). NOTE: `pass` is a
  Python keyword, hence `passed`.
- Smart editor: Monokai palette (MONOKAI in theme.py + highlighter colors),
  live lint (compile on 500 ms debounce, error line number painted red,
  message in a status-bar label via editor.lintChanged), Tab inserts 4
  spaces.
- .sikuli: `sikuli_main_script()` resolves the inner .py; wired into File >
  Open SikuliX Folder, Explorer double-click, drag-drop, and open_path.
- Asset Tester: double-click an image in Explorer -> dialog with preview,
  similarity slider, "Find on Screen" (hides IDE, SIFT search in a worker,
  hovers the match) and "Insert Pattern".

**Session 5 (2026-07-04): capture/spy UX rework from live user feedback.**
Verified via constraint checker (39 py + 5 docs), test_sikuli (22), test_engine,
test_ui_v2 (offscreen, ~110 checks), offscreen window.grab (rpa_studio_v4.png),
and a compiled --selftest + real-font screenshot after rebuild. No app docs
touched (user asked to skip documentation this round).
- Tab close buttons were invisible: theme QSS had `image: none` on
  QTabBar::close-button. Now `theme._png_icon` renders an x glyph PNG to the
  temp dir (normal=dim, hover=bright) and `_close_button_qss()` wires
  `image: url(...)`. Confirmed the x renders in the offscreen grab.
- Instant vs delayed capture: `_begin_overlay(..., delay_seconds=0)` floors at
  160 ms (just to hide the window); only "Capture Image (Delayed)"
  (Ctrl+Shift+D, new `timer` icon) passes the spinbox value. Instant capture
  is Ctrl+Shift+C; region/offset/ocr all open immediately. Spinbox tooltip now
  says it only affects delayed capture.
- Overlay no longer commits on mouse release (that was why offsets were
  impossible - it closed instantly). New flow: drag -> release keeps the
  selection -> right-click sets the click offset (only when allow_offset) OR
  drag again to redraw -> Space/Enter commits, Esc cancels. Overlay
  grabKeyboard()s in showEvent so Space reaches the frameless Tool window; a
  top banner shows the live key hints. `_finish` split into `_commit`/`_cancel`
  guarded by `_committed`.
- Capture codegen now inserts `varname = Pattern("name.png").similar(0.95)`
  (plus `.targetOffset` when an offset was set) instead of `click(Pattern(...))`;
  `app._pattern_var` derives a short var from the file stem (slugify,
  keyword/leading-digit safe).
- findElement returns a usable `Element` proxy (compat/sikuli.py):
  click/doubleClick/rightClick/hover/type/paste/getText/getName/getRole/
  getCenter/region, with `__getattr__` delegating to the node so
  `.bounding_box/.name/.to_dict()` still work; clickElement uses it. A spied
  variable therefore works immediately (`btn.click()`); editor completion knows
  the method names.
- Element Spy hotkey is now Space (panels.space_pressed, VK_SPACE 0x20 - not F8)
  and inserts `short_var = findElement(...)` with all available attributes;
  `panels.element_var` builds the short name (element's own name+role, no window
  prefix). Scrape Active Window unchanged.
- Asset Tester opens at the image's current similarity
  (`app._similarity_for` reads a `.similar()` for that filename from the editor,
  else 0.95) and "Find on Screen" draws a red rectangle on screen via
  `capture.HighlightOverlay` (frameless, WindowTransparentForInput, translucent)
  instead of hovering the mouse. Insert Pattern also uses the var-assignment form.
- `build_capture_class(qt)` now returns a `Capture` container (`.Overlay`,
  `.Highlight`), not the overlay class directly - update any caller.

**Session 6 (2026-07-04): more live feedback - capture bug + SikuliX polish.**
- BitBlt bug fixed: WindowsBackend/LinuxBackend.capture() created one
  `mss.mss()` in __init__ and reused it; mss GDI handles are thread-bound, so
  the Asset Tester's worker-thread search failed ("Windows graphics function
  failed (no error provided): BitBlt"). Both backends now `with mss.mss() as
  sct` per call (thread-safe); `_monitor` takes (sct, region). Reproduced and
  verified with a cross-thread capture harness.
- `Offset(x, y)` class added to compat/sikuli.py (exported); Pattern.targetOffset
  accepts a raw (dx, dy) or a single Offset/Location.
- New Location tool (Ctrl+Shift+L): overlay gained mode="point" (click places a
  crosshair, Space confirms); inserts `var = Location(x, y)`.
- Every capture tool now prompts for a VARIABLE and inserts `var =
  Constructor(...)`: image `var = Pattern("var.png").similar(0.95)` with the file
  saved as <var>.png (user types only the variable, no .png); standalone offset
  tool `var = Offset(dx, dy)` (offset during image capture still appends
  `.targetOffset`); region `var = Region(...)`; location `var = Location(...)`.
  Helpers app._ask_variable (keeps a valid identifier as typed, else slugifies)
  and app._default_var (next prefix_N from the editor text).
- Element Spy reworked for clarity: numbered how-to steps, a live monospace
  preview of the exact `short_var = findElement(...)` line under the cursor,
  clearer button labels; still Space (or the button) to insert.
- Verified: constraints (39 py + 5 docs), test_sikuli 23 (added Offset test),
  test_engine, test_ui_v2 (point mode, location action/16 icons, variable-prompt
  codegen via mocked dialog, spy preview), cross-thread capture harness. Exe
  rebuilt with .venv-build + compiled --selftest.

**Session 7 (2026-07-04): PyCharm-grade editing, real element actions, failed().**
- `fail()` -> `failed()` (Python reserves `pass`, and `fail` reads oddly next to
  it); runner injects `passed`/`failed`, keeps `fail` as an alias. Command
  reference + completion + doc tables updated.
- UIA now reads element value + toggle/selection state (closes a KNOWN GAP):
  windows_inspector fills `value` via ValuePattern/LegacyIAccessible and adds
  checked/selected/expanded to `states` (pattern interfaces fetched lazily so a
  missing name can never kill the inspector). This makes Element.getText() and
  isChecked() dependable.
- compat/sikuli Element proxy (what Element Spy writes) gained real actions:
  clear, setText/write, isChecked/isSelected/isEnabled, check/uncheck/toggle,
  child/find (subtree search), expand/collapse, selectItem (list/tree) and
  select (open a combo and pick by name).
- Editor is now PyCharm-like: auto-close brackets/quotes with type-over and
  empty-pair backspace, wrap-selection, Ctrl+/ comment toggle, Ctrl+D duplicate,
  Ctrl+Y delete line, Alt+Shift+Up/Down move line, Ctrl+Shift+Z redo,
  Tab/Shift+Tab block indent, smart Home, and auto-dedent after
  return/pass/break/continue/raise. (Watch out: QTextCursor.selectedText() uses
  U+2029 as its line separator - use chr(0x2029), never a literal char, or the
  ASCII check fails.)
- Element Spy answers "how do I use it": an Action picker inserts
  `var = findElement(...)` PLUS a ready action line - click / type / clear /
  setText / getText / check / uncheck / select (combo) / selectItem (list) -
  prompting for text/item when needed.
- Verified: constraints, test_sikuli 24 (test_element_actions), test_engine,
  test_ui_v2 (PyCharm editor block + spy action picker). Exe rebuilt + selftest.

**Session 8 (2026-07-04): window-scoped elements, image context menu, and the
enterprise vision/targeting wave (8 upgrades).**
- findElement/clickElement accept `window=`, `region=`, `timeout=` so a locator
  never crosses into another app (critical for same-named controls across
  windows, e.g. combat management consoles). `_window_node` resolves the top
  window by title substring; `_in_region` filters by center point. Element Spy
  and the window scraper now emit `window='...'` in every locator (pid ->
  title via `_window_title` cache).
- Editor image right-click menu on any line referencing a .png/.jpg: Open Image
  (Asset Tester via `imageOpenRequested` signal), Rename Image File (renames on
  disk + rewrites the reference in the line), Delete Image (removes the file
  and the whole line, with confirmation).
- Vision resilience (feature_matcher.py): matching now runs representation
  passes - grayscale+CLAHE first (illumination/theme normalization), then a
  Sobel edge-magnitude pass that survives full Light/Dark inversion (test
  proves a match on `255 - scene`); DPI fallback rescales the template at
  1.5/0.75/2.0 when the direct pass fails; `MatchResult.scale` reports the
  measured on-screen scale (homography-based, so 1080p/4K/OS scaling adapt).
  Scene features are computed once per representation - low compute.
- Capture parity (A3): `mss_grab()` + `screen_origin()` live in
  os_facade/base.py; Windows and Linux backends both delegate, guaranteeing
  identical BGR uint8 arrays and a unified virtual-screen origin
  (`OSBackend.origin()`). Backends also gained horizontal scroll
  (win32 MOUSEEVENTF_HWHEEL / xdotool buttons 6-7).
- Multi-anchor + self-healing: `Target(name=..., role=..., automation_id=...,
  window=..., region=..., image=..., text=..., dx, dy)` resolves through
  element -> image (SIFT) -> OCR text, computes the click point with the
  offset, and `_HEALED` remembers the winning strategy per locator for the
  session (broken OS selectors heal to visual/OCR automatically).
  `.click()/.doubleClick()/.rightClick()/.hover()/.exists()/.resolve()`.
- Raw deep tree: `AccessibilityInspector.deepest_at(x, y)` descends through
  container layers to the smallest element under the point (Electron/web
  wrappers); `InspectorDaemon(deep=True)`; Element Spy checkbox "Raw tree deep
  scan".
- VDI mode: new `core/vision/ui_finder.py` - Canny + MORPH_CLOSE + contour
  rectangle filtering (aspect/height per kind: button/field/any, polygon
  approx with epsilon capped at 0.6*short-side - 5%-of-perimeter collapses
  elongated fields to 2 points, that was a real bug) + optional OCR text
  filter; `findUI(kind, text, region)` in sikuli returns Regions. Works with
  zero accessibility (video streams, Citrix).
- autoScroll: `wait(target, timeout, autoScroll=True)` and `click(target,
  autoScroll=True)` - after a normal miss, emits 4 wheel-down + 2 wheel-right
  events (`_AUTO_SCROLL_PLAN`) rescanning between each before FindFailed.
- Verified: constraints (40 py files), test_sikuli 30, test_engine, test_ui_v2
  (image menu, raw toggle, window locator). Exe rebuilt + selftest.

**Session 9 (2026-07-04/05): app-tracking windows, IDE platform wave, GitHub.**
- openApp now returns an App handle that tracks the launched PID and waits for
  the window; App.focus()/window() match by pid OR process exe name (backend
  process_name via GetModuleFileNameEx / /proc/comm), so Turkish-titled
  windows ("Adsiz - Not Defteri") are found from "notepad.exe". switchApp
  gained contains= (exact vs substring) and process-name fallback (guarded:
  stems < 3 chars or titles with spaces never process-match). Window control:
  WindowRegion(title, pid) with moveTo/resize/setBounds/maximize/minimize/
  restore/focus; backends gained move_window/window_state/process_name.
- Editor image rename now renames the VARIABLE too (whole-document
  word-boundary stem replace, single undo step).
- Element Spy moved to the bottom-right of Output (split dock, scroll-area
  compact layout); dock state version bumped to 2 so old layouts reset.
  New Window Spy dock (Ctrl+Shift+W): all windows with title/process/pid/
  window id/pos/size, double-click inserts App(...).
- Pause finally real: runner passes the engine pause Event into
  sikuli.use_pause_event; _pause_gate() blocks inside click/type/_poll/sleep.
- Env class (getClipboard/setClipboard/getMouseLocation/getScreenSize/
  getOS/isWindows...) + SikuliX Settings extras (ClickDelay, DelayBeforeDrag/
  Drop/MouseDown, DefaultHighlightTime, OcrLanguage, WaitScanRate...) honored
  in click/dragDrop/highlight/Region.text. Region/Match/Element.highlight()
  draws a real red frame via GDI (win32gui Rectangle loop + InvalidateRect).
- IDE platform features: tab context menu (close others/right/all, PIN via
  orange tab text excluded from bulk close, copy path, reveal, rename file,
  open read-only view window); Settings dialog gained a Shortcuts tab -
  every action rebindable (QKeySequenceEdit, stored as key_<action>);
  Find in Files Ctrl+Shift+F / Replace in Files Ctrl+Shift+R / Go to File
  Ctrl+Shift+N (walk root, skip .venv/dist/.git, open at line); embedded
  Terminal dock (QProcess cmd.exe /Q /K, Alt+F12) + open-system-terminal
  button; Explorer: python.svg icons for .py (recolored SVG via temp file),
  image/md/sikuli icons (FileIcons provider), expand/collapse buttons,
  New Sikuli Folder (name.sikuli/name.py), drag-move, copy path, reveal;
  Explorer root no longer jumps into opened folders (open_path keeps root
  when the file is under it). Spinbox up/down arrows drawn (theme PNG QSS).
- Branding: vendor/logo2.png (user's purple R) is now the logo -
  theme.logo_pixmap prefers the file (runtime_paths.logo_path), build ico
  derives from it automatically; vendor/icons bundled (VENDOR_DATA) and
  logo2.png bundled (VENDOR_FILES).
- OCR: tessdata_best eng downloaded as eng_best.traineddata; user's
  dejavu_sans.traineddata added; _prepare upscales small crops (<40px, 2-4x
  cubic) + bilateral filter before Otsu; Settings.OcrLanguage wired into
  Region.text(); IDE OCR tool uses the ocr_lang setting.
- Git: repo initialized at workspace root (main), .gitignore excludes
  .venv*/dist/pycache/screenshots; vendor INCLUDED (largest file 96.8MB,
  under GitHub's 100MB hard limit). First commit f3e4215. gh CLI installed;
  push via gh repo create rpa-studio --private --source=. --push after
  device-flow login.
- KILAVUZ.md fully rewritten (Turkish, ASCII) covering everything; copied to
  workspace README.md for GitHub.
- Verified: constraints (40 files), test_sikuli 32 (window interactions,
  Env+pause gate), test_engine, test_ui_v2 (23 icons, 6 docks, settings/
  shortcuts/pins/sikuli-folder/search/window-spy checks). Exe rebuilt.

**Immediate next action:** none required - the remaining backlog is Section 5
(Role A known-gaps work and Role B polish, e.g. welcome tab, multi-monitor
capture coordinates).

Standing flags: **builds must use `.venv-build` (python.org 3.14), never
`.venv`** (Store Python cannot link); run `--selftest` on the exe after every
rebuild; check build logs for "Included data file" lines when touching
bundled data.

---

## 4. Agent Roles & Task Delegation

The project splits cleanly along the reliability architecture. Keep this lean -
four roles, with clear boundaries. A single assistant can wear one hat at a time;
do not cross boundaries without reason.

### Role A - Automation Core Engineer ("the hands and eyes")
- **Owns:** `core/os_facade/`, `core/vision/`, `core/inspector/`, and the
  matching/keyboard/element logic inside `compat/sikuli.py`.
- **Responsibilities:** native input, screen capture, window control per OS;
  SIFT/ORB feature matching and OCR; accessibility tree extraction (UIA/AT-SPI);
  cross-platform key-name and coordinate correctness.
- **Boundary:** does not touch Qt/UI code. Must preserve the import-anywhere
  rule and the factory/registry pattern. Anything that talks to the OS or
  interprets pixels is theirs.

### Role B - IDE / Desktop UX Engineer ("the face")
- **Owns:** `ide/` except `engine.py`/`runner.py` (those are shared with Role C):
  `theme.py`, `editor.py`, `panels.py`, `capture.py`, `app.py`, `highlighter.py`,
  `directives.py`, `qt_shim.py`.
- **Responsibilities:** everything the user sees and clicks - theme, tabs, docks,
  toolbar/menus, the editor experience (gutter, highlighting, inline images,
  zoom, snippet insertion), the spy/reference/console panels, and the
  screenshot/OCR overlay tools. UI/UX quality and responsiveness.
- **Boundary:** never runs blocking/native automation on the GUI thread - all
  automation goes through the engine (Role C). Consumes the script API and
  InspectorDaemon but does not implement matching or OS calls.

### Role C - Packaging & Systems Integrator ("the plumbing")
- **Owns:** `packaging/`, `ide/engine.py`, `ide/runner.py`, the two build
  environments, `runtime_paths`, and the Nuitka pipeline.
- **Responsibilities:** the multiprocessing execution model and event bridge,
  child-process API injection, resource-path resolution (source vs. compiled),
  bundling data (tessdata/tesseract/docs/examples), and producing the working
  standalone exe.
- **Boundary:** defines *how* scripts run and ship, not *what* the automation
  commands do (Role A) or how the window looks (Role B).

### Role D - Documentation & QA Specialist ("the proof")
- **Owns:** `TUTORIAL.md`, `KILAVUZ.md`, `README.md`, `examples/`, and the
  verification/constraint test scripts (in the session scratchpad).
- **Responsibilities:** user-facing docs (English + Turkish), runnable examples,
  the offscreen/headless test suites, and enforcing the NON-NEGOTIABLE code
  constraints on every change (run the constraint checker after edits).
- **Boundary:** does not change feature behavior; writes tests and docs against
  what A/B/C build, and flags violations back to them.

---

## 5. Next Steps (by role, in priority order)

Items 1-4 (KILAVUZ.md, verification, rebuild, screenshot) were COMPLETED on
2026-07-04 - see Section 3. What remains:

### FIRST - Role A (Automation Core), from CLAUDE.md "KNOWN GAPS"
5. Windows `UIAInspector.value` is empty - add ValuePattern/TextPattern via
   `GetCurrentPattern`.
6. Linux hit-testing walks the tree with extent pruning - prefer
   `Component.get_accessible_at_point` where reliable.
7. Unify cross-platform key names (Linux xdotool keysyms vs Windows VK_ names)
   if higher-level key APIs are added.
8. Add a stable-locator layer over `UIElement` (search by role/name/id path) for
   resilient selection - partially seeded by `findElement`, could be generalized.

### ONGOING - Role B (IDE/UX)
9. Polish: multi-monitor coordinate correctness in the capture overlay;
   optional autocomplete for the injected API; a proper "welcome" tab. These are
   enhancements, not blockers.

---

## 6. Dependencies and Notes

### Two Python environments (CRITICAL - do not mix them up)
- **`.venv`** = Microsoft Store Python 3.13. Use for **running and testing** the
  app and the test suite. **CANNOT build with Nuitka** - the Store install
  blocks access to its link libraries ("AccessDenied ... python313.lib"). The
  first build attempt failed here.
- **`.venv-build`** = python.org Python 3.14 (available via `py -V:3.14`). Use
  **only for Nuitka builds**. The successful `dist/RPAStudio.exe` came from here.
  Nuitka prints an "experimental 3.14" warning but the build works.
- Both have `-r requirements.txt` installed; `.venv-build` also has `nuitka`.

### Build specifics
- Command: from `C:\Users\Elessar\Desktop\workspace`, run
  `.venv-build\Scripts\python.exe -m rpa_framework.packaging.build`.
- First build downloads ziglang (C compiler) and dependency-walker automatically;
  it can take 30-60 min. Rebuilds are faster (cached).
- `--dry-run` prints the command without building; `--no-onefile` makes a folder
  build (faster iteration); `--console` keeps a console window for debugging.
- Nuitka warns it cannot find Windows Runtime DLLs - target machines need the VC
  runtime (present on essentially all Win10/11). Onefile compresses ~290 MB dist
  to ~78 MB payload.
- `--include-data-dir` skips `.py` files silently; `examples/` is bundled with
  `--include-raw-dir` instead (fixed in build.py on 2026-07-04).
- **The current `dist/RPAStudio.exe` (built 2026-07-04) is the redesigned UI**
  with docs and examples bundled.

### NON-NEGOTIABLE code constraints (from CLAUDE.md - violations are rejected)
Apply to **every Python file** added or edited:
1. **No comments, no docstrings, no inline explanations** of any kind.
2. **No type hints or annotations** anywhere.
3. **ASCII only** - every character (code, strings, identifiers, filenames) must
   be 7-bit ASCII. For special/unicode needs use `\uXXXX` escapes (as done for
   SikuliX key codepoints in `compat/sikuli.py`).
4. **Extreme DRY** - share helpers; reuse `Rect` and the factory/registry
   patterns; do not copy-paste.
5. **Match the style** - 4-space indent, `__slots__` on data classes, thin
   backend classes, broad `try/except` around every native OS/COM/AT-SPI call so
   failures degrade gracefully.
Markdown/docs files are exempt from 1-2 but keep #3 (ASCII) for safety.

### The constraint checker
Lives in the session scratchpad (session-specific temp, path:
`...\scratchpad\check_constraints.py`). It tokenizes + AST-parses every
`rpa_framework\**\*.py` and flags non-ASCII bytes, comments, docstrings, and
annotations. **It treats `IMAGE:` directive lines as exempt** from the annotation
check (they parse as `target: expr` but are stripped before execution). Re-create
it if the scratchpad is cleared; keep the IMAGE exemption.

### Import-anywhere invariant (do not break)
No platform module (win32, comtypes, gi, xdotool wrappers) and no Qt binding may
be imported at module top level. cv2/numpy imports are guarded with
try/except -> None. All native loading happens lazily in `create()` /
`load_qt()`. This is what keeps tests and Nuitka analysis working on any OS.

### Known bugs / rough edges
- Multi-monitor click coordinates are best-effort; keep target apps on the
  primary monitor for now.
- OCR needs a Tesseract binary: install system-wide (on PATH) or drop a portable
  copy into `vendor/tesseract` + `vendor/tessdata` next to `rpa_framework` and it
  gets bundled + auto-wired via `runtime_paths`. Until then OCR features raise a
  friendly error.
- `type()` intentionally shadows Python's builtin inside scripts (SikuliX
  parity). SikuliX `observe()`/event handlers and `Finder` are not implemented.
- Scripts run on real CPython 3, not Jython - Java imports in old SikuliX scripts
  won't work; `similar()` values are approximate (feature-based, not pixel).

### Handy commands
- Run the IDE (source): `python -m rpa_framework.ide` from the workspace dir
  (using `.venv`).
- Run the spy daemon: `python -m rpa_framework.core.inspector 0.3`.
- Public API import surface: `from rpa_framework.core import (...)` - see
  `core/__init__.py` `__all__`.

### Memory
A project memory note exists at the Claude memory path
(`rpa-framework-project-state.md`) capturing the layout, venvs, build command,
and constraints. Keep it in sync if major things change.
