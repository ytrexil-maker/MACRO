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
* Multiple named macro **slots** -- add / rename / remove as many as you like.
* Each slot gets its own **trigger key** and a **HOLD TO REPEAT** switch: tap
  the key to fire once, or (with repeat on) hold it to loop the macro until you
  let go.
* Big RECORD and PLAY toggles that operate on the selected slot.
* Click any key-cap, then press a key to (re)bind it -- global hotkeys and slot
  triggers alike.
* A speed slider: one percentage scales every interval so mouse + keyboard
  stay in proportion (100% = original, 50% = 2x faster, 200% = half speed).
* Save / Load your whole workspace (all slots) to a file you choose.
* A live activity log.

The actual recording / playback / audio cues all live in the engine; this is
just a front-end for it.
"""

import queue
import tkinter as tk
from tkinter import filedialog, simpledialog, font as tkfont

from fortnite_macro import CONFIG, MacroEngine


# --------------------------------------------------------------------------- #
#  Theme (Razer Synapse-ish: near-black panels, signature green accent)
# --------------------------------------------------------------------------- #

BG = "#0E0E0E"
PANEL = "#161616"
PANEL2 = "#1E1E1E"
EDGE = "#2A2A2A"
GREEN = "#44D62C"
GREEN_DIM = "#2C8C1C"
RED = "#E03E2F"
TEXT = "#EDEDED"
MUTED = "#7E7E7E"
KEYCAP = "#202020"

# Friendly labels for each *global* engine binding.
GLOBAL_BINDINGS = [
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

        self._global_caps = {}      # binding name -> key-cap Button
        self._suppress_select = False

        self._build_fonts()
        self._build_ui()
        self._wire_engine()
        self._refresh_slots()
        self._refresh_state()

        self.engine.start_listeners()
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
        self.f_big = tkfont.Font(family=fam, size=14, weight="bold")
        self.f_log = tkfont.Font(family="Consolas", size=9)
        self.f_list = tkfont.Font(family="Consolas", size=10)

    # ----- layout --------------------------------------------------------- #
    def _build_ui(self):
        self.root.title("MACRO SYNAPSE")
        self.root.configure(bg=BG)
        self.root.geometry("1020x680")
        self.root.minsize(960, 640)

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
        tk.Label(titlebox, text="MULTI-SLOT INPUT RECORDER  /  CUSTOM KEY BINDINGS",
                 fg=GREEN, bg=BG, font=self.f_sub).pack(anchor="w")
        self.status_pill = tk.Label(header, text="IDLE", fg="#0E0E0E", bg=MUTED,
                                    font=self.f_label, padx=14, pady=4)
        self.status_pill.pack(side="right")

        # ---- body: three columns ----
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=8)

        col_slots = self._panel(body, "MACRO SLOTS")
        col_slots.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._build_slots(col_slots)

        col_ctrl = tk.Frame(body, bg=BG)
        col_ctrl.pack(side="left", fill="both", expand=True, padx=8)
        self._build_controls(col_ctrl)

        col_keys = self._panel(body, "GLOBAL KEYS")
        col_keys.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self._build_global_keys(col_keys)

        # ---- log ----
        logwrap = self._panel(self.root, "ACTIVITY")
        logwrap.pack(fill="both", expand=False, padx=18, pady=(0, 16))
        self.log = tk.Text(logwrap, height=6, bg="#0A0A0A", fg=GREEN,
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

    # ----- slots column --------------------------------------------------- #
    def _build_slots(self, panel):
        listwrap = tk.Frame(panel, bg=EDGE)
        listwrap.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.slot_list = tk.Listbox(
            listwrap, bg="#0A0A0A", fg=TEXT, font=self.f_list, bd=0,
            relief="flat", highlightthickness=0, activestyle="none",
            selectbackground=GREEN, selectforeground="#0E0E0E", height=7)
        self.slot_list.pack(fill="both", expand=True, padx=1, pady=1)
        self.slot_list.bind("<<ListboxSelect>>", self._on_slot_select)

        btns = tk.Frame(panel, bg=PANEL)
        btns.pack(fill="x", padx=12, pady=(0, 8))
        self._mini_button(btns, "+ ADD", self._add_slot).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        self._mini_button(btns, "RENAME", self._rename_slot).pack(
            side="left", expand=True, fill="x", padx=4)
        self._mini_button(btns, "REMOVE", self._remove_slot).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        # selected-slot detail
        detail = tk.Frame(panel, bg=PANEL2, highlightthickness=1,
                          highlightbackground=EDGE)
        detail.pack(fill="x", padx=12, pady=(2, 12))

        trow = tk.Frame(detail, bg=PANEL2)
        trow.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(trow, text="TRIGGER KEY", fg=TEXT, bg=PANEL2,
                 font=self.f_label).pack(side="left")
        self.trigger_cap = tk.Button(
            trow, text="—", font=self.f_key, fg=GREEN, bg=KEYCAP,
            activebackground=GREEN, activeforeground="#0E0E0E", relief="flat",
            bd=0, width=10, pady=6, cursor="hand2", highlightthickness=1,
            highlightbackground=EDGE, command=self._bind_trigger)
        self.trigger_cap.pack(side="right")

        hrow = tk.Frame(detail, bg=PANEL2)
        hrow.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(hrow, text="HOLD TO REPEAT", fg=TEXT, bg=PANEL2,
                 font=self.f_label).pack(side="left")
        self.hold_btn = tk.Button(
            hrow, text="ON", font=self.f_key, fg="#0E0E0E", bg=GREEN,
            activebackground=GREEN, relief="flat", bd=0, width=6, pady=6,
            cursor="hand2", highlightthickness=1, highlightbackground=EDGE,
            command=self._toggle_hold)
        self.hold_btn.pack(side="right")

        tk.Label(panel, text="The selected slot is what RECORD captures into.\n"
                             "Tap a trigger to play once; hold it to repeat.",
                 fg=MUTED, bg=PANEL, font=self.f_sub, justify="left",
                 anchor="w").pack(fill="x", padx=12, pady=(0, 10))

    # ----- controls column ------------------------------------------------ #
    def _build_controls(self, parent):
        self.active_label = tk.Label(parent, text="", fg=GREEN, bg=BG,
                                     font=self.f_label, anchor="w")
        self.active_label.pack(fill="x", pady=(2, 4))

        self.btn_record = self._big_button(parent, "● RECORD",
                                           self.engine.toggle_recording)
        self.btn_record.pack(fill="x", pady=(0, 10))
        self.btn_play = self._big_button(parent, "▶ PLAY",
                                         self.engine.toggle_playback)
        self.btn_play.pack(fill="x", pady=(0, 14))

        speed = self._panel(parent, "PLAYBACK SPEED")
        speed.pack(fill="x")
        self.speed_val = tk.Label(speed, text="", fg=GREEN, bg=PANEL,
                                  font=self.f_big)
        self.speed_val.pack(anchor="w", padx=12)
        self.speed_scale = tk.Scale(
            speed, from_=10, to=400, orient="horizontal", showvalue=False,
            bg=PANEL, fg=TEXT, troughcolor="#0A0A0A", highlightthickness=0,
            activebackground=GREEN, bd=0, sliderrelief="flat", length=220,
            command=self._on_slider)
        self.speed_scale.set(int(self.engine.cfg["interval_percent"]))
        self.speed_scale.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(speed, text="interval %  (lower = faster, higher = slower)",
                 fg=MUTED, bg=PANEL, font=self.f_sub).pack(
            anchor="w", padx=12, pady=(0, 10))
        self._refresh_speed_label(int(self.engine.cfg["interval_percent"]))

        io = self._panel(parent, "WORKSPACE FILE")
        io.pack(fill="x", pady=(12, 0))
        iorow = tk.Frame(io, bg=PANEL)
        iorow.pack(fill="x", padx=12, pady=(0, 12))
        self._mini_button(iorow, "SAVE ALL…", self._save_as).pack(
            side="left", expand=True, fill="x", padx=(0, 5))
        self._mini_button(iorow, "LOAD…", self._load_from).pack(
            side="left", expand=True, fill="x", padx=(5, 0))

    # ----- global keys column --------------------------------------------- #
    def _build_global_keys(self, panel):
        tk.Label(panel, text="Click a key, then press the key to assign.",
                 fg=MUTED, bg=PANEL, font=self.f_sub, anchor="w").pack(
            fill="x", padx=12, pady=(0, 8))
        for name, label in GLOBAL_BINDINGS:
            row = tk.Frame(panel, bg=PANEL)
            row.pack(fill="x", padx=12, pady=4)
            tk.Label(row, text=label, fg=TEXT, bg=PANEL, font=self.f_label,
                     anchor="w", width=15).pack(side="left")
            cap = tk.Button(
                row, text=self.engine.key_display(self.engine._hotkeys[name]),
                font=self.f_key, fg=GREEN, bg=KEYCAP,
                activebackground=GREEN, activeforeground="#0E0E0E",
                relief="flat", bd=0, width=8, pady=6, cursor="hand2",
                highlightthickness=1, highlightbackground=EDGE,
                command=lambda n=name: self._begin_capture(n))
            cap.pack(side="right")
            self._global_caps[name] = cap

    # ----- reusable widgets ----------------------------------------------- #
    def _big_button(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, font=self.f_big,
                         fg=TEXT, bg=PANEL2, activebackground=GREEN_DIM,
                         activeforeground="#0E0E0E", relief="flat", bd=0,
                         pady=18, cursor="hand2", highlightthickness=1,
                         highlightbackground=EDGE)

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
        self.engine.on_speed_change = lambda p: self.ui_queue.put(("speed", p))
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
                    self._refresh_slots()
                elif kind == "speed":
                    self._refresh_speed_label(payload)
                    if int(self.speed_scale.get()) != int(payload):
                        self.speed_scale.set(int(payload))
                elif kind == "capture":
                    self._on_capture_done(*payload)
        except queue.Empty:
            pass
        if self.engine._stop_flag.is_set():
            self._on_close()
            return
        self.root.after(60, self._pump)

    # ----- slot actions --------------------------------------------------- #
    def _add_slot(self):
        name = simpledialog.askstring("New macro", "Name:", parent=self.root)
        self.engine.add_slot(name)
        self._refresh_slots()

    def _rename_slot(self):
        idx = self.engine.active
        name = simpledialog.askstring(
            "Rename macro", "Name:", parent=self.root,
            initialvalue=self.engine.slots[idx]["name"])
        if name:
            self.engine.rename_slot(idx, name)
            self._refresh_slots()

    def _remove_slot(self):
        self.engine.remove_slot(self.engine.active)
        self._refresh_slots()

    def _on_slot_select(self, _evt):
        if self._suppress_select:
            return
        sel = self.slot_list.curselection()
        if sel:
            self.engine.set_active(sel[0])
            self._refresh_slot_detail()

    def _bind_trigger(self):
        idx = self.engine.active
        self.trigger_cap.configure(text="PRESS…", fg="#0E0E0E", bg=GREEN)
        self.engine.begin_capture(("slot", idx))

    def _toggle_hold(self):
        idx = self.engine.active
        new = not self.engine.slots[idx]["hold_repeat"]
        self.engine.set_hold_repeat(idx, new)
        self._refresh_slot_detail()

    # ----- global binding capture ----------------------------------------- #
    def _begin_capture(self, name):
        self._global_caps[name].configure(text="PRESS…", fg="#0E0E0E", bg=GREEN)
        self.engine.begin_capture(name)

    def _on_capture_done(self, target, disp):
        if isinstance(target, tuple) and target[0] == "slot":
            self._refresh_slots()
        elif target in self._global_caps:
            self._global_caps[target].configure(text=disp, fg=GREEN, bg=KEYCAP)

    # ----- speed / file --------------------------------------------------- #
    def _on_slider(self, val):
        self.engine.set_speed(int(float(val)))
        self._refresh_speed_label(int(float(val)))

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("Macro files", "*.json")],
            initialfile="macros.json")
        if path:
            self.engine.save_workspace(path)

    def _load_from(self):
        path = filedialog.askopenfilename(
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")])
        if path:
            self.engine.load_workspace(path)
            self.speed_scale.set(int(self.engine.cfg["interval_percent"]))
            self._refresh_slots()

    # ----- view refresh --------------------------------------------------- #
    def _refresh_slots(self):
        self._suppress_select = True
        self.slot_list.delete(0, "end")
        for s in self.engine.slots:
            trig = self.engine.key_display(s["trigger"]) if s["trigger"] else "—"
            rep = "↻" if s["hold_repeat"] else " "
            self.slot_list.insert(
                "end", f" {s['name']:<14}{trig:>5} {rep}  {len(s['events'])}ev")
        self.slot_list.selection_clear(0, "end")
        self.slot_list.selection_set(self.engine.active)
        self.slot_list.see(self.engine.active)
        self._suppress_select = False
        self._refresh_slot_detail()

    def _refresh_slot_detail(self):
        idx = self.engine.active
        slot = self.engine.slots[idx]
        self.trigger_cap.configure(
            text=self.engine.key_display(slot["trigger"]) if slot["trigger"]
            else "SET",
            fg=GREEN, bg=KEYCAP)
        if slot["hold_repeat"]:
            self.hold_btn.configure(text="ON", fg="#0E0E0E", bg=GREEN)
        else:
            self.hold_btn.configure(text="OFF", fg=MUTED, bg=KEYCAP)
        self.active_label.configure(text=f"RECORD INTO ►  {slot['name']}")

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
