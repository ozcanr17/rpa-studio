# Building and Releasing RPA Studio

One page for every artifact this repository produces. All builds are
zero-install on the target machine: nothing to `pip install`, no Python, no
Java, no OpenCV, no Tesseract required.

## Artifacts

All artifacts are now portable standalone FOLDERS (no onefile): everything the
app needs, including onnxruntime and any `.dll`/`.so` shared libraries, ships
inside the folder, so a fresh air-gapped Windows or Linux machine runs it with
zero installs.

| Artifact | Platform | Built with | Entry |
|---|---|---|---|
| `dist/rpa-studio-windows/` + `.zip` | Windows | `scripts/build_windows.ps1` | full IDE folder, `RPAStudio.exe` inside |
| `dist/rpa-run-windows/` | Windows | `scripts/build_windows.ps1 -Headless` | headless runner folder, `rpa-run.exe` inside |
| `dist/rpa-studio-linux/` + `.tar.gz` | Linux | `scripts/build_linux.sh` | full IDE folder + `run.sh` |
| `dist/rpa-run-linux/` + `.tar.gz` | Linux | `scripts/build_linux.sh headless` | headless runner folder, no Qt |
| pip package `rpa-framework` | any | `pip install .` | library + `rpa-run` + `rpa-studio` commands |

Nuitka does not cross-compile: build Windows artifacts on Windows and Linux
artifacts on Linux (ideally the same RHEL/CentOS 8 you deploy to, so glibc
matches).

## Windows

One-time setup (python.org CPython required - Microsoft Store Python cannot
link with Nuitka):

    py -V:3.14 -m venv .venv-build
    .venv-build\Scripts\pip install -r rpa_framework\requirements.txt nuitka

Build + verify (runs the compiled exe's `--selftest` automatically):

    powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1

The result is the portable folder `dist\rpa-studio-windows\` plus a zip of it.
Flags: `-Console` (keep a console for debugging), `-DryRun` (print the Nuitka
command), `-Headless` (build the `rpa-run.exe` folder instead of the IDE),
`-SkipSelftest`, `-NoZip`.

## Linux (RHEL / CentOS 8 and others)

One-time setup:

    sudo dnf install -y patchelf gcc
    python3 -m venv build && . build/bin/activate
    pip install -r rpa_framework/requirements-linux.txt nuitka
    pip install -r rpa_framework/requirements-gui.txt   # GUI build only

Build:

    scripts/build_linux.sh            # GUI -> dist/rpa-studio-linux/ + .tar.gz
    scripts/build_linux.sh headless   # runner -> dist/rpa-run-linux/ + .tar.gz

Target-machine notes, dependency matrix, and troubleshooting live in
`rpa_framework/LINUX.md`.

## Library use inside existing SikuliX projects

Install (online or from an offline wheelhouse, see
`rpa_framework/packaging/offline.py` and LINUX.md section 5):

    pip install .          # engine only
    pip install .[gui]     # engine + desktop IDE

Then either of these runs a .sikuli folder unchanged:

    rpa-run login.sikuli

    import rpa_framework
    rpa_framework.run("login.sikuli")

Direct API access:

    from rpa_framework.compat.sikuli import Screen, Pattern, Key
    from rpa_framework.core import OSFacadeFactory, InspectorFactory

## Bundled data (optional but recommended before building)

Drop these next to `rpa_framework/` before building and they are embedded
automatically:

- `vendor/tesseract/` - portable Tesseract binary + DLLs (enables OCR)
- `vendor/tessdata/`  - language data (`eng`, `tur`, ...)
- `vendor/models/`    - AI vision: a YOLO-format `.onnx` UI detection model
  (e.g. `ui_detect.onnx`) plus an optional `<model>.labels` class list; enables
  semantic `findUI` and the `ui` anchor fallback fully offline
- `vendor/icons/`, `vendor/logo2.png` - branding (already in the repo)

onnxruntime is bundled automatically when it is installed in the build venv
(`--include-package` + `--include-package-data`); after the build,
`packaging/build.py copy_native_libs` copies any `onnxruntime/capi` shared
libraries the Nuitka scan missed into the dist folder (`.dll` on Windows,
`.so*` on Linux).

On Linux, `packaging/build.py bundle_linux_libs` then makes the folder fully
self-contained: it copies the dlopen'ed xcb family Qt 6.5+ needs at run time
(`libxcb-cursor.so.0` and friends - invisible to dependency scanners, which is
why linux-v1.0.0 failed on clean machines) plus every other externally
resolved `.so`, excluding only glibc and GPU drivers which must come from the
target OS. The staged folder gets a `run.sh` (exports `LD_LIBRARY_PATH`, picks
wayland when there is no X11) and a `diagnose.sh` (run it on the target to
list any library that still fails to resolve). Watch the build output for
`linux-libs: MISSING on build machine:` lines - install those packages on the
BUILD machine and rebuild, or the bundle will not be complete.

Check the Nuitka log for `Included data file` lines when touching bundled
data; `--include-data-dir` silently skips `.py`/`.exe`/`.dll` files, which is
why the build uses `--include-raw-dir` for those.

## Release checklist

1. All tests green, constraint checker green.
2. Build the platform artifact with the script above (selftest must pass).
3. Tag and publish:
   - Windows: tag `windows-vX.Y.Z`, attach `dist/rpa-studio-windows.zip`.
   - Linux: tag `linux-vX.Y.Z`, attach `dist/rpa-studio-linux.tar.gz`.
4. Keep `version` in `pyproject.toml` and `rpa_framework/__init__.py` in sync.

## Repository layout

    rpa_framework/      the installable package (library + IDE + packaging)
      core/             OS facade, vision, OCR, accessibility inspectors
      compat/           SikuliX-compatible scripting API
      ide/              PyQt6/PySide6 IDE (RPA Studio)
      packaging/        Nuitka build pipeline, runtime paths, offline wheelhouse
      examples/         runnable sample scripts
    scripts/            one-command platform builds
    vendor/             bundled binaries/data (tesseract, tessdata, icons, logo)
    dist/               build output (not committed)
    pyproject.toml      pip packaging (library install)
