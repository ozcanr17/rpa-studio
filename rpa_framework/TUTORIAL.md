# RPA Studio - A Friendly Guide

## What is this?

RPA Studio is a robot for your computer. You write a small script that says
"click this, type that, wait for this picture to appear", press Run, and the
robot moves the mouse and keyboard for you - just like a person would, only
faster and without getting bored.

It sees your screen in two different ways, and that is its superpower:

1. It can ask Windows (or Linux) directly: "what button is at this spot, what
   is it called, where exactly is it?" This uses the same accessibility layer
   that screen readers use. It is fast and precise.
2. It can look at the pixels, like a human: you give it a small screenshot of
   a button, and it finds that picture on the screen. It can also read text
   from the screen (OCR).

When one way fails, the other usually works. That is what makes it reliable.

## What can it do?

- Move the mouse, click, double-click, right-click, drag and drop, scroll.
- Type text and press keys (Enter, Tab, Ctrl+S, function keys...).
- Find a button or icon on screen from a screenshot you cropped.
- Wait for something to appear or disappear before continuing.
- Read text straight off the screen with OCR.
- Identify real UI elements (name, type, exact position) under the cursor.
- Start, focus, and close applications.
- Run your existing SikuliX Python scripts, mostly unchanged.
- Everything runs from a friendly editor with Run / Pause / Stop buttons,
  and a script that crashes or loops forever can never freeze the app.
- The whole thing can be compiled into ONE .exe file that runs on a machine
  with nothing installed - no Python, no libraries.

## Quick start (5 minutes)

Open a terminal in the folder that contains `rpa_framework` and run:

    python -m venv .venv
    .venv\Scripts\activate          (Linux/macOS: . .venv/bin/activate)
    pip install -r rpa_framework\requirements.txt
    python -m rpa_framework.ide

The RPA Studio window opens. Now:

1. File > Open Example, pick `hello_flow.py`.
2. Press F5 (or the Run button). Watch the output stream into the Output panel.
3. Press F6 to pause it mid-run, F6 again to resume, Shift+F5 to stop.

That is the whole workflow: open a script, run it, watch it work.

## A tour of the IDE

The window is laid out like VS Code: a tabbed editor in the middle, four
dockable panels around it. Toggle panels from the View menu, drag them where
you like - the layout is remembered for next time.

- **Editor (center)** - Monokai (PyCharm-style) syntax colors, line numbers,
  current-line highlight, Ctrl+mouse-wheel zoom, and autocompletion: after
  two letters a popup suggests every scripting command (click, Pattern,
  waitVanish...), Python keywords, and names already used in your file -
  Enter or Tab accepts. Enter keeps your indentation (plus one level after a
  `:`), Tab always inserts 4 spaces, and the code is syntax-checked as you
  type: a bad line turns its line number red and the exact error shows in the
  status bar. Any line that says `IMAGE: picture.png` shows that picture
  right inside the code. Multiple files open as tabs; unsaved changes show a
  `*` on the tab. Dropping a .py file (or a .sikuli folder) onto the window
  opens it.
- **Explorer (left)** - a file tree of your script's folder; double-click to
  open a file. Right-click to create, rename, delete, copy, and paste files
  and folders (F2 / Del / Ctrl+C / Ctrl+V work too), or to switch to another
  folder. Double-clicking a `.sikuli` folder opens the script inside it, and
  double-clicking an image opens the **Asset Tester**: adjust the similarity
  slider, press "Find on Screen" to test the image live (the mouse hovers the
  match), or insert a ready Pattern line.
- **Element Spy (left, tabbed with Explorer)** - press "Start watching" and
  move the mouse: the real UI element under the cursor (role, name, id, class,
  box, pid) shows live, straight from the OS accessibility tree. One button
  inserts a ready `clickElement(...)` line - or just press **F8** while
  hovering to insert the locator instantly without touching the IDE.
  **Scrape Active Window** waits 3 seconds while you focus the target app,
  then inserts a variable for every named element it finds, with clean
  lowercase names built from the window title and the element label
  (`untitled_notepad_close_button = findElement(...)`). Turkish characters
  are transliterated automatically. Ctrl+Shift+E brings the panel up.
- **Commands (right)** - a searchable list of every scripting command; hover
  for a description, double-click to insert the snippet into the editor.
- **Output (bottom)** - everything your script prints appears live: normal
  output in white, errors in red, status events in green, tool messages in
  yellow.

Tools worth knowing:

- **Run / Pause / Stop (F5 / F6 / Shift+F5)** - your script always runs in a
  separate helper process, so even `while True: pass` cannot freeze the
  window; Stop always works.
- **Capture Image From Screen (Ctrl+Shift+C)** - the window hides for the
  delay shown in the toolbar box (default 2 s - time to set up menus or
  hover states), the screen freezes, and you drag a box around the target.
  While dragging, a **right-click** marks where the click should actually
  land, relative to the selection center. You name the capture (`.png` is
  appended automatically) and a clean
  `click(Pattern("name.png").similar(0.95))` line is inserted - with
  `.targetOffset(x, y)` added if you right-clicked.
- **Draw Target Offset (Ctrl+Shift+T)** - drag a line from a match center to
  the point you want clicked; the measured `.targetOffset(x, y)` is inserted
  at the cursor.
- **Read Screen Text / OCR (Ctrl+Shift+R)** - drag over any screen region and
  the recognized text prints to the Output panel.
- **Insert Region From Screen (Ctrl+Shift+G)** - drag over any screen area and
  a ready `Region(x, y, w, h)` is inserted at the cursor, so you can scope
  searches or read text from exactly that spot.
- **Build Standalone EXE (Tools menu)** - one click starts the Nuitka build
  and streams its progress into the Output panel (enabled when running from
  source).
- **Help menu** - this guide (F1) and the Turkish guide open right inside the
  app.

## Your first script

Create a new file, type this, save it as `my_first.py`, press F5:

    print("watch the mouse!")
    hover(Location(500, 300))
    type("hello robot")

Useful things your scripts can call (no imports needed - they are built in):

| You write                            | The robot does                                    |
|--------------------------------------|---------------------------------------------------|
| `click("save_button.png")`           | finds that picture on screen and clicks it        |
| `click(Location(100, 200))`          | clicks exact screen coordinates                   |
| `doubleClick(...)` `rightClick(...)` | same, other click styles                          |
| `type("hello" + Key.ENTER)`          | types text, then presses Enter                    |
| `type("s", KeyModifier.CTRL)`        | presses Ctrl+S                                    |
| `paste("long text")`                 | pastes via clipboard (fast, safe for any text)    |
| `wait("dialog.png", 10)`             | waits up to 10s for the picture, else fails       |
| `exists("popup.png", 3)`             | like wait, but returns None instead of failing    |
| `waitVanish("spinner.png", 30)`      | waits until the picture disappears                |
| `findAll("checkbox.png")`            | list of every place the picture appears           |
| `dragDrop("file.png", "trash.png")`  | drags the first onto the second                   |
| `wheel(WHEEL_DOWN, 5)`               | scrolls 5 notches down                            |
| `openApp("notepad.exe")`             | starts a program                                  |
| `switchApp("Notepad")`               | brings a window to the front by its title         |
| `findElement(name="OK")`             | finds a real UI element via accessibility         |
| `clickElement(name="OK")`            | finds that UI element and clicks its center       |
| `Region(0, 0, 800, 200).text()`      | reads the text in that screen area (OCR)          |
| `find("label.png").right(150)`       | the area right of a match (also left/above/below) |
| `match.nearby(50)`                   | the match grown by 50px in every direction        |
| `windowRegion("Notepad")`            | a region glued to a window; follows it if moved   |
| `App("Notepad").focus()`             | program handle: .open() .focus() .close() .window() |
| `passed("login ok")`                 | green success line in the Output panel            |
| `failed("button missing")`           | red line + automatic clickable screenshot         |
| `sleep(2)`                           | waits 2 seconds                                   |
| `popup("done!")`                     | shows a message box                               |
| `emit("stage", "login done")`        | sends a green status event to the IDE console     |

Note: Python reserves the words `pass` and would clash with a bare `fail`, so
the helpers are named `passed(...)` and `failed(...)`; the failure screenshot
opens full-size when you click it in the Output panel.

Fine-tuning: `Pattern("btn.png").similar(0.9)` demands a stricter match,
`.targetOffset(20, 0)` clicks 20px right of the found center. `Settings.
MinSimilarity` and `Settings.AutoWaitTimeout` change the defaults.

Long-running scripts: sprinkle `wait_if_paused()` into loops (or
`await checkpoint()` inside `async def main()`) so the IDE Pause button has a
place to take hold. Scripts may define `async def main(): ...` and it will be
awaited automatically.

## Working with images

The easiest way: press Ctrl+Shift+C in the IDE and drag a box around the
target - the crop is saved next to your script and the code is inserted for
you.

To make a picture by hand instead:

1. Put the target on screen (the real button, icon, logo...).
2. Press Win+Shift+S (Snipping Tool), crop tightly around the target.
3. Save the crop as a .png next to your script.
4. Use the file name in your script: `click("my_button.png")`.

Tips: crops with detail (text, edges, corners) match far better than flat
single-color areas. Around 60-200 pixels on a side is the sweet spot. Add a
line `IMAGE: my_button.png` above the code that uses it and the editor shows
the picture inline - those lines are ignored when the script runs.

## Already have SikuliX scripts?

Open the `.py` file from inside your `something.sikuli` folder directly in
RPA Studio and run it. The images sitting next to the script are found
automatically. Supported out of the box: `click, doubleClick, rightClick,
hover, dragDrop, wheel, type, paste, find, findAll, exists, wait, waitVanish,
Pattern (similar / exact / targetOffset), Region, Screen, Location, Match,
Key.*, KeyModifier.*, Settings, setBundlePath, addImagePath, openApp,
switchApp, closeApp, popup, sleep`.

Differences to know about:

- Scripts run on real Python 3, not Jython - modern syntax works, Java
  imports do not.
- Image matching is feature-based (SIFT), not pixel-template based. It is
  robust against scaling and small changes, but `similar(...)` values are
  approximate rather than exact percentages.
- `observe()` / event handlers and `Finder` are not implemented yet.
- `type()` intentionally shadows Python's built-in `type` inside scripts,
  exactly like SikuliX.

## Reading text (OCR)

A Tesseract engine ships with the project in `vendor/tesseract` +
`vendor/tessdata` (English, Turkish, and orientation data included), gets
bundled into the .exe, and is wired up automatically - OCR works out of the
box. In scripts, `Region(...).text()` reads a screen area; `configured_ocr()`
gives you the full engine - `configured_ocr(lang="tur")` reads Turkish, and
word boxes with coordinates come from `read_boxes`. To add more languages,
drop the matching `.traineddata` file into `vendor/tessdata` and rebuild.

## Building the single .exe

    python -m rpa_framework.packaging.build

This compiles everything - Python itself, PyQt6, OpenCV, numpy, and all of
rpa_framework - into `dist\RPAStudio.exe`. Copy that one file to any Windows
machine and it runs; nothing needs to be installed there.

Good to know:

- The first build downloads a C compiler automatically and can take a long
  time (often 30-60 minutes). Later builds are faster thanks to caching.
- Nuitka does not support Python from the Microsoft Store. Use a python.org
  install (or `py -V:3.x` launcher) to create the build environment.
- To also embed OCR, create a `vendor` folder next to `rpa_framework` with
  `vendor\tesseract\tesseract.exe` (plus its DLLs) and `vendor\tessdata\`
  (the .traineddata files). The build picks them up automatically and the
  OCR engine finds them at runtime through `packaging.runtime_paths`.
- Flags: `--dry-run` shows the exact command without building, `--no-onefile`
  builds a folder instead of one file (faster to iterate), `--console` keeps
  a console window for debugging.

## When something goes wrong

- "FindFailed: image not found" - the .png is not next to the script; check
  the name and folder.
- "not found on screen" - crop a bigger, more detailed picture; make sure the
  target is actually visible and not covered.
- "BackendError: ... required" - a pip package is missing; re-run
  `pip install -r rpa_framework\requirements.txt`.
- OCR returns nothing - the `vendor` folder is missing next to `rpa_framework`
  (source runs) or the exe was built without it.
- Clicks land in odd places on multi-monitor setups - put the target app on
  the primary monitor for now.
- Anything else - run `RPAStudio.exe --selftest report.txt` and read the
  report: it probes the backend, the element inspector, screen capture, OCR,
  and the bundled docs/examples, and marks each one ok or fail.

## Under the hood (for future development)

    rpa_framework/
      core/os_facade/   mouse, keyboard, screen capture, windows (per-OS)
      core/vision/      SIFT/ORB image finding + Tesseract OCR
      core/inspector/   accessibility tree access (UIA / AT-SPI) + spy daemon
      compat/           the SikuliX-style scripting API
      ide/              the editor, console, and the safe script runner
      packaging/        the Nuitka build and bundled-resource paths
      examples/         ready-to-run scripts

New OS backends register with `@register_backend`, new inspectors with
`@register_inspector`; factories pick the right one per platform and load
native libraries only on demand, so every module imports everywhere. The
script API is injected in `ide/runner.py` - to give scripts a new built-in
command, add it to `compat/sikuli.py` and its `_EXPORTS`.
