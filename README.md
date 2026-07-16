# iSTranslater

A lightweight, **headless** Windows tool that translates whatever text you have selected in *any*
application, using the OpenAI API (or any OpenAI-compatible endpoint). It runs as a background
process — **no window, no taskbar entry, no tray icon** — driven entirely by global hotkeys.

## What it does

- **Double-tap Ctrl** — translate the current selection into **Language 1** and show it in a
  floating overlay tooltip near the cursor (non-destructive).
- **Ctrl + '** — translate the current selection into **Language 2** and paste it back **over the
  selection** in the focused input field.

## How it works

There is no universal OS API to read another app's selected text, so the tool:

1. Synthesizes **Ctrl+C** (Windows `SendInput`) to copy the selection, and detects the copy via the
   clipboard sequence number.
2. Sends it to the model for translation (`reasoning_effort=minimal` + `verbosity=low` for speed).
3. Either shows the result (overlay) or sets the clipboard and synthesizes **Ctrl+V** (replace).

The original clipboard is restored after a replace. There is **no UI** — errors go only to the log.

## Configuration

All config comes from defaults + a `.env` file (there is no settings screen). Create `.env` in the
project root (or next to the built `.exe`):

```
OPENAI_API_KEY=sk-...
# optional overrides:
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-5-nano
```

`.env` is gitignored. Defaults: Language 1 = English, Language 2 = Chinese (Simplified),
model = `gpt-5-nano`, translate = `double-ctrl`, replace = `ctrl+'`. To change languages/hotkeys,
edit `DEFAULTS` in [translator/config.py](translator/config.py) (or set a `~/.istranslater/config.json`).
Set `hotkey_translate` to a combo like `ctrl+;` instead of `double-ctrl` for a normal hotkey.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

Nothing visible appears — it's a background process. Stop it from **Task Manager**.

## Build a standalone exe

```powershell
pip install pyinstaller
./build.ps1
```

Produces `dist\istranslator.exe` — a single, windowless executable with the 文A app icon
(shown in Task Manager). The `.env` present at build time is **bundled inside the exe**, so it
runs self-contained with no external files.

> **Security:** the API key is baked into the exe and can be extracted from it — keep the exe
> private, don't share it. To change the key without rebuilding, drop an external `.env` next to
> the exe; it overrides the bundled one.

## Logs

- `~/.istranslater/istranslater.log` — activity and errors
- `~/.istranslater/crash.log` — native crashes (faulthandler)

## Notes & limitations

- Global hotkeys and key synthesis use the native Windows API (`RegisterHotKey`, a passive
  `WH_KEYBOARD_LL` hook for double-tap Ctrl, and `SendInput`). If hotkeys don't fire, run the exe
  with the same privilege level as your target app.
- Selection capture relies on Ctrl+C, so it only works where copy works.
- The replace action pastes over the selection; with nothing selected it pastes at the caret.
