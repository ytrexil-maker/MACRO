"""
Fortnite Clip & Inject -- GUI
=============================

A dark, Razer-Synapse-style control panel for the clip engine in
``clip_audio.py``. Pick your audio devices from dropdowns, bind each hotkey by
clicking a key-cap and pressing a key, and use the big buttons to clip, ghost
play (only you hear) or inject play (your teammates hear it through your
existing mic -- no new microphone is ever created).

Run:
    pip install sounddevice numpy pynput   (pyttsx3 optional)
    python clip_gui.py
"""

import queue
import tkinter as tk
from tkinter import filedialog, font as tkfont

from clip_audio import (CONFIG, ClipEngine, list_devices, find_device,
                        auto_inject_device)


# --------------------------------------------------------------------------- #
#  Theme (matches macro_gui.py)
# --------------------------------------------------------------------------- #

BG = "#0E0E0E"
PANEL = "#161616"
PANEL2 = "#1E1E1E"
EDGE = "#2A2A2A"
GREEN = "#44D62C"
GREEN_DIM = "#2C8C1C"
RED = "#E03E2F"
BLUE = "#3AA0FF"
TEXT = "#EDEDED"
MUTED = "#7E7E7E"
KEYCAP = "#202020"

BINDINGS = [
    ("clip_last_key", "CLIP LAST"),
    ("record_key", "RECORD / STOP"),
    ("ghost_play_key", "GHOST PLAY"),
    ("inject_play_key", "INJECT PLAY"),
    ("stop_play_key", "STOP PLAY"),
    ("quit_key", "QUIT"),
]


class ClipGUI:
    def __init__(self, root):
        self.root = root
        self.engine = ClipEngine(CONFIG)

        self.ui_queue = queue.Queue()
        self._caps = {}
        self._devices = list_devices()

        self._build_fonts()
        self._build_ui()
        self._wire_engine()

        self.engine.start()
        self._pump()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- fonts ---------------------------------------------------------- #
    def _build_fonts(self):
        fam = "Segoe UI"
        try:
            if fam not in set(tkfont.families()):
                fam = "Helvetica"
        except Exception:
            fam = "Helvetica"
        self.f_title = tkfont.Font(family=fam, size=18, weight="bold")
        self.f_sub = tkfont.Font(family=fam, size=9)
        self.f_label = tkfont.Font(family=fam, size=10, weight="bold")
        self.f_key = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.f_big = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_log = tkfont.Font(family="Consolas", size=9)

    # ----- layout --------------------------------------------------------- #
    def _build_ui(self):
        self.root.title("CLIP & INJECT")
        self.root.configure(bg=BG)
        self.root.geometry("1040x700")
        self.root.minsize(980, 660)

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=18, pady=(16, 8))
        bar = tk.Frame(header, bg=GREEN, width=6, height=42)
        bar.pack(side="left", padx=(0, 12))
        bar.pack_propagate(False)
        titlebox = tk.Frame(header, bg=BG)
        titlebox.pack(side="left")
        tk.Label(titlebox, text="CLIP & INJECT", fg=TEXT, bg=BG,
                 font=self.f_title).pack(anchor="w")
        tk.Label(titlebox, text="BACKGROUND AUDIO CLIPPER  /  MIC INJECTOR  (NO NEW MIC)",
                 fg=GREEN, bg=BG, font=self.f_sub).pack(anchor="w")
        self.status_pill = tk.Label(header, text="IDLE", fg="#0E0E0E", bg=MUTED,
                                    font=self.f_label, padx=14, pady=4)
        self.status_pill.pack(side="right")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=8)

        col_dev = self._panel(body, "AUDIO DEVICES")
        col_dev.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._build_devices(col_dev)

        col_ctrl = tk.Frame(body, bg=BG)
        col_ctrl.pack(side="left", fill="both", expand=True, padx=8)
        self._build_controls(col_ctrl)

        col_keys = self._panel(body, "HOTKEYS")
        col_keys.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._build_keys(col_keys)

        logwrap = self._panel(self.root, "ACTIVITY")
        logwrap.pack(fill="both", expand=False, padx=18, pady=(0, 16))
        self.log = tk.Text(logwrap, height=7, bg="#0A0A0A", fg=GREEN,
                           insertbackground=GREEN, relief="flat",
                           font=self.f_log, bd=0, padx=10, pady=8,
                           highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log.configure(state="disabled")

    def _panel(self, parent, title):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                         highlightbackground=EDGE)
        tk.Label(frame, text=title, fg=GREEN, bg=PANEL, font=self.f_sub,
                 anchor="w").pack(fill="x", padx=12, pady=(10, 6))
        return frame

    # ----- device pickers ------------------------------------------------- #
    def _dev_options(self, want_output):
        """Return (labels, index_map) for input or output devices."""
        labels = ["(system default)"]
        index_map = [None]
        for i, d in enumerate(self._devices):
            chans = d["max_output_channels"] if want_output else d["max_input_channels"]
            if chans > 0:
                labels.append(f"[{i}] {d['name']}")
                index_map.append(i)
        return labels, index_map

    def _build_devices(self, panel):
        self._dev_vars = {}

        def add_picker(key, label, want_output, note):
            tk.Label(panel, text=label, fg=TEXT, bg=PANEL, font=self.f_label,
                     anchor="w").pack(fill="x", padx=12, pady=(8, 0))
            labels, index_map = self._dev_options(want_output)
            var = tk.StringVar()
            # Preselect current config / auto-detected value.
            cur = self.engine.cfg[key]
            cur_idx = find_device(cur, want_output=want_output)
            if key == "inject_device" and cur_idx is None:
                cur_idx = auto_inject_device()
            sel = 0
            if cur_idx is not None and cur_idx in index_map:
                sel = index_map.index(cur_idx)
            var.set(labels[sel])
            opt = tk.OptionMenu(panel, var, *labels,
                                command=lambda v, k=key, m=index_map, l=labels:
                                self._on_device_pick(k, v, m, l))
            opt.configure(bg=KEYCAP, fg=GREEN, activebackground=GREEN,
                          activeforeground="#0E0E0E", relief="flat", bd=0,
                          highlightthickness=1, highlightbackground=EDGE,
                          font=self.f_sub, anchor="w")
            opt["menu"].configure(bg=PANEL2, fg=TEXT, activebackground=GREEN,
                                  activeforeground="#0E0E0E", font=self.f_sub)
            opt.pack(fill="x", padx=12, pady=(2, 0))
            tk.Label(panel, text=note, fg=MUTED, bg=PANEL, font=self.f_sub,
                     justify="left", anchor="w", wraplength=290).pack(
                fill="x", padx=12, pady=(0, 4))
            self._dev_vars[key] = var
            # Apply the preselected value to the engine now.
            self._on_device_pick(key, labels[sel], index_map, labels)

        add_picker("capture_device", "CAPTURE FROM (what gets clipped)", True,
                   "On Windows this can be an OUTPUT, captured via loopback, so "
                   "you clip the game audio you hear. Default = default output.")
        add_picker("monitor_device", "MONITOR / GHOST (only you hear)", True,
                   "Your headphones. Ghost play and 'hear while injecting' go here.")
        add_picker("inject_device", "INJECT INTO (loops to your mic)", True,
                   "The virtual output your existing mic loops from -- e.g. "
                   "Voicemod / CABLE Input. Point Fortnite's mic at the matching "
                   "device. No new mic is created.")

        tk.Button(panel, text="↻ REFRESH DEVICES", command=self._refresh_devices,
                  font=self.f_label, fg=GREEN, bg=KEYCAP, activebackground=GREEN,
                  activeforeground="#0E0E0E", relief="flat", bd=0, pady=8,
                  cursor="hand2", highlightthickness=1,
                  highlightbackground=EDGE).pack(fill="x", padx=12, pady=(6, 12))

    def _on_device_pick(self, key, value, index_map, labels):
        try:
            sel = labels.index(value)
        except ValueError:
            sel = 0
        self.engine.cfg[key] = index_map[sel]

    def _refresh_devices(self):
        self._devices = list_devices()
        self._append_log(f"[DEV] Found {len(self._devices)} devices. Reopen the "
                         "app to repopulate the dropdowns if one is missing.")

    # ----- controls ------------------------------------------------------- #
    def _build_controls(self, parent):
        row = self._panel(parent, "CLIP LENGTH")
        row.pack(fill="x")
        self.sec_val = tk.Label(row, text="", fg=GREEN, bg=PANEL, font=self.f_big)
        self.sec_val.pack(anchor="w", padx=12)
        self.sec_scale = tk.Scale(
            row, from_=1, to=30, orient="horizontal", showvalue=False,
            bg=PANEL, fg=TEXT, troughcolor="#0A0A0A", highlightthickness=0,
            activebackground=GREEN, bd=0, sliderrelief="flat",
            command=self._on_seconds)
        self.sec_scale.set(int(self.engine.cfg["clip_seconds"]))
        self.sec_scale.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(row, text="how many seconds 'CLIP LAST' grabs from the buffer",
                 fg=MUTED, bg=PANEL, font=self.f_sub).pack(
            anchor="w", padx=12, pady=(0, 10))
        self._refresh_seconds(int(self.engine.cfg["clip_seconds"]))

        self.btn_clip = self._big_button(parent, "◉ CLIP LAST", GREEN,
                                         self._clip_last)
        self.btn_clip.pack(fill="x", pady=(12, 8))
        self.btn_record = self._big_button(parent, "● RECORD", PANEL2,
                                           self.engine.toggle_recording)
        self.btn_record.pack(fill="x", pady=(0, 12))

        self.btn_ghost = self._big_button(parent, "🎧 GHOST PLAY  (only you)",
                                          PANEL2, self.engine.ghost_play)
        self.btn_ghost.pack(fill="x", pady=(0, 8))
        self.btn_inject = self._big_button(parent, "📢 INJECT PLAY  (everyone)",
                                           PANEL2, self.engine.inject_play)
        self.btn_inject.pack(fill="x", pady=(0, 8))
        self.btn_stop = self._big_button(parent, "■ STOP PLAY", PANEL2,
                                         self.engine.stop_playback)
        self.btn_stop.pack(fill="x", pady=(0, 12))

        io = tk.Frame(parent, bg=BG)
        io.pack(fill="x")
        self._mini_button(io, "LOAD CLIP…", self._load_clip).pack(
            side="left", expand=True, fill="x", padx=(0, 5))
        self._mini_button(io, "OPEN FOLDER", self._open_folder).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

        mon = tk.Frame(parent, bg=BG)
        mon.pack(fill="x", pady=(10, 0))
        self.mon_var = tk.BooleanVar(value=bool(self.engine.cfg["monitor_while_injecting"]))
        tk.Checkbutton(mon, text="Also hear injected clips in my headphones",
                       variable=self.mon_var, command=self._toggle_monitor,
                       bg=BG, fg=TEXT, selectcolor=PANEL2, activebackground=BG,
                       activeforeground=GREEN, font=self.f_sub,
                       highlightthickness=0, bd=0).pack(anchor="w")

    # ----- hotkeys -------------------------------------------------------- #
    def _build_keys(self, panel):
        tk.Label(panel, text="Click a key, then press the key to assign.",
                 fg=MUTED, bg=PANEL, font=self.f_sub, anchor="w").pack(
            fill="x", padx=12, pady=(0, 8))
        for name, label in BINDINGS:
            r = tk.Frame(panel, bg=PANEL)
            r.pack(fill="x", padx=12, pady=5)
            tk.Label(r, text=label, fg=TEXT, bg=PANEL, font=self.f_label,
                     anchor="w", width=14).pack(side="left")
            cap = tk.Button(
                r, text=self.engine.key_display(self.engine._hotkeys[name]),
                font=self.f_key, fg=GREEN, bg=KEYCAP, activebackground=GREEN,
                activeforeground="#0E0E0E", relief="flat", bd=0, width=8, pady=6,
                cursor="hand2", highlightthickness=1, highlightbackground=EDGE,
                command=lambda n=name: self._begin_capture(n))
            cap.pack(side="right")
            self._caps[name] = cap

        tk.Label(panel,
                 text="These are GLOBAL hotkeys -- they fire even while Fortnite "
                      "is focused, like a GeForce overlay.",
                 fg=MUTED, bg=PANEL, font=self.f_sub, justify="left",
                 anchor="w", wraplength=290).pack(fill="x", padx=12, pady=(12, 10))

    # ----- reusable widgets ----------------------------------------------- #
    def _big_button(self, parent, text, bg, cmd):
        return tk.Button(parent, text=text, command=cmd, font=self.f_big,
                         fg=TEXT if bg == PANEL2 else "#0E0E0E", bg=bg,
                         activebackground=GREEN_DIM, activeforeground="#0E0E0E",
                         relief="flat", bd=0, pady=14, cursor="hand2",
                         highlightthickness=1, highlightbackground=EDGE)

    def _mini_button(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, font=self.f_label,
                         fg=GREEN, bg=KEYCAP, activebackground=GREEN,
                         activeforeground="#0E0E0E", relief="flat", bd=0,
                         pady=8, cursor="hand2", highlightthickness=1,
                         highlightbackground=EDGE)

    # ----- engine wiring -------------------------------------------------- #
    def _wire_engine(self):
        self.engine.on_status = lambda m: self.ui_queue.put(("log", m))
        self.engine.on_state_change = lambda: self.ui_queue.put(("state", None))
        self.engine.on_capture_done = lambda t, d: self.ui_queue.put(
            ("capture", (t, d)))

    def _pump(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "state":
                    self._refresh_state()
                elif kind == "capture":
                    self._on_capture_done(*payload)
        except queue.Empty:
            pass
        if self.engine._stop_flag.is_set():
            self._on_close()
            return
        self.root.after(60, self._pump)

    # ----- actions -------------------------------------------------------- #
    def _clip_last(self):
        self.engine.clip_last(self.sec_scale.get())

    def _begin_capture(self, name):
        self._caps[name].configure(text="PRESS…", fg="#0E0E0E", bg=GREEN)
        self.engine.begin_capture(name)

    def _on_capture_done(self, target, disp):
        if target in self._caps:
            self._caps[target].configure(text=disp, fg=GREEN, bg=KEYCAP)

    def _on_seconds(self, val):
        v = int(float(val))
        self.engine.cfg["clip_seconds"] = float(v)
        self._refresh_seconds(v)

    def _toggle_monitor(self):
        self.engine.cfg["monitor_while_injecting"] = bool(self.mon_var.get())

    def _load_clip(self):
        path = filedialog.askopenfilename(
            filetypes=[("WAV clips", "*.wav"), ("All files", "*.*")],
            initialdir=self.engine.cfg["clip_dir"])
        if path:
            self.engine.load_clip(path)

    def _open_folder(self):
        import os
        import subprocess
        folder = os.path.abspath(self.engine.cfg["clip_dir"])
        try:
            if hasattr(os, "startfile"):
                os.startfile(folder)  # Windows
            elif __import__("sys").platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            self._append_log(f"[FOLDER] {folder}  ({exc})")

    # ----- view refresh --------------------------------------------------- #
    def _refresh_state(self):
        if self.engine.recording:
            self.btn_record.configure(text="■ STOP REC", bg=RED, fg="#0E0E0E")
            self._set_pill("● RECORDING", RED)
        else:
            self.btn_record.configure(text="● RECORD", bg=PANEL2, fg=TEXT)
        if self.engine.playing:
            self._set_pill("▶ PLAYING", GREEN)
        elif not self.engine.recording:
            has = self.engine.last_clip is not None
            self._set_pill("READY · clip loaded" if has else "IDLE",
                           GREEN if has else MUTED)

    def _set_pill(self, text, color):
        self.status_pill.configure(text=text, bg=color)

    def _refresh_seconds(self, v):
        self.sec_val.configure(text=f"{v}s")

    def _log_msg(self, m):
        self.ui_queue.put(("log", m))

    def _append_log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg.strip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ----- shutdown ------------------------------------------------------- #
    def _on_close(self):
        try:
            self.engine.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    root = tk.Tk()
    ClipGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
