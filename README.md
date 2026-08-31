# Fortnite Macro Recorder

> **This repo now has two tools:**
> 1. **Macro Recorder** (`fortnite_macro.py` / `macro_gui.py`) — records &
>    replays mouse/keyboard input. Documented below.
> 2. **Clip & Inject** (`clip_audio.py` / `clip_gui.py`) — a background **audio
>    clipper + mic injector** (GeForce-overlay style): grab the last few
>    seconds of game audio, play it back to only yourself, or **inject it into
>    your mic so teammates hear it** — without creating a new microphone. See
>    **[Clip & Inject](#clip--inject-background-audio-clipper--mic-injector)**
>    at the bottom.

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

---

# Clip & Inject — background audio clipper + mic injector

Run it overtop Fortnite like a GeForce/Shadowplay overlay. Global hotkeys work
**even while the game is focused**. You can:

- **Clip the last N seconds** of audio (instant-replay buffer, default **4s**) —
  one key, always on.
- **Manual clip** — one key starts recording, the same key stops it.
- **Ghost play** — replay the most recent clip **only into your own headphones**.
  Nobody else hears it.
- **Inject play** — replay the most recent clip **into your microphone** so your
  teammates / the lobby hear it. Great for trolling in a video.

> 🔑 **It never creates its own microphone.** It only *plays* the clip into an
> output you **already have** that loops back into an existing mic. That is the
> whole trick — no new device is installed or registered.

> ⚠️ Injecting audio into voice chat can annoy people or break a game's rules.
> Meant for making videos with friends who are in on it. Your machine, your risk.

## How injection reaches teammates without a new mic

```
 Clip & Inject  --play-->  a virtual OUTPUT you already have
                           ("Voicemod Virtual Audio Device", "CABLE Input",
                            or a real output with Windows "Listen to this
                            device" turned on)
                                   |
                                   v   (loops back internally)
                           the matching MICROPHONE endpoint
                           ("Microphone (Voicemod ...)", "CABLE Output", ...)
                                   |
                                   v
                           Fortnite / Discord mic  -->  teammates hear it
```

The only setup: point **Fortnite's microphone** at the **same** virtual device
you choose as the tool's **inject output**. Pick whichever you already have:

| You already run… | Inject output (in the tool) | Fortnite / Discord mic |
|------------------|-----------------------------|------------------------|
| **Voicemod**     | `Voicemod Virtual Audio Device` | `Microphone (Voicemod Virtual Audio Device)` |
| **VB-Audio CABLE** | `CABLE Input`             | `CABLE Output`         |
| **Nothing (zero installs)** | a real output with *Listen to this device* on, or **Stereo Mix** | that same loopback |

With Voicemod it already works: its virtual device is a loopback, so playing
into its output side comes out of its mic side, mixed in with your real voice.
Your friends can then do the exact same thing so they hear **their own** voice —
the trolling loop you described.

## Install & run

Requires **Python 3.8+**.

```bash
pip install -r requirements.txt      # sounddevice + numpy + pynput (pyttsx3 optional)
python clip_gui.py                   # control panel (recommended)
python clip_audio.py                 # console / hotkey-only, no window
python clip_audio.py --devices       # list audio devices with their indexes
```

`sounddevice` bundles PortAudio and, on **Windows**, supports **WASAPI
loopback**, so "capture from" can be an *output* device — that's how the tool
clips the **game audio you hear** rather than your mic. If loopback isn't
available it falls back to a normal input device (your mic).

## GUI

A dark, Razer-Synapse-style panel (matches the macro GUI):

- **AUDIO DEVICES** — three dropdowns:
  - *Capture from* — what gets clipped (default output via loopback = game audio).
  - *Monitor / ghost* — your headphones (ghost play + hearing your own injects).
  - *Inject into* — the virtual output that loops to your mic
    (auto-detects Voicemod / CABLE by name).
- **CLIP LENGTH** slider — 1–30s for "clip last".
- Big buttons: **CLIP LAST**, **RECORD**, **GHOST PLAY**, **INJECT PLAY**, **STOP**.
- **HOTKEYS** — click a key-cap, press a key to (re)bind it.
- A live activity log, plus **LOAD CLIP…** and **OPEN FOLDER**.

## Default hotkeys

| Key   | Action                                                    |
|-------|-----------------------------------------------------------|
| `F6`  | Clip the **last N seconds** (instant replay)              |
| `F7`  | Start / stop a **manual recording**                       |
| `F8`  | **Ghost play** the newest clip (only you hear)            |
| `F9`  | **Inject play** the newest clip (teammates hear)          |
| `F10` | Stop playback                                             |
| `F12` | Quit                                                      |

All keys and devices are configurable in the `CONFIG` block at the top of
`clip_audio.py`, or live in the GUI.

## Configuration (`CONFIG` in `clip_audio.py`)

| Setting                   | Meaning                                                         |
|---------------------------|-----------------------------------------------------------------|
| `clip_last_key` … `quit_key` | The six global hotkeys                                       |
| `clip_seconds`            | How many seconds "clip last" grabs (default 4)                  |
| `buffer_seconds`          | Size of the always-on rolling buffer (default 30)              |
| `samplerate` / `channels` / `blocksize` | Audio format                                     |
| `capture_device`          | Index or name substring to clip from (`None` = default output loopback → mic) |
| `capture_loopback`        | Try WASAPI loopback on the capture device (Windows)            |
| `monitor_device`          | Your headphones for ghost play (`None` = default output)       |
| `inject_device`           | The virtual output that loops to your mic (`None` = auto-detect) |
| `monitor_while_injecting` | Also hear injected clips in your own headphones                |
| `clip_dir`                | Folder where `.wav` clips are written                          |

## Troubleshooting (Clip & Inject)

- **Teammates can't hear the inject** — Fortnite's mic must be the device your
  inject output loops into (see the table). Test in Discord's *mic test* first.
- **Clips are silent** — your "capture from" device isn't carrying the game
  audio. On Windows use the default **output** (loopback) or enable **Stereo
  Mix**; if you only have a mic available, clips will record the mic instead.
- **"No inject output set and none auto-detected"** — pick your Voicemod / CABLE
  / Stereo-Mix output in the *Inject into* dropdown (or set `inject_device`).
- **Hotkeys don't fire in-game** — Fortnite often runs as admin; run the tool
  from an **administrator** terminal so its global key listener sees the keys.
- **Choppy playback** — raise `blocksize` (e.g. 4096) in `CONFIG`.
