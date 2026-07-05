<div align="center">

# 📗 RPA Studio — Hands-On Tutorial

### From First Launch to Your First End-to-End Macro

*A friendly, step-by-step workbook. No prior RPA experience required.*

</div>

---

## What You'll Build

By the end of this tutorial you will have written a **robust, cross-platform login macro** that:

- Targets UI elements through the **Accessibility Tree** (the fast, reliable primary path).
- **Falls back to computer vision + OCR** automatically when an app hides its accessibility model.
- Survives **resolution changes, dark-mode switches, and legacy UIs** — and reports failures clearly.

> New here? Skim the [README](README.md) for the big picture, and keep [KILAVUZ.md](KILAVUZ.md) open as your full API reference.

---

## Prerequisites & Launching the IDE

You need **nothing installed** — that's the whole point.

1. Copy **`RPAStudio.exe`** anywhere: a USB stick, a network share, your Desktop. No admin rights required.
2. Double-click it. The **first launch takes ~15–20 seconds** while modules unpack into memory.
3. You'll land in the IDE: **Explorer** on the left, the Monokai **editor** in the center, and a tabbed panel group (**Output · Terminal · Element Spy · Window Spy**) at the bottom.

> 💡 Running from source instead? Use `python -m rpa_framework.ide`.

Create a new script with **`Ctrl+N`**, save it with **`Ctrl+S`**, and run it any time with **▶ Run** (`Ctrl+^`). Pause with **`Ctrl+4`**, stop with **`Ctrl+5`**.

---

## Step 1 — Your First Script via the Accessibility Tree (Primary Path)

The primary path targets elements by their **programmatic identity** — not their pixels — so it's immune to theme and resolution changes. Let's capture a real control instead of typing selectors by hand.

**1. Open Element Spy** (`Ctrl+Shift+E`) and click **Start watching**.

**2. Hover** over any button in a target app (try a text editor's *Save* button), then press **Space**. RPA Studio writes window-locked locator code for you:

```python
save_btn = findElement(name="Save", role="Button", window="Notepad")
save_btn.click()
```

**3.** Notice the element is **locked to its window** — it will never be matched in some other app by accident.

Now let's assemble a small script. Type or capture the following:

```python
# step1_login.py — Accessibility Tree (Primary Path)

def run():
    username = findElement(name="Username", role="Edit", window="MyApp")
    username.setText("enterprise_user")

    password = findElement(name="Password", role="Edit", window="MyApp")
    password.setText("SecurePassword123")

    findElement(name="Sign In", role="Button", window="MyApp").click()
    passed("Login submitted via accessibility tree")

if __name__ == "__main__":
    run()
```

Press **▶ Run**. Watch the **Output** panel stream live results — a green line means success.

> ✅ **Why this is the preferred path:** `findElement` reads the UIA (Windows) / AT-SPI (Linux) tree. It doesn't care if the app is in dark mode, on a 4K display, or scaled to 150% DPI. Reach for it *first*, every time.

---

## Step 2 — Handling Legacy UIs with the SIFT + OCR Fallback

Some apps — Delphi thick clients, raw Java Applets, canvas panels, or **Citrix/RDP** sessions — expose *no* accessibility model. `findElement` can't see them. This is where **Layer 2** earns its keep.

You don't switch modes manually — image and OCR commands *are* the fallback layer. Let's tune it.

### 2a. Capture a target image

Use **Capture Image** (`Ctrl+1` instant, or `Ctrl+2` delayed), drag a box around the control, right-click to mark the click point, and confirm with **Space**. Type only a variable name; the image saves as `variable.png` next to your script:

```python
login_btn = Pattern("login_btn.png").similar(0.90)
click(login_btn)
```

### 2b. Adjust matching thresholds

The single most important dial is **similarity** — how close a match must be (0.0–1.0):

```python
Settings.MinSimilarity = 0.75      # global default

# Too many false matches?  Raise it:
strict = Pattern("login_btn.png").similar(0.92)

# Target not found on a re-themed / re-rendered screen?  Lower it:
loose  = Pattern("login_btn.png").similar(0.65)
```

> 🎯 **Rule of thumb:** start at `0.75`. If it clicks the *wrong* thing, raise toward `0.90+`. If it finds *nothing*, lower toward `0.65`. The **Asset Tester** (double-click any image in Explorer) lets you slide the threshold and preview the match on screen before committing.

### 2c. Multi-scale scans & CLAHE — already working for you

The fallback pipeline handles DPI and theme differences automatically:

- **`0.5×–3×` pyramid scan** resizes your captured asset across scales, so a button captured at 100% DPI still matches at 150% or 200%.
- **CLAHE + edge mapping** neutralize dramatic lighting/shadow shifts and survive app re-theming — the match is based on *structure*, not color.

You rarely touch these directly; just capture at a normal DPI and let the pyramid do the work. If matches are marginal, capture a **tighter, higher-contrast** region.

### 2d. Read text with OCR

When even an image is unreliable, anchor on **text**. The embedded Tesseract engine reads straight from the screen:

```python
Settings.OcrLanguage = "eng_best"      # highest accuracy; use "tur" for Turkish
click(findText("SIGN IN"))             # find the words, click them

# Validate content in a region:
banner = Region(0, 0, 600, 120).text()
if "Welcome" in banner:
    passed("Login confirmed by OCR")
```

Putting the fallback layer together:

```python
# step2_login_fallback.py — Vision + OCR (Fallback Path)
Settings.MinSimilarity = 0.75
Settings.OcrLanguage   = "eng_best"

def run():
    type("username_field", "enterprise_user")   # image-anchored
    type("password_field", "SecurePassword123")
    if exists("submit_button", 3):              # returns None (no crash) if absent
        click("submit_button")
    else:
        click(findText("SIGN IN"))              # OCR text-anchor as last resort
    passed("Legacy login submitted")

if __name__ == "__main__":
    run()
```

---

## Step 3 — Robust, Cross-Platform Best Practices

### Combine both layers with `Target`

The most resilient pattern doesn't choose a layer — it declares all three and lets RPA Studio pick the winner, then **remembers** which one worked:

```python
sign_in = Target(name="Sign In", window="MyApp",
                 image="login_btn.png", text="SIGN IN")
sign_in.click()   # tries element → image → OCR, in that order
```

Use this for any mission-critical step that must run across mixed Windows/Linux fleets or VDI sessions.

### The character-mapping workflow (do this every time)

> ⚠️ **Critical rule:** All **code identifiers** — file names, variables, `Pattern`/asset names — must use **standard English characters only**. This isolates your scripts from code-page mismatches (Windows-1254 vs. UTF-8) that crash automation on locked-down systems.

Map Turkish characters to their English equivalents in identifiers:

| Turkish | English | | Turkish | English |
|:---:|:---:|---|:---:|:---:|
| `ı / İ` | `i / I` | | `ç / Ç` | `c / C` |
| `ş / Ş` | `s / S` | | `ö / Ö` | `o / O` |
| `ğ / Ğ` | `g / G` | | `ü / Ü` | `u / U` |

```python
# ❌ Fragile on restricted infrastructure:
click("çıkış_düğmesi")

# ✅ Portable everywhere:
click("cikis_dugmesi")
```

Note the *data you type* into a field can stay Turkish — only the identifiers must be ASCII:

```python
type("mesaj_alani", "Merhaba, hoş geldiniz")   # value is fine; name is ASCII
```

### Bound the search area for speed and safety

Restricting a search to a `Region` makes it faster *and* prevents matching a look-alike elsewhere on screen:

```python
toolbar = Region(0, 0, 1920, 80)
toolbar.find("save.png").highlight(1)
```

---

## Step 4 — Putting It All Together

Here's a complete, defensive end-to-end macro that launches an app, logs in through whichever layer works, verifies the result, and reports clearly:

```python
# e2e_login.py — complete cross-platform macro
Settings.MinSimilarity = 0.75
Settings.OcrLanguage   = "eng_best"
Settings.ClickDelay    = 0.2

def run():
    app = openApp("myapp.exe")          # launches, tracks PID, waits for window
    app.window().moveTo(0, 0)

    # Declare a triple-anchor target: element → image → OCR
    user = Target(name="Username", window="MyApp",
                  image="username_field.png", text="Username")
    user.setText("enterprise_user")

    type("password_field", "SecurePassword123")

    sign_in = Target(name="Sign In", window="MyApp",
                     image="login_btn.png", text="SIGN IN")
    sign_in.click()

    # Verify with OCR
    if "Welcome" in Region(0, 0, 800, 200).text():
        passed("End-to-end login succeeded")
    else:
        failed("Login page did not confirm success")

if __name__ == "__main__":
    run()
```

Run it, then flip your OS to dark mode and change your display scaling — it should still pass. That's the dual-layer promise.

---

## Troubleshooting — Common Edge Cases

| Symptom | Likely Cause | Fix |
|---|---|---|
| **`FindFailed: image not found`** | Asset `.png` isn't next to the script, or name typo | Save the capture beside your script; check the file name in Explorer. |
| Clicks the **wrong** element | Similarity too low | Raise `Pattern(...).similar(0.90+)`; capture a tighter, distinctive region. |
| Target **not found** after re-theme / DPI change | Similarity too strict, or color-dependent capture | Lower to `~0.65`; rely on edge-map fallback; re-capture at normal DPI. |
| `findElement` returns nothing | App exposes **no accessibility tree** (legacy/VDI) | Switch to image/`findText`, or use a `Target(...)` triple anchor. |
| OCR misreads text | Wrong language model or tiny text | Set `Settings.OcrLanguage` (`eng_best` / `tur`); OCR auto-upscales, but capture a larger region if needed. |
| **Encoding / runtime error** on a corporate machine | Turkish characters in identifiers | Apply the [character-mapping workflow](#the-character-mapping-workflow-do-this-every-time). |
| App window won't focus (Turkish title) | Title differs by locale | Use `openApp(...)` / `switchApp("process_name")` — it tracks by **PID and process name**, not title. |
| Script seems frozen | It's paused, not crashed | Press **`Ctrl+4`** to resume, or **`Ctrl+5`** to stop. Scripts run in a **separate process**, so the IDE never locks up. |

> 🧭 **Debugging tip:** Every failure drops a **screenshot and line number** into the Output panel. Read that first — it usually tells you exactly what the engine saw (or didn't) at the moment of failure.

---

<div align="center">

**You're ready.** Capture, script, run — and let the fallback layer catch the hard cases.

[README.md](README.md) · [KILAVUZ.md](KILAVUZ.md)

</div>
