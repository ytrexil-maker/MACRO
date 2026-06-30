"""
Fortnite Macro Recorder
=======================

A lightweight background macro tool you can run *overtop* Fortnite (or any
full-screen game). It records your exact mouse movements, clicks, scrolls and
keystrokes with high-resolution timing, then replays them so they look just
like you played the sequence live.

Workflow
--------
1. Run the script. It sits quietly in the background listening for hotkeys.
2. Press the RECORD hotkey (default: F8).
      * You hear a 3-beep countdown in your headset.
      * The final beep is a spoken "GO" -- recording starts on that beep.
3. Play your sequence in-game. Every mouse move / click / scroll / key press
   is captured with a precise timestamp.
4. Press the RECORD hotkey (F8) again to stop. You hear "recording stopped".
5. Press the PLAY hotkey (default: F9) to replay the last recording.
6. Adjust playback speed with the [ and ] keys (or in the config). Speed is a
   single percentage applied uniformly to every time interval, so the mouse
   and keyboard stay perfectly in proportion / in sync.

Hotkeys (configurable near the top of the file)
-----------------------------------------------
    F8  : start / stop recording
    F9  : play / stop playback of the last recording
    [   : slow playback down (interval percentage +10%)
    ]   : speed playback up   (interval percentage -10%)
    F7  : save last recording to disk  (macro.json)
    F6  : load recording from disk     (macro.json)
    F10 : quit

Dependencies
------------
    pip install pynput
    pip install pyttsx3   (optional, for the spoken "GO" / "recording stopped";
                           falls back to plain beeps if not installed)

Notes
-----
* On Windows the beeps use the built-in winsound module (no extra install).
* Replaying input into some anti-cheat protected games can violate their terms
  of service. Use this on your own machine, for practice / training, and at
  your own risk.
"""

import json
import os
import sys
import threading
import time

try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button, Controller as MouseController
    from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
except ImportError:
    sys.exit(
        "The 'pynput' package is required.\n"
        "Install it with:  pip install pynput"
    )


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #

CONFIG = {
    # Hotkeys -- change these to taste. Use pynput key names, e.g. "f8", "f9".
    "record_key": "f8",
    "play_key": "f9",
    "speed_down_key": "[",   # makes intervals longer  -> slower replay
    "speed_up_key": "]",     # makes intervals shorter -> faster replay
    "save_key": "f7",
    "load_key": "f6",
    "quit_key": "f10",

    # Playback speed as a PERCENTAGE of the original time intervals.
    #   100 = original speed
    #   200 = twice as long between events (half speed, slower)
    #    50 = half the time between events (double speed, faster)
    # Applied uniformly to mouse + keyboard so everything stays in proportion.
    "interval_percent": 100,

    # Countdown: number of lead beeps before the spoken "GO".
    "countdown_beeps": 2,        # 2 beeps + "GO" beep = 3 audible cues total
    "beep_freq": 880,            # Hz
    "beep_ms": 180,              # length of each beep
    "beep_gap_s": 0.7,           # gap between countdown beeps

    # File used by the save / load hotkeys.
    "macro_file": "macro.json",

    # If True, mouse-move events are captured. Turn off to record only
    # clicks / scrolls / keystrokes (much smaller files).
    "record_mouse_moves": True,
}


# --------------------------------------------------------------------------- #
#  Audio helpers (beeps + optional spoken cues)
# --------------------------------------------------------------------------- #

class Audio:
    """Plays beeps and (if available) spoken phrases into the default output."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._tts = None
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", 185)
        except Exception:
            self._tts = None  # fall back to beeps only

        # Pick a beep backend.
        self._winsound = None
        if sys.platform.startswith("win"):
            try:
                import winsound
                self._winsound = winsound
            except Exception:
                self._winsound = None

    def beep(self, freq=None, ms=None):
        freq = freq or self.cfg["beep_freq"]
        ms = ms or self.cfg["beep_ms"]
        if self._winsound:
            try:
                self._winsound.Beep(int(freq), int(ms))
                return
            except Exception:
                pass
        # Cross-platform fallback: terminal bell (best effort).
        sys.stdout.write("\a")
        sys.stdout.flush()
        time.sleep(ms / 1000.0)

    def say(self, phrase, fallback_beep=True):
        """Speak a phrase. Falls back to a distinctive beep if no TTS engine."""
        if self._tts is not None:
            try:
                self._tts.say(phrase)
                self._tts.runAndWait()
                return
            except Exception:
                pass
        if fallback_beep:
            # A higher, longer beep stands in for the spoken word.
            self.beep(freq=self.cfg["beep_freq"] + 320, ms=self.cfg["beep_ms"] + 120)

    def countdown_then_go(self):
        """Three-beep countdown ending on a spoken 'GO'."""
        for _ in range(max(0, self.cfg["countdown_beeps"])):
            self.beep()
            time.sleep(self.cfg["beep_gap_s"])
        # Final cue: a beep together with the spoken "GO". Recording starts now.
        self.beep(freq=self.cfg["beep_freq"] + 220, ms=self.cfg["beep_ms"])
        self.say("GO")


# --------------------------------------------------------------------------- #
#  Event (de)serialisation
# --------------------------------------------------------------------------- #
#
# Every recorded action is stored as a dict so it can be saved to JSON:
#
#   {"t": <float seconds since recording start>, "type": "...", ...}
#
# Types:
#   move   : {"x", "y"}
#   click  : {"x", "y", "button", "pressed"}
#   scroll : {"x", "y", "dx", "dy"}
#   kdown  : {"key"}
#   kup    : {"key"}
#
# Keys are serialised to a string form we can reconstruct on playback.

def key_to_str(key):
    """Serialise a pynput key to a portable string."""
    if isinstance(key, KeyCode):
        if key.char is not None:
            return "char:" + key.char
        if key.vk is not None:
            return "vk:" + str(key.vk)
        return "char:?"
    if isinstance(key, Key):
        return "key:" + key.name
    return "key:" + str(key)


def str_to_key(s):
    """Reconstruct a pynput key from its string form."""
    if s.startswith("char:"):
        return KeyCode.from_char(s[len("char:"):])
    if s.startswith("vk:"):
        return KeyCode.from_vk(int(s[len("vk:"):]))
    if s.startswith("key:"):
        name = s[len("key:"):]
        return getattr(Key, name, None)
    return None


# --------------------------------------------------------------------------- #
#  The recorder / player
# --------------------------------------------------------------------------- #

class MacroEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.audio = Audio(cfg)

        self.events = []           # the last recording
        self.recording = False
        self.playing = False

        self._rec_start = 0.0
        self._mouse_listener = None
        self._kbd_listener = None

        self._mouse_ctl = MouseController()
        self._kbd_ctl = KeyboardController()

        # Resolve hotkey objects once for fast comparison.
        self._hotkeys = {
            name: self._parse_hotkey(cfg[name])
            for name in (
                "record_key", "play_key", "speed_down_key", "speed_up_key",
                "save_key", "load_key", "quit_key",
            )
        }
        # Set of hotkeys we must NOT record (so control keys don't pollute macros).
        self._control_keys = set(self._hotkeys.values())

        self._stop_flag = threading.Event()   # signals app quit
        self._play_stop = threading.Event()    # signals "stop current playback"

        # ----- optional GUI hooks (left as None for headless console use) --- #
        self.on_status = None        # callback(str) -> append to a log / status line
        self.on_state_change = None  # callback() -> recording/playing state changed
        self.on_speed_change = None  # callback(int) -> interval_percent changed
        self.on_capture_done = None  # callback(binding_name, display_str)
        self._capture_target = None  # name of the binding currently being rebound

    def _log(self, msg):
        """Route a user-facing message to the GUI (if attached) and console."""
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

    # ----- hotkey parsing ------------------------------------------------- #
    @staticmethod
    def _parse_hotkey(spec):
        """Return a comparable key object for a config hotkey string."""
        spec = spec.strip()
        special = getattr(Key, spec, None)
        if special is not None:
            return special
        return KeyCode.from_char(spec)

    @staticmethod
    def _same_key(a, b):
        """Compare two key objects loosely (char or special name)."""
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

    def _is_control_key(self, key):
        return any(self._same_key(key, ck) for ck in self._control_keys)

    @staticmethod
    def key_display(key):
        """Human-readable label for a key object (for the GUI)."""
        if key is None:
            return "—"
        if isinstance(key, Key):
            return key.name.upper()
        ch = getattr(key, "char", None)
        if ch:
            return ch.upper() if ch.isalpha() else ch
        vk = getattr(key, "vk", None)
        return f"VK{vk}" if vk is not None else str(key)

    # ----- live rebinding (used by the GUI) ------------------------------- #
    def begin_capture(self, binding_name):
        """Arm capture: the next key you press becomes this binding."""
        self._capture_target = binding_name
        self._log(f"[BIND] Press a key to set '{binding_name}'...")

    def cancel_capture(self):
        self._capture_target = None

    def _handle_capture(self, key):
        name = self._capture_target
        self._capture_target = None
        self._hotkeys[name] = key
        self.cfg[name] = self.key_display(key).lower()
        self._control_keys = set(self._hotkeys.values())
        label = self.key_display(key)
        self._log(f"[BIND] '{name}' set to {label}")
        if self.on_capture_done:
            try:
                self.on_capture_done(name, label)
            except Exception:
                pass

    # ----- recording ------------------------------------------------------ #
    def _now(self):
        return time.perf_counter() - self._rec_start

    def _record_event(self, ev):
        if self.recording:
            self.events.append(ev)

    def _on_move(self, x, y):
        if self.recording and self.cfg["record_mouse_moves"]:
            self._record_event({"t": self._now(), "type": "move", "x": x, "y": y})

    def _on_click(self, x, y, button, pressed):
        if self.recording:
            self._record_event({
                "t": self._now(), "type": "click",
                "x": x, "y": y, "button": button.name, "pressed": pressed,
            })

    def _on_scroll(self, x, y, dx, dy):
        if self.recording:
            self._record_event({
                "t": self._now(), "type": "scroll",
                "x": x, "y": y, "dx": dx, "dy": dy,
            })

    def _on_press(self, key):
        # Hotkeys are handled by a separate dispatcher; here we only record.
        if self.recording and not self._is_control_key(key):
            self._record_event({"t": self._now(), "type": "kdown", "key": key_to_str(key)})

    def _on_release(self, key):
        if self.recording and not self._is_control_key(key):
            self._record_event({"t": self._now(), "type": "kup", "key": key_to_str(key)})

    def start_recording(self):
        if self.recording or self.playing:
            return
        self._log("[REC] Countdown...")
        self.audio.countdown_then_go()
        self.events = []
        self._rec_start = time.perf_counter()
        self.recording = True
        self._log("[REC] Recording -- press the record hotkey again to stop.")
        self._notify_state()

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self._log(f"[REC] Stopped. Captured {len(self.events)} events.")
        self._notify_state()
        self.audio.say("recording stopped")

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    # ----- playback ------------------------------------------------------- #
    def toggle_playback(self):
        if self.playing:
            self._play_stop.set()
            return
        if self.recording:
            self._log("[PLAY] Cannot play while recording.")
            return
        if not self.events:
            self._log("[PLAY] Nothing recorded yet.")
            return
        t = threading.Thread(target=self._play_thread, daemon=True)
        t.start()

    def _play_thread(self):
        self.playing = True
        self._play_stop.clear()
        self._notify_state()
        scale = max(0.0, self.cfg["interval_percent"] / 100.0)
        self._log(f"[PLAY] Replaying {len(self.events)} events at "
                  f"{self.cfg['interval_percent']}% interval "
                  f"(speed x{(1/scale) if scale else 0:.2f}).")
        start = time.perf_counter()
        try:
            for ev in self.events:
                if self._play_stop.is_set():
                    self._log("[PLAY] Stopped by user.")
                    break
                # When should this event fire, scaled by the interval percentage?
                target = start + ev["t"] * scale
                while True:
                    if self._play_stop.is_set():
                        break
                    remaining = target - time.perf_counter()
                    if remaining <= 0:
                        break
                    time.sleep(min(remaining, 0.005))
                if self._play_stop.is_set():
                    break
                self._dispatch(ev)
            else:
                self._log("[PLAY] Done.")
        finally:
            # Release any keys/buttons that might still be held down.
            self._release_all()
            self.playing = False
            self._notify_state()

    def _dispatch(self, ev):
        et = ev["type"]
        try:
            if et == "move":
                self._mouse_ctl.position = (ev["x"], ev["y"])
            elif et == "click":
                self._mouse_ctl.position = (ev["x"], ev["y"])
                btn = getattr(Button, ev["button"], Button.left)
                if ev["pressed"]:
                    self._mouse_ctl.press(btn)
                else:
                    self._mouse_ctl.release(btn)
            elif et == "scroll":
                self._mouse_ctl.position = (ev["x"], ev["y"])
                self._mouse_ctl.scroll(ev["dx"], ev["dy"])
            elif et == "kdown":
                k = str_to_key(ev["key"])
                if k is not None:
                    self._kbd_ctl.press(k)
            elif et == "kup":
                k = str_to_key(ev["key"])
                if k is not None:
                    self._kbd_ctl.release(k)
        except Exception as exc:
            print(f"[PLAY] Skipped event {ev}: {exc}")

    def _release_all(self):
        """Safety: release common modifiers and mouse buttons after playback."""
        for k in (Key.shift, Key.ctrl, Key.alt, Key.cmd):
            try:
                self._kbd_ctl.release(k)
            except Exception:
                pass
        for b in (Button.left, Button.right, Button.middle):
            try:
                self._mouse_ctl.release(b)
            except Exception:
                pass

    # ----- speed adjustment ---------------------------------------------- #
    def adjust_speed(self, delta_percent):
        new = self.cfg["interval_percent"] + delta_percent
        new = max(10, min(1000, new))   # clamp to a sane range
        self.cfg["interval_percent"] = new
        speed = (100.0 / new) if new else 0
        self._log(f"[SPEED] interval = {new}%  (playback speed x{speed:.2f})")
        if self.on_speed_change:
            try:
                self.on_speed_change(new)
            except Exception:
                pass

    def set_speed(self, percent):
        """Set interval percentage directly (used by the GUI slider)."""
        percent = max(10, min(1000, int(percent)))
        self.cfg["interval_percent"] = percent
        speed = (100.0 / percent) if percent else 0
        self._log(f"[SPEED] interval = {percent}%  (playback speed x{speed:.2f})")

    # ----- save / load ---------------------------------------------------- #
    def save(self, path=None):
        if not self.events:
            self._log("[SAVE] Nothing to save.")
            return
        path = path or self.cfg["macro_file"]
        data = {"interval_percent": self.cfg["interval_percent"], "events": self.events}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self._log(f"[SAVE] Wrote {len(self.events)} events to {os.path.abspath(path)}")

    def load(self, path=None):
        path = path or self.cfg["macro_file"]
        if not os.path.exists(path):
            self._log(f"[LOAD] No file at {os.path.abspath(path)}")
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.events = data.get("events", [])
        if "interval_percent" in data:
            self.cfg["interval_percent"] = data["interval_percent"]
            if self.on_speed_change:
                try:
                    self.on_speed_change(self.cfg["interval_percent"])
                except Exception:
                    pass
        self._log(f"[LOAD] Loaded {len(self.events)} events from {os.path.abspath(path)}")

    # ----- hotkey dispatch ------------------------------------------------ #
    def _hotkey_handler(self, key):
        if self._same_key(key, self._hotkeys["quit_key"]):
            self._log("[QUIT] Exiting.")
            self._stop_flag.set()
            return False  # stops the keyboard listener
        if self._same_key(key, self._hotkeys["record_key"]):
            self.toggle_recording()
        elif self._same_key(key, self._hotkeys["play_key"]):
            self.toggle_playback()
        elif self._same_key(key, self._hotkeys["speed_down_key"]):
            self.adjust_speed(+10)   # longer intervals = slower
        elif self._same_key(key, self._hotkeys["speed_up_key"]):
            self.adjust_speed(-10)   # shorter intervals = faster
        elif self._same_key(key, self._hotkeys["save_key"]):
            self.save()
        elif self._same_key(key, self._hotkeys["load_key"]):
            self.load()
        return True

    # ----- listener lifecycle (shared by console + GUI) ------------------- #
    def start_listeners(self):
        """Start the background mouse/keyboard listeners (non-blocking)."""
        # Mouse listener: records movement / clicks / scroll.
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )

        # Keyboard listener: capture-mode rebinding, recording, AND hotkeys.
        def on_press(key):
            if self._capture_target is not None:
                self._handle_capture(key)
                return True
            self._on_press(key)
            return self._hotkey_handler(key)

        self._kbd_listener = keyboard.Listener(
            on_press=on_press,
            on_release=self._on_release,
        )

        self._mouse_listener.start()
        self._kbd_listener.start()

    def stop_listeners(self):
        self._play_stop.set()
        try:
            self._mouse_listener.stop()
        except Exception:
            pass
        try:
            self._kbd_listener.stop()
        except Exception:
            pass

    # ----- run (console mode) --------------------------------------------- #
    def run(self):
        self._print_banner()
        self.start_listeners()
        try:
            while not self._stop_flag.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[QUIT] Interrupted.")
        finally:
            self.stop_listeners()

    def _print_banner(self):
        c = self.cfg
        print("=" * 60)
        print(" Fortnite Macro Recorder")
        print("=" * 60)
        print(f"  Record / stop : {c['record_key'].upper()}")
        print(f"  Play / stop   : {c['play_key'].upper()}")
        print(f"  Slower        : {c['speed_down_key']}   (interval +10%)")
        print(f"  Faster        : {c['speed_up_key']}   (interval -10%)")
        print(f"  Save          : {c['save_key'].upper()}  -> {c['macro_file']}")
        print(f"  Load          : {c['load_key'].upper()}  <- {c['macro_file']}")
        print(f"  Quit          : {c['quit_key'].upper()}")
        print("-" * 60)
        print(f"  Playback interval: {c['interval_percent']}%")
        print("  Press the record key to start a 3-beep countdown.")
        print("=" * 60)


def main():
    engine = MacroEngine(CONFIG)
    engine.run()


if __name__ == "__main__":
    main()
