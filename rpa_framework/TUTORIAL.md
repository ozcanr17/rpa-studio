# RPA Studio - Complete Guide

RPA Studio automates a real desktop. You write a short script that says "click
this, type that, wait for this picture, read that text", press Run, and it
drives the mouse and keyboard exactly like a person would - only faster and
without getting bored.

It is three things in one:

- a **desktop IDE** for writing, capturing, and running automation,
- a **SikuliX-compatible engine** so your existing `.sikuli` scripts run
  almost unchanged,
- an **importable Python library** you can call from your own programs.

This guide covers all three. There is a Turkish version in KILAVUZ.md.

---

## 1. Why it is reliable: two ways of seeing the screen

Automation targets are located two independent ways, and the combination is
what makes it robust:

1. **Native accessibility (primary).** It asks the operating system directly:
   "what control is at this spot, what is it called, where is it?" This is the
   same layer screen readers use - Windows UI Automation, Linux AT-SPI. It is
   fast and exact and survives theme or resolution changes.
2. **Computer vision + OCR (fallback).** It looks at pixels like a human: you
   give it a cropped screenshot and it finds that picture on screen (feature
   matching, SIFT/ORB - robust to scaling and small changes), and it reads
   on-screen text with Tesseract OCR.

When one way fails the other usually works. The `Target(...)` locator even
combines them and remembers which one succeeded (self-healing).

---

## 2. Install and first run

### From source (needs Python 3.8+)

Open a terminal in the folder that contains `rpa_framework` and run:

    python -m venv .venv
    .venv\Scripts\activate           (Linux/macOS: . .venv/bin/activate)
    pip install -r rpa_framework\requirements.txt
    python -m rpa_framework.ide

The RPA Studio window opens. Then:

1. File > Open Example, pick `hello_flow.py`.
2. Press **Ctrl+3** (or the Run button). Output streams into the Output panel.
3. Press **Ctrl+4** to pause, **Ctrl+4** again... actually press the Run button
   again to resume; **Ctrl+5** stops.

### From the standalone build (nothing to install)

Download `RPAStudio.exe` (Windows) or the `rpa-studio-linux` folder (Linux)
from the GitHub Releases page and launch it. Python, Qt, OpenCV, and Tesseract
are all embedded - a clean machine runs it with nothing preinstalled.

---

## 3. The IDE, panel by panel

The window is laid out like VS Code: a tabbed editor in the middle with
dockable panels around it. Toggle panels from the View menu or the three panel
buttons at the right of the toolbar; drag them anywhere - the layout is
remembered.

### Editor (center)
- Monokai syntax colors, line numbers, current-line highlight, indent guides.
- **Autocompletion**: after two letters a popup suggests every scripting
  command (click, Pattern, findText, observe...), Python keywords, and words
  already in your file. Enter or Tab accepts.
- **PyCharm-style editing**: auto-closing brackets/quotes, Ctrl+/ comment
  toggle, Ctrl+D duplicate line, Ctrl+Y delete line, Alt+Shift+Up/Down move
  line, Tab/Shift+Tab indent a selection, smart Home, auto-indent after `:`.
- **Live syntax check**: a bad line turns its number red and the error shows in
  the status bar.
- **Inline images**: a line `IMAGE: picture.png` shows that picture right in
  the code (ignored when the script runs). Right-click such a line to open,
  rename, or delete the image file.
- Ctrl+mouse-wheel zooms. Tabs show a `*` when unsaved. Drop a `.py` file or a
  `.sikuli` folder onto the window to open it.

### Explorer (left)
A file tree of your script's folder. Double-click to open. Right-click to
create / rename / delete / copy / paste files and folders (F2, Del, Ctrl+C,
Ctrl+V) or to choose another folder. Double-clicking a `.sikuli` folder opens
the script inside. Double-clicking an image opens the **Asset Tester**: adjust
the similarity slider, press "Find on Screen" to test the picture live (a red
frame is drawn on the match), or insert a ready Pattern line.

### Element Spy (bottom, tabbed with Output)
Press "Start watching" and move the mouse: the real UI element under the cursor
(role, name, id, class, bounding box, pid) is shown live from the OS
accessibility tree. **Right-click** while hovering to insert the element's
locator instantly. An Action picker can add a ready action line
(`.click()`, `.type("..")`, `.check()`, `.select("..")`...). **Scrape Active
Window** waits 3 seconds while you focus the target app, then inserts a named
variable for every element it finds (clean lowercase names, Turkish characters
transliterated). Ctrl+Shift+E raises the panel.

### Window Spy (bottom, tabbed)
Lists every open window with title, process, pid, position and size.
Double-click one to insert an `App(...)`. Ctrl+Shift+W.

### Commands (right)
A searchable, categorized list of every scripting command. Hover for a
description; double-click to insert the snippet.

### Output (bottom)
Everything your script prints, live: normal text white, errors red, status
events green, tool messages yellow. `failed(...)` embeds a clickable
screenshot. When a script errors, a plain-language explanation with the script
line number is shown.

### Terminal (bottom)
A built-in command line (Alt+F12). Type a command, press Enter; `cd` and
`clear` are built in, Up/Down recall history, a stop button kills a running
command. It runs `cmd` on Windows and your shell on Linux.

### Toolbar tools
- **Run / Pause / Stop (Ctrl+3 / Ctrl+4 / Ctrl+5).** Your script always runs in
  a separate helper process, so even `while True: pass` cannot freeze the
  window and Stop always works. While paused the Pause button dims and the play
  button becomes "Resume".
- **Capture Image, instant (Ctrl+1)** and **delayed (Ctrl+2).** The window
  hides (delayed waits the toolbar delay box first, so you can open menus or
  hover states), the screen freezes, and you drag a box around the target. A
  right-click during the drag marks where the click should actually land
  (target offset). You name the capture and a
  `var = Pattern("name.png").similar(0.95)` line is inserted (with
  `.targetOffset(x, y)` if you set one).
- **Capture Region From Screen (Ctrl+Shift+D).** Drag any area; a
  `var = Region(x, y, w, h)` is inserted - scope searches or read text there.
- **Capture Location From Screen (Ctrl+Shift+L).** Click a point; a
  `var = Location(x, y)` is inserted.
- **Draw Target Offset (Ctrl+Shift+O).** Drag a line to measure a
  `.targetOffset(x, y)`.
- **Read Screen Text / OCR (Ctrl+Shift+T).** Drag any region; the recognized
  text prints to Output.
- **Find in Files (Ctrl+Shift+F)**, **Replace in Files (Ctrl+Shift+R)**,
  **Go to File (Ctrl+Shift+N).**
- **Build Standalone EXE (Tools menu).** One click runs the Nuitka build and
  streams progress to Output (only when running from source).
- **Help menu.** This guide (F1) and the Turkish guide (F2) open in-app.

---

## 4. Your first script

New file, type this, save as `my_first.py`, press Ctrl+3:

    print("watch the mouse!")
    hover(Location(500, 300))
    type("hello robot" + Key.ENTER)

No imports are needed - every command below is built in. Scripts may also
define `async def main(): ...` and it is awaited automatically, so you can
`await checkpoint()` inside long loops.

---

## 5. Full scripting reference

Everything here is available in IDE scripts, in `rpa-run` scripts, and inside a
`.sikuli` file, all with no imports. (In your own Python programs, import them
first - see section 8.)

### 5.1 Mouse

    click("save.png")                 find the picture, left-click its center
    click(Location(100, 200))         click exact coordinates
    click(region)                     click a region's center
    doubleClick("icon.png")           double-click
    rightClick("row.png")             right-click
    hover("menu.png")                 move the mouse onto the target
    dragDrop("file.png", "trash.png") drag first target onto the second
    drag("file.png"); dropAt("bin.png")   the two halves separately
    wheel(WHEEL_DOWN, 3)              scroll 3 notches (WHEEL_UP to go up)
    mouseMove(Location(10, 20))       move the mouse
    mouseMove(30, -5)                 move by an offset from here
    mouseDown(); mouseUp()            press / release a button manually

A click target may be a picture path, a Pattern, a Location, a Region, a Match,
an Element, or a Target. Add `modifiers=` (e.g. `KeyModifier.CTRL`) to any
click, and `autoScroll=True` to scroll-and-rescan when the target is below the
fold.

### 5.2 Keyboard

    type("hello" + Key.ENTER)         type text then press Enter
    type("field.png", "text")         click the field first, then type
    type("s", KeyModifier.CTRL)       press Ctrl+S
    paste("long text")                paste via clipboard (fast, any text)
    keyDown(Key.SHIFT); keyUp(Key.SHIFT)   hold / release a key

`Key.*` covers ENTER, TAB, ESC, BACKSPACE, DELETE, arrows, HOME/END, PAGE_UP/
DOWN, F1-F12, CTRL/ALT/SHIFT/WIN, and more. `KeyModifier.*` is CTRL, ALT,
SHIFT, WIN/META/CMD (add them to combine: `CTRL + SHIFT`).

### 5.3 Finding pictures

    m = find("logo.png")              find now; returns a Match (throws if none)
    wait("dialog.png", 10)            wait up to 10s; throws FindFailed if none
    exists("popup.png", 3)            like wait but returns None instead
    has("popup.png")                  True/False shortcut
    waitVanish("spinner.png", 30)     wait until it disappears
    for m in findAll("row.png"): ...  every occurrence (iterator)
    findAllList("row.png")            same as a list sorted best-first, no throw
    findAllByRow("cell.png")          all matches top-down then left-right
    findAllByColumn("cell.png")       all matches left-right then top-down
    findBest("ok.png", "yes.png")     the strongest match among several
    findAny("a.png", "b.png")         list of whichever are on screen now
    waitAny(10, "ok.png", "err.png")  wait for any of them; waitBest for one
    waitBest(10, "a.png", "b.png")    wait, return the strongest

Tuning: `Pattern("btn.png").similar(0.9)` demands a stricter match, `.exact()`
is near-exact, `.targetOffset(20, 0)` clicks 20px right of the found center.

### 5.4 Searching inside an image with Finder

`Finder` searches a saved image or a captured frame instead of the live screen:

    f = Finder("screenshot.png")
    if f.find("button.png"):
        print(f.next().getScore())
    for m in f.findAll("row.png"):
        print(m.x, m.y)
    changes = Finder("before.png").findChanges("after.png")   # changed areas

### 5.5 Reading text on screen (OCR)

    Region(0, 0, 800, 200).text()     read all text in an area as one string
    m = findText("Save As")           find a line of text; a clickable Match
    findWord("Username")              find a single word
    findLine("Total: 42")             find a whole line
    hasText("Ready")                  True/False
    waitText("Done", 20)              wait for text to appear
    for m in findWords(): ...         every recognized word as a Match
    for m in findLines(): ...         every line as a Match
    collectWordsText()                all words as plain strings
    collectLinesText()                all lines as plain strings

    OCR.readText("crop.png")          OCR any image file, region, or array
    OCR.readLine(region)              one line; readWord, readChar too
    OCR.readWords(region)             word Matches; readLines for line Matches
    OCR.language("tur")               switch OCR language

`findText`/`findWord` return a Match you can click: `click(findText("OK"))`.
Set the default language with `Settings.OcrLanguage = "eng_best"` (bundled:
eng, eng_best, tur, dejavu_sans; drop more `.traineddata` into vendor/tessdata
and rebuild).

### 5.6 Watching for events (observe)

Register handlers, then observe for a while. Handlers get an `ObserveEvent`.

    def on_alert(e):
        print("appeared at", e.getMatch())
        click(e.getMatch())

    reg = Region(0, 0, 800, 600)
    reg.onAppear("alert.png", on_alert)     # or onVanish / onChange
    reg.onChange(100, lambda e: print("changed:", e.getChanges()))
    reg.observe(30)                         # blocking, up to 30s
    reg.observeInBackground(30)             # in a thread
    if reg.isObserving(): reg.stopObserver()
    for e in reg.getEvents(): print(e.getType())

`onChange(minPixels, handler)` fires when at least that many pixels change.
`ObserveEvent` has `.getType()`, `.getMatch()`, `.getRegion()`,
`.getChanges()`, `.isAppear()/.isVanish()/.isChange()`, `.repeat()`.

### 5.7 Regions, locations, geometry

    Region(0, 0, 800, 600)            an area of the screen
    Location(500, 300)                an exact point
    Offset(10, -4)                    a relative shift
    r.getTopLeft(); r.getCenter(); r.getBottomRight()
    r.grow(20)                        20px bigger all round (also 2- and 4-arg)
    r.nearby(50)                      alias for grow
    r.above(120); r.below(); r.left(); r.right(200)   strips around r
    r.union(other); r.intersection(other)
    r.offset(dx, dy); r.moveTo(loc); r.morphTo(other)
    r.setROI(x, y, w, h)              move+resize in place
    r.setRaster(rows, cols); r.getCell(row, col); r.getRow(i); r.getCol(j)
    r.highlight(2)                    flash a red frame for 2s (color optional)
    click(find("label.png").right(150))    act relative to an anchor

A `Region` also has its own `find/wait/exists/click/type/...`, so you can scope
any search: `Region(0,0,400,300).exists("icon.png")`. Per-region tuning:
`r.setAutoWaitTimeout(5)`, `r.setWaitScanRate(3)`, `r.setThrowException(False)`.

### 5.8 Applications and windows

    app = openApp("notepad.exe")      start a program, get an App handle
    switchApp("Notepad")              focus by title OR process name
    closeApp("Notepad")               close a window's process
    app = App("Notepad"); app.open(); app.focus(); app.close()
    app.isRunning(); app.window()     the window as a WindowRegion
    win = windowRegion("Notepad")     a region glued to a window
    win.moveTo(0, 0).resize(800, 600).focus()
    win.maximize(); win.minimize(); win.restore(); win.setBounds(...)
    win.find("save.png")              search only inside that window

`App`/`switchApp` match by pid, exact title, title substring, or process exe
name, so localized titles ("Adsiz - Not Defteri" from "notepad.exe") are found.

### 5.9 Native UI elements (accessibility)

    btn = findElement(name="OK", role="Button")
    findElement(name="Fire", window="Weapon Control")   # only in that window
    findElement(automation_id="submit", timeout=5)
    clickElement(name="OK", role="Button")

The returned `Element` acts on the real control:

    btn.click(); btn.doubleClick(); btn.rightClick(); btn.hover()
    field.setText("hello")    field.clear()    field.type("more")
    box.check(); box.uncheck(); box.isChecked()
    combo.select("Option 2")          open a combo and pick by name
    listbox.selectItem("Row 3")       pick a list/tree item by name
    node.expand(); node.collapse()
    child = panel.child(name="Save")  search inside this element
    e.getText(); e.getName(); e.getRole(); e.region(); e.highlight()

### 5.10 Self-healing multi-anchor targets

`Target` tries the OS element first, then an image, then OCR text, and
remembers which worked for the session:

    Target(name="Fire", window="Console", image="fire.png", text="FIRE").click()
    t = Target(automation_id="submit", image="submit.png")
    t.exists(); t.hover(); t.doubleClick(); t.targetOffset(5, 0).click()

### 5.11 Vision-only controls (no accessibility)

For Citrix, VDI, or video streams with no accessibility tree:

    findUI("button", text="OK")       list Regions that look like an OK button
    findUI("field"); findUI("any", region=Region(0,0,800,600))

`findUI` has two engines and picks the best one automatically:

1. **AI vision (semantic).** If a UI-detection model is bundled (see below),
   an offline ONNX neural network scans the screenshot and returns elements by
   *meaning* - "this is a button", "this is an input field" - even when the
   pixels, theme, or DPI have changed. Nothing leaves the machine: inference
   runs locally on the CPU through the bundled onnxruntime.
2. **Shape heuristics (fallback).** Without a model, the classic
   contour-based detector (edges + rectangle filtering) is used, exactly as
   before.

Supported kinds with the default model labels: `button`, `field`, `checkbox`,
`combobox`, `radio`, `link`, `icon`, `image`, `menu`, `slider`, `switch`,
`tab`, `text`, `scrollbar`, `window`, plus `any`. Common synonyms are
accepted (`input`/`edit`/`textbox` -> `field`, `dropdown`/`select` ->
`combobox`, and so on).

`Target` also gained a fourth self-healing anchor: after `element`, `image`,
and `text` all fail, it asks the AI detector for an element whose class
matches the Target's `role` (filtered by `text` when given). The `ui` anchor
only activates when a model is bundled, so behavior without one is unchanged:

    Target(role="button", text="Save", window="Editor").click()

#### Enabling AI vision

Drop a YOLO-format ONNX model into `vendor/models/` (source tree) or
`models/` (portable build folder), for example `models/ui_detect.onnx`. Class
names are read from the model metadata when present, otherwise from a
`ui_detect.labels` file next to it (one class name per line), otherwise the
default label list above is assumed. Everything works fully offline - the
model file ships inside the app folder.

#### Direct API (library use)

    from rpa_framework.core import UIDetector, find_ui
    from rpa_framework.packaging import configured_detector

    detector = configured_detector()          bundled model, or None
    detector = UIDetector("my_model.onnx")    explicit model file
    hits = detector.detect(frame, kind="button", min_score=0.5)
    hits[0].rect; hits[0].label; hits[0].score

    boxes = find_ui(frame, "field", detector=detector)   Rect list, heuristic fallback

The detector loads lazily on first use and is cached for the session. Scripts
always execute in the runner child process, so inference never blocks the IDE;
when embedding the library in your own GUI, call `detect` from a worker
thread.

### 5.12 Dialogs and user input

    popup("done!")                    message box with OK
    popError("something broke")       error message box
    if popAsk("Continue?"): ...       Yes/No, returns True on Yes
    name = input("Your name?")        one line of text (hidden=True for password)
    notes = inputText("Notes:")       multi-line text
    choice = select("Pick", options=["A", "B"])   drop-down list
    path = popFile()                  open-file dialog, returns a path

### 5.13 Environment, clipboard, settings

    Env.getClipboard(); Env.setClipboard("hi")
    Env.getMouseLocation(); Env.getScreenSize()
    Env.getOS(); Env.isWindows(); Env.isLinux(); Env.isMac()
    getNumberScreens(); Screen(0); Screen(1)      multi-monitor

    Settings.MinSimilarity = 0.8      global match strictness (default 0.7)
    Settings.AutoWaitTimeout = 5      default wait() timeout
    Settings.ClickDelay = 0.3         also MoveMouseDelay, TypeDelay
    Settings.DelayBeforeDrag = 0.5    also DelayBeforeMouseDown/Drop
    Settings.DefaultHighlightTime = 3
    Settings.OcrLanguage = "tur"
    Settings.ObserveScanRate = 3      searches per second while observing
    setShowActions(True)              flash a marker before each action (demo)

### 5.14 Flow, paths, output

    sleep(2)                          wait seconds (respects the Pause button)
    exit(0)                           stop now with an exit code
    setBundlePath("."); addImagePath("assets"); addImportPath("lib")
    makePath("a", "b"); getBundlePath(); getParentFolder()
    emit("stage", "login ok")         green status event in the IDE console
    passed("login ok")                green success line in Output
    failed("button missing")          red line + automatic clickable screenshot
    wait_if_paused()                  let the Pause button take hold in a loop

`passed`/`failed` are named that way because Python reserves `pass` and a bare
`fail` reads oddly next to it; `emit`, `passed`, `failed`, `wait_if_paused`,
and `checkpoint` are provided by the runner (IDE and `rpa-run`).

---

## 6. Working with images

Fastest: press **Ctrl+1** in the IDE and drag a box around the target - the
crop is saved next to your script and the code is inserted.

By hand: put the target on screen, snip it tightly (Win+Shift+S on Windows),
save the `.png` next to your script, and use the file name: `click("btn.png")`.

Tips: detailed crops (text, edges, corners) match far better than flat
single-color areas; 60-200 pixels on a side is the sweet spot. Add
`IMAGE: btn.png` above the code to preview it inline in the editor.

---

## 7. Running your existing SikuliX scripts

Open the `.py` inside your `something.sikuli` folder and press Run - the images
next to it are found automatically. You can also run a whole folder from the
command line (section 8). The full SikuliX scripting surface is implemented:
Region/Screen/Pattern/Match/Location/Offset/Finder/App/Key/KeyModifier/
Settings/Env/OCR, the find family, the text/OCR search family, observe/onAppear/
onVanish/onChange, dialogs, and the geometry/raster helpers.

Differences to know:

- Scripts run on real **CPython 3**, not Jython - modern Python works, Java
  imports (`from java.awt ...`) do not.
- Image matching is **feature-based (SIFT)**, robust to scaling and small theme
  changes; `similar(x)` is an approximate strictness knob, not an exact pixel
  percentage.
- `type()` intentionally shadows Python's built-in `type` inside scripts,
  exactly like SikuliX.
- Reusing another `.sikuli` as a module works: `import mylib` finds
  `mylib.sikuli/mylib.py` on the image/import path and injects the API into it
  automatically.

---

## 8. Using it as a library / command line

### Run a script or folder headlessly

    rpa-run login.sikuli              run a .sikuli folder, then exit
    rpa-run test.py                   run a single file
    rpa-run a.sikuli b.sikuli -c      several, continue on error
    rpa-run login.sikuli --verbose    also print emit() events
    rpa-run --list                    list every command available in scripts

`rpa-run` is the direct replacement for `java -jar sikulix.jar -r test.sikuli`.
Exit code is 0 when all scripts pass, non-zero otherwise - good for cron/CI.

### Import it into your own Python

    pip install .            # from the folder with pyproject.toml (engine only)
    pip install .[gui]       # also the desktop IDE

    import rpa_framework
    rpa_framework.run("login.sikuli")        # returns an exit code

    from rpa_framework.compat.sikuli import Screen, Pattern, Key, Region
    scr = Screen()
    scr.click("button.png")
    scr.type("hello" + Key.ENTER)
    print(Region(0, 0, 800, 200).text())

    from rpa_framework.core import OSFacadeFactory, InspectorFactory
    backend = OSFacadeFactory.create()
    inspector = InspectorFactory.create()

Offline install for closed networks (build a wheelhouse on a matching machine):

    python -m rpa_framework.packaging.offline download ./wheelhouse
    pip install --no-index --find-links ./wheelhouse .

Linux specifics (RHEL/CentOS 8, dependencies, headless Xvfb) are in LINUX.md.

---

## 9. Building the portable folders

Every artifact is a standalone portable FOLDER: copy it to a fresh, air-gapped
Windows or Linux machine and it runs with zero installs - no Python, no
OpenCV, no Tesseract, no onnxruntime. All shared libraries (`.dll` / `.so`)
ship inside the folder.

    scripts\build_windows.ps1               Windows IDE: dist\rpa-studio-windows\ (+ zip, + selftest)
    scripts\build_windows.ps1 -Headless     Windows runner: dist\rpa-run-windows\
    scripts/build_linux.sh                  Linux IDE: dist/rpa-studio-linux/ (+ tar.gz)
    scripts/build_linux.sh headless         Linux runner: dist/rpa-run-linux/ (+ tar.gz)

Or call the packager directly:

    python -m rpa_framework.packaging.build             # GUI standalone folder
    python -m rpa_framework.packaging.build --headless  # rpa-run, no Qt

Notes: Nuitka does not cross-compile (build Windows on Windows, Linux on
Linux) and does not support Microsoft Store Python (use a python.org install).
The first build downloads a C compiler and can take a while. To embed OCR, put
`vendor/tesseract/` (binary + DLLs) and `vendor/tessdata/` (the `.traineddata`
files) next to `rpa_framework` before building. To embed AI vision, put the
`.onnx` UI-detection model (plus optional `.labels` file) in `vendor/models/`.
Both are bundled and wired up automatically, and onnxruntime is included in
the folder whenever it is installed in the build venv. Flags: `--dry-run`,
`--console`, `--onefile` (legacy single-file build). Full matrix in
BUILDING.md.

---

## 10. When something goes wrong

- **FindFailed: image not found** - the `.png` is not next to the script; check
  the name and folder.
- **not found on screen** - crop a bigger, more detailed picture; make sure the
  target is visible and not covered; lower `.similar(...)` or the global
  `Settings.MinSimilarity`.
- **text not found** - OCR needs clear, reasonably large text; try
  `Settings.OcrLanguage` or a tighter region.
- **BackendError: ... required** - a package is missing; re-run
  `pip install -r rpa_framework\requirements.txt`.
- **OCR returns nothing** - the `vendor` folder is missing next to
  `rpa_framework` (source runs) or the exe was built without it.
- **Clicks land oddly on multi-monitor setups** - keep the target app on the
  primary monitor for now, or scope with `Screen(1)`.
- **findUI feels dumb (misses obvious buttons)** - no AI model is bundled, so
  the shape heuristic is running; add a model under `models/` (see 5.11).
- **Anything else** - run `RPAStudio.exe --selftest report.txt`: it probes the
  backend, inspector, capture, OCR, AI vision, docs, and examples and marks
  each ok/fail.

---

## 11. Layout (for developers)

    rpa_framework/
      core/os_facade/   mouse, keyboard, screen capture, windows (per-OS)
      core/vision/      SIFT/ORB image finding, OCR, AI + heuristic UI detection
      core/inspector/   accessibility tree access (UIA / AT-SPI) + spy daemon
      compat/sikuli.py  the SikuliX-compatible scripting API
      ide/              editor, panels, capture tools, the safe script runner
      packaging/        Nuitka build, runtime paths, offline wheelhouse
      scripting.py      Qt-free script execution (used by rpa-run and the IDE)
      examples/         ready-to-run scripts

New OS backends register with `@register_backend`, inspectors with
`@register_inspector`; factories load native libraries only on demand, so every
module imports on any OS. To add a new built-in script command, add it to
`compat/sikuli.py` and its `_EXPORTS` - the IDE completion, the Commands panel,
`rpa-run --list`, and injected scopes all read from there.
