# Fortnite Macro Recorder

A lightweight background macro tool you run **overtop Fortnite** (or any other
game). Press a key to record; it gives you a **3-beep countdown ending on a
spoken "GO"**, then captures your **exact mouse movements, clicks, scrolls and
keystrokes with precise timing**. Press the key again and it plays
**"recording stopped"**. Replay the sequence any time, and dial the speed
up or down by a **single percentage** that scales every interval uniformly so
the mouse and keyboard stay perfectly in proportion.

> ⚠️ **Use responsibly.** Automating input in online competitive games can
> violate their Terms of Service / anti-cheat rules. This is intended for your
> own machine, for practice and training. Use at your own risk.

---

## What it does

- **Record hotkey** (default `F8`) → 3-beep countdown, final beep speaks **"GO"**,
  recording begins on "GO".
- Captures **every** mouse move, click, scroll, key-down and key-up with a
  high-resolution timestamp (`time.perf_counter`) so playback replicates exactly
  what you did, with the same timing.
- Press the record hotkey **again** to stop → plays **"recording stopped"**.
- **Play hotkey** (default `F9`) replays the last recording. Press again to stop.
- **Speed control**: one percentage (`interval_percent`) is multiplied into every
  recorded interval, so mouse and keyboard scale together and stay in sync:
  - `100%` = original speed
  - `50%`  = half the time between events → **2× faster**
  - `200%` = double the time between events → **half speed**
  - Adjust live with `[` (slower) and `]` (faster), in 10% steps.
- **Save / Load** a recording to `macro.json` (`F7` / `F6`).

---

## Install

Requires **Python 3.8+**.

```bash
pip install -r requirements.txt
```

- `pynput` is required (input capture + playback).
- `pyttsx3` is optional — it provides the spoken "GO" and "recording stopped".
  Without it the tool falls back to distinctive beeps.
- On **Windows** the countdown beeps use the built-in `winsound` (no extra
  install). The voice cues use your system's installed TTS voices via `pyttsx3`.

---

## Run

**GUI (recommended)** — a dark, Razer-Synapse-style control panel:

```bash
python macro_gui.py
```

Nothing is pre-set: click any key-cap and press the key you want to bind it
(record, play, slower, faster, save, load, quit). Big RECORD / PLAY toggles
light up while active, a speed slider scales playback, and there's a live
activity log plus Save / Load buttons.

**Multiple macro slots, each with its own key and hold-to-repeat:**

- Use **MACRO SLOTS** to add / rename / remove as many macros as you like.
- The selected slot is the one **RECORD** captures into.
- Give each slot its own **trigger key** (click `TRIGGER KEY`, press a key).
- Toggle **HOLD TO REPEAT** per slot:
  - **ON**  → hold the trigger key and the macro loops until you let go.
  - **OFF** → tap the trigger key to play the macro once.
- `SAVE ALL… / LOAD…` save and restore your whole workspace (every slot,
  trigger and setting) to one `.json` file.

**Console (no window)** — same engine, hotkey-only:

```bash
python fortnite_macro.py
```

Leave either one running in the background and tab into Fortnite.

> **Tip (Windows):** Fortnite usually runs as administrator. For the macro to
> send input into it, run the script from an **administrator** terminal too,
> otherwise replayed input may be ignored by the game window.

---

## Hotkeys

| Key   | Action                                             |
|-------|----------------------------------------------------|
| `F8`  | Start / stop recording                             |
| `F9`  | Play / stop playback of the last recording         |
| `[`   | Slower playback (interval percentage **+10%**)     |
| `]`   | Faster playback (interval percentage **−10%**)     |
| `F7`  | Save last recording → `macro.json`                 |
| `F6`  | Load recording ← `macro.json`                      |
| `F10` | Quit                                               |

All hotkeys are configurable at the top of `fortnite_macro.py` in the `CONFIG`
dictionary.

---

## Configuration

Edit the `CONFIG` block near the top of `fortnite_macro.py`:

| Setting              | Meaning                                                        |
|----------------------|---------------------------------------------------------------|
| `record_key`         | Hotkey to start/stop recording                                |
| `play_key`           | Hotkey to play/stop playback                                   |
| `speed_down_key` / `speed_up_key` | Live speed adjustment keys                        |
| `save_key` / `load_key` | Save / load hotkeys                                        |
| `quit_key`           | Quit hotkey                                                    |
| `interval_percent`   | Playback speed as a % of original intervals (100 = original)   |
| `countdown_beeps`    | Lead beeps before "GO" (2 → three audible cues total)         |
| `beep_freq` / `beep_ms` / `beep_gap_s` | Countdown beep tuning                       |
| `macro_file`         | File used by save/load (default `macro.json`)                  |
| `record_mouse_moves` | `True` records full mouse path; `False` records only clicks/keys |

---

## How playback speed works

Each event stores its time offset `t` from the start of the recording. On
playback the engine fires event *i* at:

```
start_time + t_i * (interval_percent / 100)
```

Because the **same** factor multiplies every offset, both mouse and keyboard
events shift together — the whole combined sequence is scaled proportionally,
keeping movement and key timing in sync at any speed.

---

## Troubleshooting

- **No sound / no voice:** install `pyttsx3` for spoken cues; on non-Windows the
  beep falls back to the terminal bell. Make sure your headset is the default
  output device.
- **Replayed input ignored by the game:** run the script as administrator
  (see the run tip above).
- **Keystrokes look stuck after playback:** the engine auto-releases common
  modifiers and mouse buttons when playback ends; if you stopped abruptly,
  tap the affected key once.
- **Files are huge:** set `record_mouse_moves` to `False` to capture only
  clicks, scrolls and keystrokes.
