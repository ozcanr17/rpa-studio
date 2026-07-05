# Building and Releasing RPA Studio

One page for every artifact this repository produces. All builds are
zero-install on the target machine: nothing to `pip install`, no Python, no
Java, no OpenCV, no Tesseract required.

## Artifacts

| Artifact | Platform | Built with | Entry |
|---|---|---|---|
| `dist/RPAStudio.exe` | Windows | `scripts/build_windows.ps1` | full IDE, onefile |
| `dist/rpa-studio-linux.tar.gz` | Linux | `scripts/build_linux.sh` | full IDE, standalone folder + `run.sh` |
| `dist/rpa-run.bin` | Linux | `scripts/build_linux.sh headless` | headless script runner, no Qt |
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

Flags: `-NoOnefile` (fast folder build), `-Console` (keep a console for
debugging), `-DryRun` (print the Nuitka command), `-Headless` (build
`rpa-run.exe` instead of the IDE), `-SkipSelftest`.

## Linux (RHEL / CentOS 8 and others)

One-time setup:

    sudo dnf install -y patchelf gcc
    python3 -m venv build && . build/bin/activate
    pip install -r rpa_framework/requirements-linux.txt nuitka
    pip install -r rpa_framework/requirements-gui.txt   # GUI build only

Build:

    scripts/build_linux.sh            # GUI -> dist/rpa-studio-linux.tar.gz
    scripts/build_linux.sh headless   # runner -> dist/rpa-run.bin

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
- `vendor/icons/`, `vendor/logo2.png` - branding (already in the repo)

Check the Nuitka log for `Included data file` lines when touching bundled
data; `--include-data-dir` silently skips `.py`/`.exe`/`.dll` files, which is
why the build uses `--include-raw-dir` for those.

## Release checklist

1. All tests green, constraint checker green.
2. Build the platform artifact with the script above (selftest must pass).
3. Tag and publish:
   - Windows: tag `windows-vX.Y.Z`, attach `dist/RPAStudio.exe`.
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
