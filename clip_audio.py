"""
Fortnite Clip & Inject -- background audio clipper + mic injector
=================================================================

A lightweight background tool you run *overtop* Fortnite (or any game), like an
NVIDIA/GeForce overlay. It listens for global hotkeys, so a keypress works even
while the game window is focused. With it you can:

* **Instant-replay clip** -- always-on rolling buffer. Hit one key to grab the
  **last N seconds** (default 4) of audio, exactly like "Save last 5 minutes"
  in the GeForce overlay, but for audio.
* **Manual clip** -- hit a key to *start* recording, hit it again to *stop*.
* **Ghost play** -- play the most recent clip **only into your own headphones**
  (your default output). Nobody else hears it.
* **Inject play** -- play the most recent clip **into your microphone** so your
  teammates / lobby hear it, as a prank for a video.

Crucially, this tool **does NOT create a microphone of its own**. It never
installs or registers any audio device. It only *plays* the clip into an output
you already have that loops back into an existing mic:

    +--------------------------------------------------------------+
    |  How "inject" reaches your teammates without a new mic        |
    +--------------------------------------------------------------+
    |  This tool  --play-->  a virtual OUTPUT you already have      |
    |                        (e.g. "Voicemod Virtual Audio Device", |
    |                         "CABLE Input", or a real output with  |
    |                         Windows "Listen to this device" on)   |
    |                                |                              |
    |                                v  (loops back internally)     |
    |                        the matching MICROPHONE endpoint        |
    |                        (e.g. "Microphone (Voicemod ...)")      |
    |                                |                              |
    |                                v                              |
    |                        Fortnite / Discord mic  --> teammates   |
    +--------------------------------------------------------------+

So the only setup is: point Fortnite's microphone at the SAME virtual device
you pick as the tool's "inject" output. If you use Voicemod, that's already
true -- Voicemod's virtual device is a loopback, so playing into its output
side comes out of its mic side, mixed in with your real voice.

    * Already run Voicemod?  Inject device = "Voicemod Virtual Audio Device".
    * Have VB-Audio CABLE?   Inject device = "CABLE Input", game mic = "CABLE
      Output".
    * Neither, want zero installs?  Enable "Stereo Mix" (or, on a real output,
      right-click it in Sound settings -> Properties -> Listen -> "Listen to
      this device" -> playback via your mic loop). Then inject to that output.

Dependencies
------------
    pip install sounddevice numpy pynput
    pip install pyttsx3   (optional -- spoken confirmations; falls back to beeps)

sounddevice ships PortAudio and, on Windows, supports WASAPI loopback so the
tool can record your *system / game audio* (what you hear) as easily as a mic.

Run
---
    python clip_gui.py      # the control panel (recommended)
    python clip_audio.py    # console / hotkey-only, no window

Notes
-----
* Injecting sound into a game's voice chat may annoy people or run afoul of a
  game's rules. This is meant for making videos with friends who are in on it.
  Use it on your own machine and at your own risk.
"""

import os
import sys
import threading
import time
import wave
from collections import deque

try:
    import numpy as np
except ImportError:
    sys.exit(
        "The 'numpy' package is required.\n"
        "Install it with:  pip install numpy"
    )

try:
    import sounddevice as sd
except ImportError:
    sys.exit(
        "The 'sounddevice' package is required.\n"
        "Install it with:  pip install sounddevice"
    )

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
except ImportError:
    sys.exit(
        "The 'pynput' package is required (global hotkeys).\n"
        "Install it with:  pip install pynput"
    )


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #

CONFIG = {
    # ----- Hotkeys (pynput names, e.g. "f6", "f7", or a single character) --- #
    "clip_last_key": "f6",     # grab the last N seconds from the rolling buffer
    "record_key": "f7",        # start / stop a manual recording
    "ghost_play_key": "f8",    # play most recent clip -> your headphones only
    "inject_play_key": "f9",   # play most recent clip -> your mic (others hear)
    "stop_play_key": "f10",    # stop any playback in progress
    "quit_key": "f12",         # quit the tool

    # ----- Instant-replay buffer ----------------------------------------- #
    "clip_seconds": 4.0,       # how many seconds "clip last" grabs
    "buffer_seconds": 30.0,    # size of the always-on rolling buffer

    # ----- Audio format --------------------------------------------------- #
    "samplerate": 48000,
    "channels": 2,
    "blocksize": 2048,

    # ----- Devices (None = auto / system default). Set by index or by a
    #        case-insensitive name substring; see list_devices(). ---------- #
    #  capture_device : where clips are recorded FROM. On Windows this can be
    #                   an OUTPUT device captured via WASAPI loopback (records
    #                   the game audio you hear). Leave None to auto-pick the
    #                   default output's loopback, falling back to the mic.
    "capture_device": None,
    "capture_loopback": True,  # try WASAPI loopback on the capture device

    #  monitor_device : your headphones, used for "ghost play". None = default.
    "monitor_device": None,

    #  inject_device  : the virtual OUTPUT that loops into your existing mic.
    #                   None = auto-detect Voicemod / VB-CABLE by name.
    "inject_device": None,

    # When injecting, also play into your headphones so you hear it too.
    "monitor_while_injecting": True,

    # ----- Files ---------------------------------------------------------- #
    "clip_dir": "clips",       # where .wav clips are written
}

# Names we auto-match for the "inject" output if none is configured. These are
# devices that already exist on machines running these tools -- we create none.
INJECT_NAME_HINTS = ("voicemod", "cable input", "vb-audio", "vb audio",
                     "voicemeeter", "stereo mix", "line 1")


# --------------------------------------------------------------------------- #
#  Small spoken / beep confirmations (reused pattern from fortnite_macro.py)
# --------------------------------------------------------------------------- #

class Cue:
    """Short audible confirmations into the default output (best effort)."""

    def __init__(self):
        self._tts = None
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", 190)
        except Exception:
            self._tts = None
        self._winsound = None
        if sys.platform.startswith("win"):
            try:
                import winsound
                self._winsound = winsound
            except Exception:
                self._winsound = None

    def beep(self, freq=880, ms=120):
        if self._winsound:
            try:
                self._winsound.Beep(int(freq), int(ms))
                return
            except Exception:
                pass
        sys.stdout.write("\a")
        sys.stdout.flush()

    def say(self, phrase):
        # Speak in a worker so it never blocks the hotkey thread.
        def run():
            if self._tts is not None:
                try:
                    self._tts.say(phrase)
                    self._tts.runAndWait()
                    return
                except Exception:
                    pass
            self.beep()
        threading.Thread(target=run, daemon=True).start()


# --------------------------------------------------------------------------- #
#  Device helpers
# --------------------------------------------------------------------------- #

def list_devices():
    """Return sounddevice's device table (list of dicts)."""
    try:
        return list(sd.query_devices())
    except Exception:
        return []


def print_devices():
    """Print a numbered list of devices with in/out channel counts."""
    devs = list_devices()
    print("Index  In  Out  Name")
    print("-----  --  ---  ----")
    for i, d in enumerate(devs):
        print(f"{i:>5}  {d['max_input_channels']:>2}  {d['max_output_channels']:>3}"
              f"  {d['name']}")


def find_device(spec, want_output=True):
    """Resolve a device spec (int index, or name substring) to an index.

    Returns an int index, or None if not found / spec is None.
    """
    if spec is None:
        return None
    if isinstance(spec, int):
        return spec
    if isinstance(spec, str) and spec.strip():
        needle = spec.strip().lower()
        for i, d in enumerate(list_devices()):
            chans = d["max_output_channels"] if want_output else d["max_input_channels"]
            if chans > 0 and needle in d["name"].lower():
                return i
    return None


def auto_inject_device():
    """Guess an output device that loops into an existing mic (no install)."""
    for hint in INJECT_NAME_HINTS:
        idx = find_device(hint, want_output=True)
        if idx is not None:
            return idx
    return None


# --------------------------------------------------------------------------- #
#  The clip engine
# --------------------------------------------------------------------------- #

class ClipEngine:
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.cue = Cue()

        self.sr = int(cfg["samplerate"])
        self.ch = int(cfg["channels"])
        self.block = int(cfg["blocksize"])

        # Always-on rolling buffer of recent audio (deque of int16 chunks).
        max_chunks = int(cfg["buffer_seconds"] * self.sr / self.block) + 4
        self._ring = deque(maxlen=max_chunks)
        self._ring_lock = threading.Lock()

        # Manual recording state.
        self.recording = False
        self._rec_chunks = []
        self._rec_lock = threading.Lock()

        # Most recent finished clip (int16 numpy array, shape (n, channels)).
        self.last_clip = None
        self.last_path = None

        self.playing = False
        self._play_stop = threading.Event()
        self._active_streams = []

        self._in_stream = None
        self._kbd_listener = None
        self._stop_flag = threading.Event()

        # Resolve hotkeys once for fast comparison.
        self._hotkeys = {
            name: self._parse_hotkey(cfg[name])
            for name in ("clip_last_key", "record_key", "ghost_play_key",
                         "inject_play_key", "stop_play_key", "quit_key")
        }

        os.makedirs(self.cfg["clip_dir"], exist_ok=True)

        # ----- optional GUI hooks (None for headless console use) ---------- #
        self.on_status = None        # callback(str)
        self.on_state_change = None  # callback()
        self.on_capture_done = None  # callback(binding_name, display_str)
        self._capture_target = None

    # ----- logging -------------------------------------------------------- #
    def _log(self, msg):
        if self.on_status:
            try:
                self.on_status(msg)
            except Exception:
                pass
        else:
            print(msg)

    def _notify_state(self):
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    # ----- hotkey parsing (same conventions as fortnite_macro.py) --------- #
    @staticmethod
    def _parse_hotkey(spec):
        spec = str(spec).strip()
        special = getattr(Key, spec, None)
        if special is not None:
            return special
        return KeyCode.from_char(spec)

    @staticmethod
    def _same_key(a, b):
        if a is None or b is None:
            return False
        if isinstance(a, Key) and isinstance(b, Key):
            return a == b
        ca = getattr(a, "char", None)
        cb = getattr(b, "char", None)
        if ca is not None and cb is not None:
            return ca == cb
        va = getattr(a, "vk", None)
        vb = getattr(b, "vk", None)
        if va is not None and vb is not None:
            return va == vb
        return False

    @staticmethod
    def key_display(key):
        if key is None:
            return "-"
        if isinstance(key, Key):
            return key.name.upper()
        ch = getattr(key, "char", None)
        if ch:
            return ch.upper() if ch.isalpha() else ch
        vk = getattr(key, "vk", None)
        return f"VK{vk}" if vk is not None else str(key)

    # ----- live rebinding (used by the GUI) ------------------------------- #
    def begin_capture(self, target):
        self._capture_target = target
        self._log(f"[BIND] Press a key to set '{target}'...")

    def cancel_capture(self):
        self._capture_target = None

    def _handle_capture(self, key):
        target = self._capture_target
        self._capture_target = None
        label = self.key_display(key)
        self._hotkeys[target] = key
        self.cfg[target] = label.lower()
        self._log(f"[BIND] '{target}' set to {label}")
        if self.on_capture_done:
            try:
                self.on_capture_done(target, label)
            except Exception:
                pass

    # ----- capture stream ------------------------------------------------- #
    def _open_input_stream(self):
        """Open the always-on capture stream, trying WASAPI loopback first."""
        device = find_device(self.cfg["capture_device"], want_output=True)
        extra = None
        loopback_ok = False

        # On Windows we can record the audio you HEAR by opening the output
        # device with WASAPI loopback. This is what makes "clip the game" work.
        if self.cfg.get("capture_loopback") and sys.platform.startswith("win"):
            try:
                out_default = sd.default.device[1]
                target = device if device is not None else out_default
                extra = sd.WasapiSettings(loopback=True)
                self._in_stream = sd.InputStream(
                    samplerate=self.sr, channels=self.ch, dtype="int16",
                    blocksize=self.block, device=target,
                    extra_settings=extra, callback=self._audio_cb)
                self._in_stream.start()
                loopback_ok = True
                self._log(f"[AUDIO] Capturing system/game audio (loopback) from "
                          f"device {target}.")
            except Exception as exc:
                self._log(f"[AUDIO] Loopback capture unavailable ({exc}); "
                          f"using a normal input device.")
                self._in_stream = None

        if not loopback_ok:
            # Plain input (a microphone, or default input device).
            in_device = device if device is not None else None
            self._in_stream = sd.InputStream(
                samplerate=self.sr, channels=self.ch, dtype="int16",
                blocksize=self.block, device=in_device, callback=self._audio_cb)
            self._in_stream.start()
            self._log(f"[AUDIO] Capturing from input device "
                      f"{in_device if in_device is not None else 'default'}.")

    def _audio_cb(self, indata, frames, time_info, status):
        if status:
            # Overflows are non-fatal; just note them once in a while.
            pass
        chunk = np.array(indata, dtype=np.int16, copy=True)
        with self._ring_lock:
            self._ring.append(chunk)
        if self.recording:
            with self._rec_lock:
                self._rec_chunks.append(chunk)

    # ----- clip creation -------------------------------------------------- #
    def clip_last(self, seconds=None):
        """Grab the last N seconds from the rolling buffer as the newest clip."""
        seconds = float(seconds if seconds is not None else self.cfg["clip_seconds"])
        with self._ring_lock:
            chunks = list(self._ring)
        if not chunks:
            self._log("[CLIP] Buffer is empty (is audio playing / capturing?).")
            return None
        data = np.concatenate(chunks, axis=0)
        want = int(seconds * self.sr)
        if data.shape[0] > want:
            data = data[-want:]
        self.last_clip = data
        path = self._save_wav(data, prefix="clip")
        self._log(f"[CLIP] Saved last {seconds:g}s "
                  f"({data.shape[0] / self.sr:.1f}s) -> {path}")
        self.cue.beep(1046, 90)
        self._notify_state()
        return path

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.recording:
            return
        with self._rec_lock:
            self._rec_chunks = []
        self.recording = True
        self._log("[REC] Recording... press the record key again to stop.")
        self.cue.beep(660, 90)
        self._notify_state()

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        with self._rec_lock:
            chunks = list(self._rec_chunks)
            self._rec_chunks = []
        if not chunks:
            self._log("[REC] Stopped -- nothing captured.")
            self._notify_state()
            return
        data = np.concatenate(chunks, axis=0)
        self.last_clip = data
        path = self._save_wav(data, prefix="rec")
        self._log(f"[REC] Stopped. {data.shape[0] / self.sr:.1f}s -> {path}")
        self.cue.beep(1046, 90)
        self._notify_state()

    def _save_wav(self, data, prefix="clip"):
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(self.cfg["clip_dir"], f"{prefix}-{ts}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(self.ch)
            w.setsampwidth(2)  # int16
            w.setframerate(self.sr)
            w.writeframes(np.ascontiguousarray(data, dtype="<i2").tobytes())
        self.last_path = path
        return path

    def load_clip(self, path):
        """Load a .wav file as the most-recent clip (for replay)."""
        with wave.open(path, "rb") as w:
            n = w.getnframes()
            raw = w.readframes(n)
            ch = w.getnchannels()
        data = np.frombuffer(raw, dtype="<i2")
        if ch > 1:
            data = data.reshape(-1, ch)
        else:
            data = data.reshape(-1, 1)
        self.last_clip = data
        self.last_path = path
        self._log(f"[LOAD] Loaded {path} ({data.shape[0] / self.sr:.1f}s).")
        self._notify_state()

    # ----- playback ------------------------------------------------------- #
    def ghost_play(self):
        """Play the newest clip into your headphones only (nobody else hears)."""
        self._play_last([("monitor", self.cfg["monitor_device"])], "GHOST")

    def inject_play(self):
        """Play the newest clip into your mic so teammates hear it."""
        inject = self.cfg["inject_device"]
        idx = find_device(inject, want_output=True)
        if idx is None:
            idx = auto_inject_device()
        if idx is None:
            self._log("[INJECT] No inject output set and none auto-detected. "
                      "Pick your Voicemod / CABLE / Stereo-Mix output first.")
            self.cue.beep(220, 200)
            return
        targets = [("inject", idx)]
        if self.cfg.get("monitor_while_injecting"):
            targets.append(("monitor", self.cfg["monitor_device"]))
        self._play_last(targets, "INJECT")

    def _play_last(self, targets, label):
        if self.last_clip is None:
            self._log(f"[{label}] No clip yet -- make one first.")
            self.cue.beep(220, 160)
            return
        # Stop anything currently playing, then start fresh.
        self._play_stop.set()
        time.sleep(0.02)
        self._play_stop.clear()
        data = self.last_clip
        started = 0
        for kind, spec in targets:
            idx = find_device(spec, want_output=True) if not isinstance(spec, int) else spec
            try:
                self._play_to_device(data, idx, kind)
                started += 1
            except Exception as exc:
                self._log(f"[{label}] Could not open {kind} device {spec}: {exc}")
        if started:
            dests = ", ".join(k for k, _ in targets)
            self._log(f"[{label}] Playing {data.shape[0] / self.sr:.1f}s -> {dests}.")
            self.playing = True
            self._notify_state()

    def _play_to_device(self, data, device, kind):
        """Stream an int16 array to one output device in a background thread."""
        stream = sd.OutputStream(
            samplerate=self.sr, channels=data.shape[1], dtype="int16",
            blocksize=self.block, device=device)
        stream.start()
        self._active_streams.append(stream)

        def run():
            try:
                i = 0
                n = data.shape[0]
                while i < n and not self._play_stop.is_set():
                    stream.write(data[i:i + self.block])
                    i += self.block
            except Exception:
                pass
            finally:
                try:
                    stream.stop(); stream.close()
                except Exception:
                    pass
                if stream in self._active_streams:
                    self._active_streams.remove(stream)
                if not self._active_streams:
                    self.playing = False
                    self._notify_state()

        threading.Thread(target=run, daemon=True).start()

    def stop_playback(self):
        self._play_stop.set()
        for s in list(self._active_streams):
            try:
                s.stop(); s.close()
            except Exception:
                pass
        self._active_streams.clear()
        self.playing = False
        self._log("[PLAY] Stopped.")
        self._notify_state()

    # ----- hotkey dispatch ------------------------------------------------ #
    def _hotkey_handler(self, key):
        if self._same_key(key, self._hotkeys["quit_key"]):
            self._log("[QUIT] Exiting.")
            self._stop_flag.set()
            return False
        if self._same_key(key, self._hotkeys["clip_last_key"]):
            self.clip_last()
        elif self._same_key(key, self._hotkeys["record_key"]):
            self.toggle_recording()
        elif self._same_key(key, self._hotkeys["ghost_play_key"]):
            self.ghost_play()
        elif self._same_key(key, self._hotkeys["inject_play_key"]):
            self.inject_play()
        elif self._same_key(key, self._hotkeys["stop_play_key"]):
            self.stop_playback()
        return True

    # ----- lifecycle ------------------------------------------------------ #
    def start(self):
        self._open_input_stream()

        def on_press(key):
            if self._capture_target is not None:
                self._handle_capture(key)
                return True
            return self._hotkey_handler(key)

        self._kbd_listener = keyboard.Listener(on_press=on_press)
        self._kbd_listener.start()

    def stop(self):
        self._play_stop.set()
        try:
            if self._in_stream:
                self._in_stream.stop(); self._in_stream.close()
        except Exception:
            pass
        try:
            if self._kbd_listener:
                self._kbd_listener.stop()
        except Exception:
            pass

    # ----- console mode --------------------------------------------------- #
    def run(self):
        self._print_banner()
        self.start()
        try:
            while not self._stop_flag.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[QUIT] Interrupted.")
        finally:
            self.stop()

    def _print_banner(self):
        c = self.cfg
        inj = find_device(c["inject_device"], True)
        if inj is None:
            inj = auto_inject_device()
        inj_name = list_devices()[inj]["name"] if inj is not None and list_devices() else "NOT SET"
        print("=" * 62)
        print(" Fortnite Clip & Inject")
        print("=" * 62)
        print(f"  Clip last {c['clip_seconds']:g}s : {c['clip_last_key'].upper()}")
        print(f"  Record start/stop: {c['record_key'].upper()}")
        print(f"  Ghost play (you) : {c['ghost_play_key'].upper()}")
        print(f"  Inject play (all): {c['inject_play_key'].upper()}")
        print(f"  Stop playback    : {c['stop_play_key'].upper()}")
        print(f"  Quit             : {c['quit_key'].upper()}")
        print("-" * 62)
        print(f"  Inject output    : {inj_name}")
        print(f"  Clips folder     : {os.path.abspath(c['clip_dir'])}")
        print("=" * 62)
        print("  Tip: run 'python clip_audio.py --devices' to list audio")
        print("  devices, then set inject_device / capture_device in CONFIG.")
        print("=" * 62)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--devices", "-d", "--list"):
        print_devices()
        return
    engine = ClipEngine(CONFIG)
    engine.run()


if __name__ == "__main__":
    main()
