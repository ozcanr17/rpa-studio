# RPA Framework on Linux (RHEL / CentOS 8 and others)

This guide covers running the framework on Linux with **no Python install
required**, using it as an **importable library**, and keeping your existing
**SikuliX `.sikuli` scripts** working. An ASCII Turkish version follows the
English one (see "TURKCE").

---

## 1. Three ways to run on Linux

You can pick whichever fits your closed system. All three share the same
automation engine and the same script commands.

### A. Zero-install headless runner (recommended for servers / closed systems)
A single self-contained binary, `rpa-run`, that runs a script and exits - the
direct replacement for `java -jar sikulix.jar -r test.sikuli`. It bundles its
own Python, OpenCV, and all framework code. No Python, no Java, no pip on the
target machine.

    ./rpa-run test.sikuli
    ./rpa-run test.sikuli --verbose
    ./rpa-run a.sikuli b.sikuli --continue-on-error

### B. Zero-install GUI (RPA Studio)
The full desktop IDE as a single binary (`RPAStudio.bin`) for authoring and
debugging scripts with the visual tools. Needs a graphical desktop session.

### C. Import as a library / run from source
On a machine that has Python 3.8+ you can `import rpa_framework` in your own
code, or run scripts with `python -m rpa_framework test.sikuli`. See section 5.

---

## 2. Your SikuliX scripts keep working

Nothing about your authoring workflow has to change:

- A `.sikuli` folder still holds `name.sikuli/name.py` plus its `.png` images;
  images next to the script are found automatically.
- The same commands are available with no imports: `click, doubleClick,
  rightClick, hover, dragDrop, wheel, type, paste, find, findAll, exists, wait,
  waitVanish, Pattern (.similar/.exact/.targetOffset), Region, Screen, Location,
  Match, Key.*, KeyModifier.*, Settings, openApp, switchApp, closeApp, popup,
  sleep`, plus native-accessibility extras `findElement`, `clickElement`,
  `findUI`, and OCR via `Region(...).text()`.
- Old command:  `java -jar sikulix.jar -r login.sikuli`
  New command:   `rpa-run login.sikuli`   (or `python -m rpa_framework login.sikuli`)

Migration notes (SikuliX/Jython -> this framework):
- Scripts run on **CPython 3**, not Jython. Use `print(...)` (parentheses); Java
  imports (`from java.awt ...`) do not work. Pure-Python SikuliX scripts run
  unchanged.
- Image matching is **feature-based (SIFT)**, robust to scaling and small theme
  changes; `.similar(x)` is an approximate strictness knob, not an exact pixel
  percentage.
- `observe()` / event handlers and `Finder` are not implemented yet.

---

## 3. Building the zero-install binaries on Linux

Nuitka compiles to native code and does **not cross-compile**: build the Linux
binary on a Linux machine (ideally the same RHEL/CentOS 8 you deploy to, so the
glibc/openssl versions match). You only need this build box once; the output
binary is what you copy to the closed system.

Prepare a build machine (RHEL/CentOS 8):

    sudo dnf module install python38          # or python39
    python3.8 -m venv build && . build/bin/activate
    pip install -r rpa_framework/requirements-linux.txt nuitka
    pip install -r rpa_framework/requirements-gui.txt   # only for the GUI build
    sudo dnf install -y patchelf gcc

Build the headless runner (no Qt, small):

    python -m rpa_framework.packaging.build --headless
    # -> dist/rpa-run.bin

Build the GUI (needs PyQt6 + a desktop):

    python -m rpa_framework.packaging.build
    # -> dist/RPAStudio.bin

Notes:
- The first build downloads a C toolchain automatically; it can take a while.
- To embed OCR, drop a portable Tesseract into `vendor/tesseract/` and its data
  into `vendor/tessdata/` before building; they are bundled automatically and
  found at runtime.
- `--no-onefile` produces a folder build (faster to iterate); `--dry-run` prints
  the exact Nuitka command without building.

Copy `dist/rpa-run.bin` to the target, `chmod +x rpa-run.bin`, and run it. No
dependencies are needed on that machine.

---

## 4. What each feature needs (dependency matrix)

The framework degrades gracefully: a missing piece only disables its own
feature and raises a clear error, never an import crash. In the zero-install
binaries everything except the OS session below is already embedded.

- **A graphical session (X11 or Wayland).** GUI automation drives a real
  desktop, so the process must reach a display. On a headless server use a
  virtual display: `sudo dnf install -y xorg-x11-server-Xvfb` then
  `xvfb-run -a rpa-run test.sikuli`.
- **Mouse/keyboard input:** `xdotool` (`sudo dnf install -y xdotool`, EPEL).
- **Native accessibility (findElement/clickElement/Element Spy):** AT-SPI stack
  - `at-spi2-core`, `gobject-introspection`, and PyGObject (`python3-gobject`),
  with accessibility enabled in the session.
- **Computer vision (find/click by image):** OpenCV + numpy (embedded in the
  binaries; `pip` for source use). OpenCV also needs `libGL`
  (`sudo dnf install -y mesa-libGL`).
- **OCR (Region.text()):** a `tesseract` binary plus language data, either
  installed (`sudo dnf install -y tesseract`, EPEL) or bundled via `vendor/`.

You do not need all of these. Native-accessibility automation (AT-SPI + xdotool)
works with no OpenCV/OCR at all; add OpenCV only if you match by image.

---

## 5. Import-only / offline install (closed RHEL/CentOS 8)

If you cannot run an unknown binary but can install a Python package, use the
library path. RHEL 8 ships Python 3.6 by default; install a newer one:

    sudo dnf module install python38

### 5a. Offline wheelhouse (no internet on the target)
On a machine with internet that matches the target (same OS/arch/Python):

    python -m rpa_framework.packaging.offline download ./wheelhouse
    # add --gui to also fetch PyQt6

Copy `./wheelhouse` and the project to the closed system, then:

    python -m rpa_framework.packaging.offline install ./wheelhouse
    pip install --no-index --find-links ./wheelhouse .

### 5b. Plain install (if the target has a package mirror)

    pip install .            # from the folder containing pyproject.toml
    pip install .[gui]       # also install the desktop IDE

This gives you the `rpa-run` command, the `rpa-studio` GUI command, and
`import rpa_framework` in your own Python code:

    import rpa_framework
    rpa_framework.run("test.sikuli")        # returns process exit code

    # or use the API directly
    from rpa_framework.compat.sikuli import Screen, Pattern, Key
    scr = Screen()
    scr.click("button.png")
    scr.type("hello" + Key.ENTER)

### 5c. Source drop, no install
If you may only copy files, put the project folder on `PYTHONPATH` and run the
module form (needs OpenCV/numpy importable for vision features):

    export PYTHONPATH=/opt/rpa
    python3.8 -m rpa_framework test.sikuli

---

## 6. Quick reference

    rpa-run SCRIPT ...        run one or more .sikuli/.py scripts, then exit
      -v, --verbose          also print emit() events
      -c, --continue-on-error keep going if a script fails
      --no-color             plain output (for logs/CI)
      --list                 list every command available inside scripts
      --version              print version

Exit code is 0 when all scripts succeed, non-zero otherwise - suitable for cron,
CI, and shell pipelines.

---

## 7. The GUI binary was built but will not open

Always run it from a terminal first so you can see the real error - do not
double-click:

    ./dist/RPAStudio.bin

Then match the error below.

- **"could not load the Qt platform plugin xcb"** - the target is missing the
  X/Qt runtime libraries. On RHEL/CentOS 8:

        sudo dnf install -y libxkbcommon libxkbcommon-x11 xcb-util xcb-util-image \
          xcb-util-keysyms xcb-util-renderutil xcb-util-wm xcb-util-cursor \
          libX11 libXext libXrender fontconfig freetype mesa-libGL

  (Debian/Ubuntu: `libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0
  libxcb-keysyms1 libxcb-render-util0 libgl1`). To see exactly which library is
  missing: `QT_DEBUG_PLUGINS=1 ./dist/RPAStudio.bin`.

- **Silent exit / "cannot create temporary directory" / "permission denied"** -
  the onefile binary unpacks to a temp folder, and hardened systems mount /tmp
  with `noexec`. The build now unpacks to `~/.cache/RPAStudio` instead. If you
  still hit this, point it somewhere executable at run time:

        NUITKA_ONEFILE_TEMPDIR=$HOME/.rpa-run ./dist/RPAStudio.bin

  or, most robust for closed systems, build a folder instead of onefile (no
  extraction at all):

        python -m rpa_framework.packaging.build --no-onefile
        ./dist/app.dist/RPAStudio.bin

- **"qt.qpa.xcb: could not connect to display" / runs over SSH** - there is no
  graphical session. Run it on the actual desktop, forward X (`ssh -X`), or use
  a virtual display: `xvfb-run -a ./dist/RPAStudio.bin`.

- **"version GLIBC_2.xx not found"** - the build machine is newer than the
  target. Rebuild on a machine whose distro is the same age or older than the
  deployment target (ideally the same RHEL/CentOS 8).

If the GUI still refuses and you only need to run scripts, remember the headless
runner has no Qt at all and needs none of the above: `./dist/rpa-run.bin
test.sikuli`.


## TURKCE - RPA Framework Linux (RHEL / CentOS 8) Kilavuzu

Bu bolum yukaridaki Ingilizce anlatimin Turkce ozetidir. Turkce karakterler
sistem kisitlari nedeniyle ASCII olarak yazilmistir.

### 1. Linux uzerinde uc calistirma yontemi
- **A. Kurulumsuz headless calistirici (`rpa-run`)**: tek dosyalik, kendi
  Python ve OpenCV'sini iceren ikili. `java -jar sikulix.jar -r test.sikuli`
  komutunun dogrudan karsiligi: `./rpa-run test.sikuli`. Hedef makinede Python,
  Java veya pip gerekmez. Kapali sistemler icin onerilir.
- **B. Kurulumsuz arayuz (RPA Studio)**: gorsel IDE'nin tek dosyalik ikilisi
  (`RPAStudio.bin`). Grafik masaustu oturumu gerektirir.
- **C. Kutuphane olarak**: Python 3.8+ olan makinede `import rpa_framework`
  veya `python -m rpa_framework test.sikuli`.

### 2. Mevcut SikuliX betikleriniz aynen calisir
- `.sikuli` klasoru yine `ad.sikuli/ad.py` ve `.png` gorsellerini tutar; yanindaki
  gorseller otomatik bulunur.
- Ayni komutlar importsuz kullanilir: `click, doubleClick, rightClick, hover,
  dragDrop, wheel, type, paste, find, findAll, exists, wait, waitVanish, Pattern,
  Region, Screen, Location, Match, Key.*, KeyModifier.*, Settings, openApp,
  switchApp, closeApp, popup, sleep` ve ek olarak `findElement, clickElement,
  findUI` ile `Region(...).text()` (OCR).
- Eski komut: `java -jar sikulix.jar -r login.sikuli`
  Yeni komut: `rpa-run login.sikuli`
- Onemli farklar: betikler **Jython degil CPython 3** uzerinde calisir;
  `print(...)` kullanin, Java importlari calismaz. Gorsel eslesme SIFT tabanlidir;
  `.similar(x)` yaklasik bir siki-eslesme ayaridir.

### 3. Linux'ta kurulumsuz ikili uretmek
Nuitka capraz derleme yapmaz: Linux ikilisini bir Linux makinede (tercihen ayni
RHEL/CentOS 8) uretin. Cikan ikiliyi kapali sisteme kopyalayin.

    sudo dnf module install python38
    python3.8 -m venv build && . build/bin/activate
    pip install -r rpa_framework/requirements-linux.txt nuitka
    sudo dnf install -y patchelf gcc
    python -m rpa_framework.packaging.build --headless      # -> dist/rpa-run.bin

OCR gomulmesi icin derlemeden once `vendor/tesseract/` ve `vendor/tessdata/`
klasorlerini ekleyin.

### 4. Hangi ozellik neye ihtiyac duyar
- **Grafik oturum (X11/Wayland).** Sunucuda sanal ekran: `xvfb-run -a rpa-run
  test.sikuli`.
- **Fare/klavye:** `xdotool` (EPEL).
- **Yerel erisilebilirlik (findElement/clickElement):** AT-SPI + PyGObject.
- **Gorsel eslesme:** OpenCV + numpy (ikililerde gomuludur); ayrica `mesa-libGL`.
- **OCR:** `tesseract` ikilisi ve dil verisi (kurulu ya da `vendor/` ile gomulu).
Hepsi gerekmez: yalnizca yerel erisilebilirlik ile OpenCV'siz otomasyon mumkundur.

### 5. Cevrimdisi / kurulumsuz kutuphane (kapali RHEL/CentOS 8)
Internetli, hedefle ayni makinede:

    python -m rpa_framework.packaging.offline download ./wheelhouse

`./wheelhouse` klasorunu ve projeyi kapali sisteme kopyalayin:

    python -m rpa_framework.packaging.offline install ./wheelhouse
    pip install --no-index --find-links ./wheelhouse .

Sadece dosya kopyalayabiliyorsaniz `PYTHONPATH` ile:

    export PYTHONPATH=/opt/rpa
    python3.8 -m rpa_framework test.sikuli

Kutuphane kullanimi:

    import rpa_framework
    rpa_framework.run("test.sikuli")

### 6. Hizli komut ozeti
    rpa-run BETIK ...     bir veya daha cok .sikuli/.py betigini calistirir
      -v                  emit() olaylarini da yazar
      -c                  hata olsa da digerlerine devam eder
      --no-color          sade cikti (log/CI icin)
      --list              betik icindeki tum komutlari listeler
Cikis kodu: hepsi basarili ise 0, aksi halde sifirdan farkli.
