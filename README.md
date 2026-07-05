<div align="center">

# 🎯 RPA Studio

### The Zero-Installation, Portable IDE for Ultra-Reliable Desktop Automation

*One executable. No installers. No dependencies. Just automation that survives the real world.*

<!-- Status Badges — replace the placeholder targets with your CI / registry URLs -->
[![Build](https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge)](#)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=for-the-badge)](#)
[![SikuliX](https://img.shields.io/badge/SikuliX-compatible-orange?style=for-the-badge)](#)

</div>

---

## What is RPA Studio?

**RPA Studio** is an enterprise-grade, **standalone IDE and automation framework** that packages its entire runtime, dependency tree, and user interface into a **single, high-performance executable** — `RPAStudio.exe`. It runs natively with **no MSI installer**, **no `.NET`/Java prerequisites**, **no registry edits**, and **no administrative privileges**.

It speaks the **SikuliX API syntax** you already know (`click()`, `type()`, `find()`, `wait()`, `findText()`), but backs it with a **Dual-Layer Locator Architecture** that keeps scripts running when screen resolutions change, themes flip to dark mode, or the target app refuses to expose an accessibility model.

> **Built for the hard environments.** Air-gapped labs, locked-down corporate workstations, and virtualized Citrix/RDP sessions are exactly where RPA Studio shines — precisely where traditional RPA tooling falls apart. And because every script runs in a **separate process**, a crashed or runaway script never freezes the IDE.

---

## 🧠 Why RPA Studio? — Plan A *and* Plan B, Always

Most automation tools gamble everything on a single locator strategy. When it breaks, your script breaks. RPA Studio runs a **fail-safe primary layer** with a **computer-vision fallback** that activates transparently — so there is always a Plan B.

| | **🅰️ Layer 1 — Accessibility Tree** *(Primary)* | **🅱️ Layer 2 — Vision + OCR** *(Fallback)* |
|---|---|---|
| **How it targets** | Programmatic properties: `AutomationID`, Control Type, Name | Visual features, edges & on-screen text |
| **Engine** | Windows **UIA** · Linux **AT-SPI** | **SIFT** matching + **Tesseract OCR** |
| **Resolution / DPI** | ✅ Fully agnostic | ✅ `0.5×–3×` multi-scale pyramid scan |
| **Theme (Light/Dark)** | ✅ Unaffected | ✅ Edge-map + **CLAHE** resilient |
| **Best for** | Modern, accessible apps | Legacy Delphi, Java Applets, canvas, Citrix/RDP |
| **When it fires** | First — the default path | Automatically, when Layer 1 is blocked |

> **The key insight:** Layer 2 is *not* fragile pixel-matching. It runs a multi-stage vision pipeline — grayscale + **CLAHE** normalization → structural **edge mapping** → **SIFT** keypoint extraction → **0.5×–3×** pyramid scaling → **Tesseract OCR** text anchoring. Re-theming, shadow shifts, and DPI changes don't stop it.

---

## ✨ Key Features

- **🖥️ Truly Cross-Platform** — Native Windows (UIA) and Linux (AT-SPI) targeting from the same script.
- **🔌 SikuliX-Compatible** — Drop-in familiar syntax: `click()`, `type()`, `find()`, `wait()`, `findText()`, `exists()`, `Pattern`, `Region`.
- **🔎 Element Spy & Window Spy** — Hover any control, **right-click**, and RPA Studio writes window-locked, resolution-proof locator code for you.
- **📖 Built-in OCR Engine** — Embedded Tesseract (`eng`, `eng_best`, `tur`, `dejavu_sans`) for content validation and text-anchor clicks — no external install. Search on-screen text with `findText`, `findWord`, `findLine`, `findWords`, and the `OCR` class.
- **👀 Event Observation** — `onAppear` / `onVanish` / `onChange` handlers with blocking or background `observe()`, plus `Finder` for searching inside saved images.
- **📦 Single-File Portability** — Copy one binary to deploy; delete one binary to decommission. No "DLL Hell."
- **🛡️ Environment Isolation** — Runs from memory or a self-contained directory; never drops shared libraries into `System32` or `/usr/lib`.
- **🧩 Full IDE** — Monokai editor with live syntax checking, autocomplete, capture tools, `.sikuli` folder support, integrated terminal, and pause/stop controls.

---

## 🚀 Quick Start

1. Run **`RPAStudio.exe`** (first launch takes ~15–20 s while modules unpack).
2. Open an example from **`File > Open Example`**, then press **▶ Run** (`Ctrl+3`).
3. Pause with **`Ctrl+4`**, stop with **`Ctrl+5`**. Live output streams in the **Output** panel.

A minimal dual-layer automation looks like this:

```python
# RPA Studio — Minimal Example (SikuliX-compatible syntax)
Settings.MinSimilarity = 0.75      # Layer 2 vision tolerance
setBundlePath("./assets/")         # where the .png targets live

def run():
    # Layer 1 (Accessibility Tree) tries first;
    # Layer 2 (SIFT + CLAHE + OCR) triggers automatically if the element isn't exposed.
    if exists("username_field"):
        click("username_field")
        type("username_field", "enterprise_user")
        type("password_field", "SecurePassword123")
        click("submit_button")
    else:
        # Text-anchor fallback via Tesseract OCR
        click(findText("GIRIS YAP"))

if __name__ == "__main__":
    run()
```

Prefer the command line? Run from source with `python -m rpa_framework.ide`.

> **⚠️ Character-set rule:** Keep asset names, variables, and identifiers in **standard English characters**. Replace `ı ş ğ ç ö ü` with `i s g c o u`. This isolates scripts from code-page mismatches (Windows-1254 vs. UTF-8) that crash automation on restricted infrastructure. Full mapping in the [reference manual](KILAVUZ.md).

---

## 📚 Repository Navigation

| Document | Language | Description |
|---|---|---|
| **[📘 KILAVUZ.md](KILAVUZ.md)** | 🇹🇷 Türkçe | Definitive reference manual — architecture deep-dive, portable model, spying & coding rules, full API reference. |
| **[📗 TUTORIAL.md](TUTORIAL.md)** | 🇬🇧 English | Hands-on, step-by-step workbook from first launch to a complete end-to-end macro. |

---

## 🗂️ Project Layout

```
rpa_framework/
  core/os_facade/    mouse · keyboard · screen  (win32 + pywinauto / xdotool + mss)
  core/vision/       SIFT matching, edge maps, UI locator, OCR engine
  core/inspector/    UIA / AT-SPI accessibility tree & spy service
  compat/sikuli.py   the scripting API used throughout the docs
  ide/               editor, panels, run engine (separate process)
  packaging/         Nuitka single-file builder
```

Build the portable binary via **`Tools > Build Standalone EXE`**, the one-command
`scripts\build_windows.ps1` (Windows) / `scripts/build_linux.sh` (Linux), or
`.venv-build\Scripts\python.exe -m rpa_framework.packaging.build` → outputs `dist/RPAStudio.exe`, which runs on a clean machine with no Python, OpenCV, or Tesseract installed. Prebuilt Windows and Linux binaries are on the [Releases](https://github.com/ozcanr17/rpa-studio/releases) page. Full build matrix and library-install steps are in [BUILDING.md](BUILDING.md).

---

<div align="center">

**RPA Studio** · Portable IDE · Dual-Layer Locator Engine · SikuliX-Compatible

<sub>Automation that survives resolution changes, theme shifts, and legacy UIs.</sub>

</div>
