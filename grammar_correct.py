#!/usr/bin/env python3
"""
Grammar correction pop-up window.
Called by the Automator service with selected text via stdin.
Prints corrected (or original) text to stdout so Automator can replace the selection.
"""
import sys
import os
import json
import threading
import re
import difflib
import tkinter as tk
from tkinter import ttk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MISTAKES_FILE = os.path.expanduser("~/.cj_correcter/mistakes.json")

# ── helpers ──────────────────────────────────────────────────────────────────

def save_mistake(original_word, correction):
    os.makedirs(os.path.dirname(MISTAKES_FILE), exist_ok=True)
    data = {}
    if os.path.exists(MISTAKES_FILE):
        with open(MISTAKES_FILE) as f:
            data = json.load(f)
    entry = data.setdefault(original_word, {"count": 0, "correction": correction})
    entry["count"] += 1
    entry["correction"] = correction
    with open(MISTAKES_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── popup window ──────────────────────────────────────────────────────────────

class CorrectionWindow:
    FONT  = "Helvetica Neue"
    BG    = "#f5f5f7"
    CARD  = "#ffffff"
    BORDER= "#d2d2d7"
    RED   = "#ff3b30"
    GREEN = "#34c759"
    FG    = "#1d1d1f"
    SUBTLE= "#6e6e73"
    W     = 420

    def __init__(self, original_text):
        self.original  = original_text
        self.corrected = original_text
        self.mistakes  = []
        self.accepted  = False

        self.root = tk.Tk()
        self.root.overrideredirect(True)        # no title bar → clean popup
        self.root.configure(bg=self.BORDER)     # 1-px border colour
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # Position: top-right corner, just below the menu bar
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        x  = sw - self.W - 16
        y  = 36                                 # below macOS menu bar
        self.root.geometry(f"{self.W}x160+{x}+{y}")

        self._build_ui()
        self._make_draggable()
        self._bring_to_front()
        self._start_correction()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("aqua")
        except Exception:
            pass

        # outer 1-px border via the root bg; inner card
        card = tk.Frame(self.root, bg=self.BG, padx=0, pady=0)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        # ── drag handle / status bar ──
        self._drag_bar = tk.Frame(card, bg=self.BG, height=36)
        self._drag_bar.pack(fill="x")
        self._drag_bar.pack_propagate(False)

        self.status_icon = tk.Label(
            self._drag_bar, text="⏳",
            font=(self.FONT, 12), bg=self.BG, fg=self.SUBTLE,
        )
        self.status_icon.pack(side="left", padx=(14, 4), pady=8)

        self.status_label = tk.Label(
            self._drag_bar, text="Checking grammar…",
            font=(self.FONT, 12), bg=self.BG, fg=self.SUBTLE,
        )
        self.status_label.pack(side="left", pady=8)

        # close ×
        close_btn = tk.Label(
            self._drag_bar, text="✕",
            font=(self.FONT, 11), bg=self.BG, fg=self.SUBTLE, cursor="hand2",
        )
        close_btn.pack(side="right", padx=12, pady=8)
        close_btn.bind("<Button-1>", lambda e: self._cancel())

        # ── thin separator ──
        tk.Frame(card, bg=self.BORDER, height=1).pack(fill="x")

        # ── progress bar (hidden after load) ──
        self.progress = ttk.Progressbar(card, mode="indeterminate", length=self.W - 2)
        self.progress.pack(fill="x", padx=0, pady=0)
        self.progress.start(12)

        # ── text area (compact, max 5 lines) ──
        self.text_widget = tk.Text(
            card,
            font=(self.FONT, 13),
            bg=self.CARD, fg=self.FG,
            relief="flat", bd=0,
            padx=14, pady=10,
            wrap="word",
            height=4,
            state="disabled",
            highlightthickness=0,
        )
        self.text_widget.pack(fill="x", padx=0, pady=0)

        self.text_widget.tag_config(
            "mistake",   foreground=self.RED,   overstrike=True, font=(self.FONT, 13))
        self.text_widget.tag_config(
            "correction",foreground=self.GREEN,                  font=(self.FONT, 13, "bold"))
        self.text_widget.tag_config(
            "normal",    foreground=self.FG)

        # ── bottom bar: legend + buttons ──
        tk.Frame(card, bg=self.BORDER, height=1).pack(fill="x")

        bottom = tk.Frame(card, bg=self.BG, height=40)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        # legend (tiny tk.Text so overstrike tag works)
        leg = tk.Text(
            bottom, height=1, bg=self.BG, bd=0, relief="flat",
            font=(self.FONT, 9), state="normal", cursor="arrow",
            highlightthickness=0,
        )
        leg.pack(side="left", padx=(14, 0), pady=10)
        leg.tag_config("m", foreground=self.RED,   overstrike=True, font=(self.FONT, 9))
        leg.tag_config("c", foreground=self.GREEN, font=(self.FONT, 9, "bold"))
        leg.tag_config("s", foreground=self.SUBTLE)
        leg.insert("end", "mistake", "m")
        leg.insert("end", " → ", "s")
        leg.insert("end", "correction", "c")
        leg.config(state="disabled", width=20)

        self.cancel_btn = ttk.Button(bottom, text="Cancel",  command=self._cancel, width=8)
        self.cancel_btn.pack(side="right", padx=(4, 12), pady=6)

        self.accept_btn = ttk.Button(
            bottom, text="Accept", command=self._accept, state="disabled", width=8)
        self.accept_btn.pack(side="right", padx=(0, 4), pady=6)

        # bind Escape → cancel
        self.root.bind("<Escape>", lambda e: self._cancel())

    # ── drag-to-move ──────────────────────────────────────────────────────────

    def _make_draggable(self):
        def on_press(e):
            self._dx = e.x_root - self.root.winfo_x()
            self._dy = e.y_root - self.root.winfo_y()

        def on_drag(e):
            self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

        self._drag_bar.bind("<Button-1>",   on_press)
        self._drag_bar.bind("<B1-Motion>",  on_drag)
        self.status_icon.bind("<Button-1>", on_press)
        self.status_icon.bind("<B1-Motion>",on_drag)
        self.status_label.bind("<Button-1>",on_press)
        self.status_label.bind("<B1-Motion>",on_drag)

    # ── bring to front (works in every app, full-screen, all Spaces) ─────────

    def _bring_to_front(self):
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        # Schedule Cocoa-level float after Tk draws the window
        self.root.after(0, self._cocoa_float)

    def _cocoa_float(self):
        """
        Make the popup visible above full-screen apps.

        Two things are required:
        1. NSApp.activateIgnoringOtherApps_ — activates this Python process so
           macOS pulls its windows into the currently active Space (incl. full-screen).
        2. High window level + MoveToActiveSpace + FullScreenAuxiliary — keeps the
           window on top once it is in the right Space.

        Level 1000 = NSScreenSaverWindowLevel, reliably above full-screen content.
        Behaviour flags:
          2   NSWindowCollectionBehaviorMoveToActiveSpace  – follow the user
          256 NSWindowCollectionBehaviorFullScreenAuxiliary – allowed in FS Space
        """
        try:
            from AppKit import NSApp
            NSApp.activateIgnoringOtherApps_(True)   # pull into current Space
            for win in NSApp.windows():
                win.setLevel_(1000)                  # NSScreenSaverWindowLevel
                win.setCollectionBehavior_(2 | 256)  # MoveToActiveSpace | FullScreenAux
                win.makeKeyAndOrderFront_(None)
        except Exception:
            pass

    # ── correction logic ──────────────────────────────────────────────────────

    def _start_correction(self):
        sys.path.insert(0, SCRIPT_DIR)
        from ollama_client import correct_czech

        def _work():
            result = correct_czech(self.original)
            self.root.after(0, lambda: self._show_result(result))

        threading.Thread(target=_work, daemon=True).start()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _diff_ops(self):
        """Word-level diff opcodes between original and corrected."""
        return list(difflib.SequenceMatcher(
            None,
            self.original.split(),
            self.corrected.split(),
            autojunk=False,
        ).get_opcodes())

    # ── result display ────────────────────────────────────────────────────────

    def _show_result(self, result):
        self.corrected = result.get("corrected", self.original)
        self.mistakes  = result.get("mistakes", [])   # kept for save_mistake

        self.progress.stop()
        self.progress.pack_forget()

        ops   = self._diff_ops()
        n_ops = sum(1 for tag, *_ in ops if tag != "equal")

        if n_ops == 0:
            self.status_icon.config(text="✅")
            self.status_label.config(text="No mistakes found", fg=self.GREEN)
            self._render_plain(self.original)
            self.accept_btn.config(state="normal", text="OK")
        else:
            self.status_icon.config(text="🔴")
            self.status_label.config(
                text=f"{n_ops} mistake{'s' if n_ops != 1 else ''} found",
                fg=self.RED,
            )
            self._render_diff(ops)
            self.accept_btn.config(state="normal")

        # resize to fit after widgets have updated
        self.root.after_idle(self._fit_height)

    def _fit_height(self):
        self.root.update_idletasks()
        self.root.geometry(f"{self.W}x{self.root.winfo_reqheight()}")

    def _render_plain(self, text):
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("end", text, "normal")
        self.text_widget.config(state="disabled")

    def _render_diff(self, ops):
        """Render word-level diff: red-strikethrough originals, green corrections."""
        orig_words = self.original.split()
        corr_words = self.corrected.split()

        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", "end")

        ins = self.text_widget.insert   # shorthand
        need_space = [False]           # list so inner assignments are visible

        def gap():
            if need_space[0]:
                ins("end", " ", "normal")
            need_space[0] = True

        for tag, i1, i2, j1, j2 in ops:
            if tag == "equal":
                chunk = " ".join(orig_words[i1:i2])
                if chunk:
                    gap(); ins("end", chunk, "normal")

            elif tag == "replace":
                gap()
                ins("end", " ".join(orig_words[i1:i2]), "mistake")
                ins("end", " ")
                ins("end", " ".join(corr_words[j1:j2]), "correction")

            elif tag == "delete":
                gap(); ins("end", " ".join(orig_words[i1:i2]), "mistake")

            elif tag == "insert":
                gap(); ins("end", " ".join(corr_words[j1:j2]), "correction")

        self.text_widget.config(state="disabled")

    # ── actions ───────────────────────────────────────────────────────────────

    def _accept(self):
        for m in self.mistakes:
            orig = m.get("original", "").strip()
            corr = m.get("correction", "").strip()
            if orig:
                save_mistake(orig, corr)
        self.accepted = True
        self.root.destroy()

    def _cancel(self):
        self.accepted = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.corrected if self.accepted else self.original


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    elif len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "Já jdem do školy a mám maš rád čokolády."  # demo

    if not text:
        sys.exit(0)

    if len(text) > 8000:
        text = text[:8000]

    win = CorrectionWindow(text)
    result = win.run()
    print(result, end="")


if __name__ == "__main__":
    main()
