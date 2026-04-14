#!/usr/bin/env python3
"""Statistics window showing most common Czech grammar mistakes as a bar chart."""
import os
import json
import tkinter as tk
from tkinter import ttk

MISTAKES_FILE = os.path.expanduser("~/.cj_correcter/mistakes.json")
BG = "#f5f5f7"
FG = "#1d1d1f"
SUBTLE = "#6e6e73"
RED = "#ff3b30"
GREEN = "#34c759"
FONT = "Helvetica Neue"


def load_mistakes():
    if os.path.exists(MISTAKES_FILE):
        with open(MISTAKES_FILE) as f:
            return json.load(f)
    return {}


def show():
    mistakes = load_mistakes()
    sorted_items = sorted(mistakes.items(), key=lambda x: x[1]["count"], reverse=True)[:15]

    root = tk.Tk()
    root.title("Grammar Mistakes Statistics")
    root.configure(bg=BG)
    W, H = 720, 500
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
    root.resizable(True, True)

    style = ttk.Style()
    try:
        style.theme_use("aqua")
    except Exception:
        pass

    # ── header ──
    header = tk.Frame(root, bg=BG)
    header.pack(fill="x", padx=24, pady=(22, 4))
    tk.Label(header, text="Most Common Mistakes",
             font=(FONT, 17, "bold"), bg=BG, fg=FG).pack(side="left")
    total = sum(d["count"] for _, d in sorted_items)
    tk.Label(header, text=f"Total corrections: {total}",
             font=(FONT, 11), bg=BG, fg=SUBTLE).pack(side="right", pady=(4, 0))

    ttk.Separator(root).pack(fill="x", padx=24, pady=(4, 0))

    if not sorted_items:
        tk.Label(
            root,
            text="No mistakes recorded yet.\nStart correcting text to see statistics.",
            font=(FONT, 14), bg=BG, fg=SUBTLE, justify="center",
        ).pack(expand=True)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=20)
        root.mainloop()
        return

    # ── try matplotlib chart ──
    try:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        labels = [f"{w}\n→ {d['correction']}" for w, d in sorted_items]
        counts = [d["count"] for _, d in sorted_items]

        fig, ax = plt.subplots(figsize=(8.5, 3.8))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor("#ffffff")

        bars = ax.bar(range(len(labels)), counts, color=RED, alpha=0.82, width=0.55)

        for bar, cnt in zip(bars, counts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.08,
                str(cnt),
                ha="center", va="bottom",
                fontsize=9, fontweight="bold", color=FG,
            )

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=8.5, color=FG)
        ax.set_ylabel("Number of mistakes", color=SUBTLE, fontsize=10)
        ax.tick_params(colors=SUBTLE)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#d2d2d7")
        ax.spines["bottom"].set_color("#d2d2d7")
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.tight_layout(pad=1.4)

        canvas = FigureCanvasTkAgg(fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=24, pady=12)

    except ImportError:
        # ── fallback: plain tkinter rows ──
        frame = tk.Frame(root, bg=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=12)

        # Header row
        hdr = tk.Frame(frame, bg="#e5e5ea")
        hdr.pack(fill="x", pady=(0, 4))
        for col, w, anchor in [("Mistake", 18, "w"), ("Correction", 18, "w"), ("Count", 8, "center")]:
            tk.Label(hdr, text=col, font=(FONT, 11, "bold"),
                     bg="#e5e5ea", fg=FG, width=w, anchor=anchor).pack(side="left", padx=8, pady=6)

        # Max bar width reference
        max_count = sorted_items[0][1]["count"] if sorted_items else 1

        for word, data in sorted_items:
            row = tk.Frame(frame, bg="white", relief="flat")
            row.pack(fill="x", pady=1)

            tk.Label(row, text=word, font=(FONT, 12), bg="white", fg=RED,
                     width=18, anchor="w", overstrike=True).pack(side="left", padx=8, pady=5)
            tk.Label(row, text=data["correction"], font=(FONT, 12, "bold"), bg="white", fg=GREEN,
                     width=18, anchor="w").pack(side="left", padx=8)

            cnt = data["count"]
            bar_w = max(4, int(120 * cnt / max_count))
            bar_frame = tk.Frame(row, bg=BG)
            bar_frame.pack(side="left", fill="x", expand=True, padx=8)
            tk.Frame(bar_frame, bg=RED, height=14, width=bar_w).pack(side="left", pady=5)
            tk.Label(bar_frame, text=f" {cnt}", font=(FONT, 11, "bold"),
                     bg=BG, fg=FG).pack(side="left")

    # ── close button ──
    ttk.Button(root, text="Close", command=root.destroy).pack(pady=(4, 20))
    root.mainloop()


if __name__ == "__main__":
    show()
