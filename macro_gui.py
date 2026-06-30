"""
Macro Recorder -- GUI
=====================

A dark, Razer-Synapse-style control panel for the macro engine in
``fortnite_macro.py``. Nothing is hard-coded: you bind every key yourself by
clicking a key-cap and pressing the key you want.

Run:
    pip install pynput        (pyttsx3 optional, for spoken cues)
    python macro_gui.py

Panel features
--------------
* Big RECORD and PLAY toggles that light up green while active.
* Click any key-cap, then press a key to (re)bind it -- record, play,
  slower, faster, save, load and quit are all yours to set.
* A speed slider: one percentage scales every interval so mouse + keyboard
  stay in proportion (100% = original, 50% = 2x faster, 200% = half speed).
* Save / Load recordings to a file you choose.
* A live activity log.

The actual recording / playback / audio cues all live in the engine; this is
just a front-end for it.
"""

import os
import queue
import tkinter as tk
from tkinter import filedialog, font as tkfont

from fortnite_macro import CONFIG, MacroEngine


# --------------------------------------------------------------------------- #
#  Theme (Razer Synapse-ish: near-black panels, signature green accent)
# --------------------------------------------------------------------------- #

BG = "#0E0E0E"          # window background
PANEL = "#161616"       # raised panel
PANEL2 = "#1E1E1E"      # inner panel
EDGE = "#2A2A2A"        # subtle borders
GREEN = "#44D62C"       # Razer green
GREEN_DIM = "#2C8C1C"   # pressed / inactive green
RED = "#E03E2F"         # recording indicator
TEXT = "#EDEDED"
MUTED = "#7E7E7E"
KEYCAP = "#202020"

# Friendly labels for each engine binding.
BINDINGS = [
    ("record_key", "RECORD / STOP"),
    ("play_key", "PLAY / STOP"),
    ("speed_down_key", "SLOWER  (-)"),
    ("speed_up_key", "FASTER  (+)"),
    ("save_key", "QUICK SAVE"),
    ("load_key", "QUICK LOAD"),
    ("quit_key", "QUIT"),
]


class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.engine = MacroEngine(CONFIG)

        # Thread-safe channel: engine callbacks (other threads) push work here,
        # the Tk main loop drains it. Tkinter is not thread-safe otherwise.
        self.ui_queue = queue.Queue()

        self._capturing_name = None     # binding currently waiting for a key
        self._keycap_btns = {}          # binding name -> Button widget

        self._build_fonts()
        self._build_ui()
        self._wire_engine()

        self.engine.start_listeners()
        self._pump()  # start draining the UI queue
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- fonts ---------------------------------------------------------- #
    def _build_fonts(self):
        fam = "Segoe UI"
        try:
            available = set(tkfont.families())
            if fam not in available:
                fam = "Helvetica"
        except Exception:
            fam = "Helvetica"
        self.f_title = tkfont.Font(family=fam, size=18, weight="bold")
        self.f_sub = tkfont.Font(family=fam, size=9)
        self.f_label = tkfont.Font(family=fam, size=10, weight="bold")
        self.f_key = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.f_big = tkfont.Font(family=fam, size=14, weight="bold")
        self.f_log = tkfont.Font(family="Consolas", size=9)

    # ----- layout --------------------------------------------------------- #
    def _build_ui(self):
        self.root.title("MACRO SYNAPSE")
        self.root.configure(bg=BG)
        self.root.geometry("780x600")
        self.root.minsize(720, 560)

        # ---- header ----
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=18, pady=(16, 8))
        bar = tk.Frame(header, bg=GREEN, width=6, height=42)
        bar.pack(side="left", padx=(0, 12))
        bar.pack_propagate(False)
        titlebox = tk.Frame(header, bg=BG)
        titlebox.pack(side="left")
        tk.Label(titlebox, text="MACRO SYNAPSE", fg=TEXT, bg=BG,
                 font=self.f_title).pack(anchor="w")
        tk.Label(titlebox, text="INPUT RECORDER  /  CUSTOM KEY BINDINGS",
                 fg=GREEN, bg=BG, font=self.f_sub).pack(anchor="w")

        # status pill (top-right)
        self.status_pill = tk.Label(header, text="IDLE", fg="#0E0E0E", bg=MUTED,
                                    font=self.f_label, padx=14, pady=4)
        self.status_pill.pack(side="right")

        # ---- main body: two columns ----
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=8)

        left = self._panel(body, "KEY BINDINGS")
        left.pack(side="left", fill="both", expand=True, padx=(0, 9))
        self._build_bindings(left)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(9, 0))
        self._build_controls(right)

        # ---- log ----
        logwrap = self._panel(self.root, "ACTIVITY")
        logwrap.pack(fill="both", expand=False, padx=18, pady=(0, 16))
        self.log = tk.Text(logwrap, height=7, bg="#0A0A0A", fg=GREEN,
                           insertbackground=GREEN, relief="flat",
                           font=self.f_log, bd=0, padx=10, pady=8,
                           highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log.configure(state="disabled")

    def _panel(self, parent, title):
        """A bordered panel with a green section title; pack children into it."""
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                         highlightbackground=EDGE)
        tk.Label(frame, text=title, fg=GREEN, bg=PANEL, font=self.f_sub,
                 anchor="w").pack(fill="x", padx=12, pady=(10, 6))
        return frame

    # ----- bindings column ------------------------------------------------ #
    def _build_bindings(self, panel):
        hint = tk.Label(panel, text="Click a key, then press the key to assign.",
                        fg=MUTED, bg=PANEL, font=self.f_sub, anchor="w")
        hint.pack(fill="x", padx=12, pady=(0, 8))

        for name, label in BINDINGS:
            row = tk.Frame(panel, bg=PANEL)
            row.pack(fill="x", padx=12, pady=4)
            tk.Label(row, text=label, fg=TEXT, bg=PANEL, font=self.f_label,
                     anchor="w", width=16).pack(side="left")
            cap = tk.Button(
                row, text=self.engine.key_display(self.engine._hotkeys[name]),
                font=self.f_key, fg=GREEN, bg=KEYCAP,
                activebackground=GREEN, activeforeground="#0E0E0E",
                relief="flat", bd=0, width=10, pady=6, cursor="hand2",
                highlightthickness=1, highlightbackground=EDGE,
                command=lambda n=name: self._begin_capture(n),
            )
            cap.pack(side="right")
            self._keycap_btns[name] = cap

    # ----- controls column ------------------------------------------------ #
    def _build_controls(self, parent):
        # RECORD toggle
        self.btn_record = self._big_button(parent, "● RECORD",
                                           self.engine.toggle_recording)
        self.btn_record.pack(fill="x", pady=(0, 10))

        # PLAY toggle
        self.btn_play = self._big_button(parent, "▶ PLAY",
                                         self.engine.toggle_playback)
        self.btn_play.pack(fill="x", pady=(0, 14))

        # Speed panel
        speed = self._panel(parent, "PLAYBACK SPEED")
        speed.pack(fill="x")
        self.speed_val = tk.Label(speed, text="", fg=GREEN, bg=PANEL,
                                  font=self.f_big)
        self.speed_val.pack(anchor="w", padx=12)
        self.speed_scale = tk.Scale(
            speed, from_=10, to=400, orient="horizontal", showvalue=False,
            bg=PANEL, fg=TEXT, troughcolor="#0A0A0A", highlightthickness=0,
            activebackground=GREEN, bd=0, sliderrelief="flat", length=220,
            command=self._on_slider,
        )
        self.speed_scale.set(int(self.engine.cfg["interval_percent"]))
        self.speed_scale.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(speed, text="interval %  (lower = faster, higher = slower)",
                 fg=MUTED, bg=PANEL, font=self.f_sub).pack(anchor="w",
                                                           padx=12, pady=(0, 10))
        self._refresh_speed_label(int(self.engine.cfg["interval_percent"]))

        # Save / Load to a chosen file
        io = self._panel(parent, "FILE")
        io.pack(fill="x", pady=(12, 0))
        iorow = tk.Frame(io, bg=PANEL)
        iorow.pack(fill="x", padx=12, pady=(0, 12))
        self._mini_button(iorow, "SAVE AS…", self._save_as).pack(side="left",
                                                                 expand=True,
                                                                 fill="x",
                                                                 padx=(0, 5))
        self._mini_button(iorow, "LOAD…", self._load_from).pack(side="left",
                                                                expand=True,
                                                                fill="x",
                                                                padx=(5, 0))

    def _big_button(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, font=self.f_big,
                         fg=TEXT, bg=PANEL2, activebackground=GREEN_DIM,
                         activeforeground="#0E0E0E", relief="flat", bd=0,
                         pady=18, cursor="hand2",
                         highlightthickness=1, highlightbackground=EDGE)

    def _mini_button(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, font=self.f_label,
                         fg=GREEN, bg=KEYCAP, activebackground=GREEN,
                         activeforeground="#0E0E0E", relief="flat", bd=0,
                         pady=8, cursor="hand2",
                         highlightthickness=1, highlightbackground=EDGE)

    # ----- engine wiring -------------------------------------------------- #
    def _wire_engine(self):
        # All callbacks fire from listener / playback threads -> marshal to UI.
        self.engine.on_status = lambda m: self.ui_queue.put(("log", m))
        self.engine.on_state_change = lambda: self.ui_queue.put(("state", None))
        self.engine.on_speed_change = lambda p: self.ui_queue.put(("speed", p))
        self.engine.on_capture_done = lambda n, d: self.ui_queue.put(
            ("capture", (n, d)))

    def _pump(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "state":
                    self._refresh_state()
                elif kind == "speed":
                    self._refresh_speed_label(payload)
                    if int(self.speed_scale.get()) != int(payload):
                        self.speed_scale.set(int(payload))
                elif kind == "capture":
                    name, disp = payload
                    self._capturing_name = None
                    self._keycap_btns[name].configure(text=disp, fg=GREEN,
                                                      bg=KEYCAP)
        except queue.Empty:
            pass
        if self.engine._stop_flag.is_set():
            self._on_close()
            return
        self.root.after(60, self._pump)

    # ----- actions -------------------------------------------------------- #
    def _begin_capture(self, name):
        # Reset any previously-armed cap.
        if self._capturing_name and self._capturing_name in self._keycap_btns:
            prev = self._keycap_btns[self._capturing_name]
            prev.configure(
                text=self.engine.key_display(
                    self.engine._hotkeys[self._capturing_name]),
                fg=GREEN, bg=KEYCAP)
        self._capturing_name = name
        self._keycap_btns[name].configure(text="PRESS…", fg="#0E0E0E", bg=GREEN)
        self.engine.begin_capture(name)

    def _on_slider(self, val):
        self.engine.set_speed(int(float(val)))
        self._refresh_speed_label(int(float(val)))

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("Macro files", "*.json")],
            initialfile="macro.json")
        if path:
            self.engine.save(path)

    def _load_from(self):
        path = filedialog.askopenfilename(
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")])
        if path:
            self.engine.load(path)

    # ----- view refresh --------------------------------------------------- #
    def _refresh_state(self):
        if self.engine.recording:
            self.btn_record.configure(text="■ STOP REC", bg=RED, fg="#0E0E0E")
            self._set_pill("● RECORDING", RED)
        else:
            self.btn_record.configure(text="● RECORD", bg=PANEL2, fg=TEXT)

        if self.engine.playing:
            self.btn_play.configure(text="■ STOP", bg=GREEN, fg="#0E0E0E")
            self._set_pill("▶ PLAYING", GREEN)
        else:
            self.btn_play.configure(text="▶ PLAY", bg=PANEL2, fg=TEXT)

        if not self.engine.recording and not self.engine.playing:
            n = len(self.engine.events)
            self._set_pill(f"READY · {n} events" if n else "IDLE",
                           GREEN if n else MUTED)

    def _set_pill(self, text, color):
        self.status_pill.configure(text=text, bg=color)

    def _refresh_speed_label(self, percent):
        percent = max(1, int(percent))
        self.speed_val.configure(text=f"{percent}%   (x{100.0/percent:.2f})")

    def _append_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg.strip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ----- shutdown ------------------------------------------------------- #
    def _on_close(self):
        try:
            self.engine.stop_listeners()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    root = tk.Tk()
    MacroGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
