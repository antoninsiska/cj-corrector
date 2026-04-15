# CJ Correcter — Czech Grammar Corrector for macOS

> **A native macOS menu bar app that corrects Czech grammar in any application using a local AI model — no internet, no subscriptions, fully offline.**

---

## What it does

CJ Correcter sits in your menu bar and corrects Czech grammar with a single keyboard shortcut. It works in **any app** — browser, email, text editor, Slack, whatever you're typing in. Select your text, press **⌘⇧G**, and a native popup appears with the correction highlighted inline. Accept with **Return**, dismiss with **Escape**.

Everything runs 100% locally on your Mac using the [`ufal/byt5-small-geccc-mate`](https://huggingface.co/ufal/byt5-small-geccc-mate) model — a compact, fast Czech GEC (Grammatical Error Correction) model optimized for real-world Czech text.

---

## Screenshots

### Menu Bar Icon

```
┌─────────────────────────────────────────────────────────────────┐
│  macOS Menu Bar                                    Č✓  ···  🔋  │
│                                              ↑                  │
│                                     CJ Correcter lives here     │
└─────────────────────────────────────────────────────────────────┘
```

While processing, the icon changes to `Č…` so you know it's working.

---

### Correction Popup

```
┌──────────────────────────────────────────────────────────────┐
│  Czech Grammar Correction                                  ✕  │
├──────────────────────────────────────────────────────────────┤
│  🔴 2 mistakes found                                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Já  ~~jdem~~  jdu  do  školy  každy~~í~~  den .           │
│       ^^^^^^                        ^^^^^^^                  │
│    (deleted, red)               (inserted, green bold)       │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                               [ Cancel ]   [ Accept  ↩ ]    │
└──────────────────────────────────────────────────────────────┘
```

The diff view shows:
- **Strikethrough red** — text that was removed
- **Bold green** — corrected replacement
- **Normal** — unchanged text

---

### Menu

```
┌─────────────────────────────────────────┐
│  Model: ufal/byt5-small-geccc-mate      │  (disabled label)
│  Hotkey: ⌘⇧G (works everywhere)        │  (disabled label)
├─────────────────────────────────────────┤
│  Correct Clipboard Text                 │
│  Statistics                             │
├─────────────────────────────────────────┤
│  Quit                              ⌘Q   │
└─────────────────────────────────────────┘
```

---

### Statistics Window

Tracks every mistake you've ever made, how many times, and what the correction was — stored locally in `~/.cj_correcter/mistakes.json`.

---

## How it works

1. You press **⌘⇧G** anywhere on your Mac
2. The app simulates **⌘C** to copy the selected text
3. The text is sent to the local `ufal/byt5-small-geccc-mate` transformer model running via 🤗 Transformers (with Apple Silicon MPS acceleration if available)
4. The model returns the corrected Czech text
5. A native `NSPanel` pops up showing the diff
6. If you press **Accept**, the corrected text is placed in the clipboard and **⌘V** is simulated to paste it back — replacing the original text seamlessly
7. Your mistake is logged to `~/.cj_correcter/mistakes.json` for the Statistics view

---

## Requirements

| Requirement | Version |
|---|---|
| macOS | 12 Monterey or later |
| Python | 3.9+ |
| RAM | ~1 GB free (model loading) |
| Disk | ~400 MB (model cache) |
| Accessibility | Must be granted (for global hotkey & auto-paste) |

> **Apple Silicon (M1/M2/M3):** The model uses MPS acceleration automatically, making inference noticeably faster than on Intel Macs.

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/antoninsiska/cj-corrector.git
cd cj-corrector
```

### 2. Run setup

```bash
bash setup.sh
```

This will:
- Install Python dependencies (`torch`, `transformers`, `pyobjc`, `matplotlib`)
- Download the `ufal/byt5-small-geccc-mate` model (~300 MB, first run only)
- Create the Automator Quick Action (right-click service)
- Create a double-clickable launcher: `Start CJ Correcter.command`

### 3. Grant Accessibility permission

On first launch, macOS will ask for **Accessibility** access. This is required for:
- Listening to the global ⌘⇧G hotkey in any app
- Simulating ⌘C / ⌘V to copy/paste text automatically

Go to **System Settings → Privacy & Security → Accessibility** and enable it for Terminal (or the .app bundle if you're using that).

### 4. Start the app

```bash
python3 app.py
```

Or double-click **`Start CJ Correcter.command`**.

To run at login: **System Settings → General → Login Items → +** and add the `.command` file.

---

## Usage

### Global hotkey (main workflow)

1. Select some Czech text in **any application**
2. Press **⌘⇧G**
3. The menu bar icon briefly shows `Č…`
4. A popup appears with the correction diff
5. Press **Return** (or click Accept) to paste the correction, or **Escape** to cancel

### Clipboard correction

Click the **`Č✓`** icon → **Correct Clipboard Text** to correct whatever is currently in your clipboard.

### Right-click service

After setup, you can also right-click selected text in most apps → **Services → Correct Czech Grammar**.

### Statistics

Click the icon → **Statistics** to see a window with your most frequent mistakes.

---

## Project structure

```
cj-corrector/
├── app.py                  # Main status bar app (NSApplication + NSPanel)
├── ollama_client.py        # Grammar correction engine (HuggingFace Transformers)
├── grammar_correct.py      # CLI wrapper (used by Automator service)
├── create_service.py       # Generates the Automator Quick Action
├── stats_window.py         # Statistics window (matplotlib or AppKit)
├── setup.sh                # One-shot installer
├── Start CJ Correcter.command  # Double-click launcher
└── CJ Correcter.app/       # macOS .app bundle (LSUIElement, no Dock icon)
    └── Contents/
        ├── Info.plist
        └── MacOS/
```

### Key files explained

**`app.py`** — The heart of the app. Uses `pyobjc` to build a native macOS status bar app with `NSStatusBar`, a global hotkey monitor via `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_`, and a custom `NSPanel` for the correction popup. The panel uses `NSWindowCollectionBehaviorCanJoinAllSpaces` so it appears above full-screen apps too.

**`ollama_client.py`** — Loads `ufal/byt5-small-geccc-mate` via 🤗 Transformers. Exposes `correct_czech(text) → dict` returning `{corrected: str, mistakes: list}`. The model is cached after first load (per process). Uses MPS on Apple Silicon automatically.

**`grammar_correct.py`** — A thin subprocess-safe wrapper around `ollama_client.py` for use in Automator services where each invocation is a fresh process.

**`create_service.py`** — Programmatically creates the Automator `.workflow` bundle in `~/Library/Services/`.

**`stats_window.py`** — Reads `~/.cj_correcter/mistakes.json` and displays a ranked list of your grammar mistakes.

---

## The model: `ufal/byt5-small-geccc-mate`

| Property | Value |
|---|---|
| Architecture | ByT5 (byte-level T5) |
| Task | Czech Grammatical Error Correction |
| Source | [ÚFAL, Charles University Prague](https://ufal.mff.cuni.cz/) |
| Size | ~300 MB |
| Input | Space-tokenized Czech text |
| HuggingFace | [ufal/byt5-small-geccc-mate](https://huggingface.co/ufal/byt5-small-geccc-mate) |

The model was trained on the [GECCC corpus](https://lindat.mff.cuni.cz/repository/xmlui/handle/11234/1-4639) — a large Czech GEC dataset containing texts from native speakers, language learners, and OCR output.

> **Privacy:** Your text never leaves your machine. There are no API calls, no telemetry, no cloud.

---

## Troubleshooting

**Popup doesn't appear / hotkey doesn't work**
→ Check Accessibility permissions: System Settings → Privacy & Security → Accessibility

**`ModuleNotFoundError: No module named 'AppKit'`**
→ Run `pip3 install pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices`

**Model takes a long time on first correction**
→ The model loads into memory on first use (~5–10 sec). Subsequent corrections are much faster.

**`PYTORCH_ENABLE_MPS_FALLBACK` warnings**
→ These are suppressed in the app. On Intel Macs the model falls back to CPU automatically.

**Text not pasted after Accept**
→ The app simulates ⌘V via AppleScript. Make sure the target app is focused and accepts paste. In rare cases (e.g., password fields) pasting is blocked by the OS.

---

## Data & privacy

- Correction history is stored in `~/.cj_correcter/mistakes.json`
- No data is ever sent anywhere — completely offline
- To wipe history: `rm ~/.cj_correcter/mistakes.json`

---

## License

MIT — do whatever you want with it.

---

*Built with [ufal/byt5-small-geccc-mate](https://huggingface.co/ufal/byt5-small-geccc-mate) · [pyobjc](https://pyobjc.readthedocs.io/) · 🤗 [Transformers](https://huggingface.co/docs/transformers)*
