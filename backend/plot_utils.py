# plot_utils.py
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional, List

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt


def render_candles_png(
    df,                       # DataFrame indexed by datetime, cols: open, high, low, close
    center_time: datetime,    # the alert candle time
    window: int = 30,         # total candles to show
    theme: str = "dark",      # "dark" | "light"
    title: str = "",
    subtitle: Optional[str] = None,
    entry_price: Optional[float] = None,
    exit_price: Optional[float] = None,
    outcome: Optional[str] = None,   # "WIN" | "LOSS" | None
    side: Optional[str] = None,      # "LONG" | "SHORT" | None
    notes: Optional[List[str]] = None,
    dpi: int = 180,
) -> bytes:
    """Return PNG bytes of a clean candlestick panel that matches a dark trading UI."""
    # THEME
    if theme == "dark":
        bg = "#0b0b0b"       # app background
        panel = "#121212"    # card background
        grid = "#252525"
        fg = "#e5e5e5"
        green = "#16a34a"
        red = "#ef4444"
        accent = "#f59e0b"
    else:
        bg = "#ffffff"
        panel = "#f8f8f8"
        grid = "#e5e7eb"
        fg = "#111827"
        green = "#15803d"
        red = "#dc2626"
        accent = "#b45309"

    # locate center index
    if center_time not in df.index:
        idx = df.index.get_indexer([center_time], method="nearest")[0]
    else:
        idx = df.index.get_loc(center_time)

    half = window // 2
    start = max(0, idx - half)
    end = min(len(df), start + window)
    start = max(0, end - window)
    data = df.iloc[start:end].copy()

    plt.close("all")
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=dpi, facecolor=bg)
    ax.set_facecolor(panel)

    xs = range(len(data))
    o = data["open"].values
    h = data["high"].values
    l = data["low"].values
    c = data["close"].values
    up = c >= o
    dn = ~up

    # wicks
    ax.vlines(xs, l, h, color=fg, linewidth=0.75, alpha=0.7, zorder=1)

    # bodies
    body_w = 0.55
    ax.bar([x for x, u in zip(xs, up) if u],
           (c - o)[up], bottom=o[up],
           width=body_w, color=green, edgecolor="none", zorder=2)
    ax.bar([x for x, d in zip(xs, dn) if d],
           (c - o)[dn], bottom=o[dn],
           width=body_w, color=red, edgecolor="none", zorder=2)

    # highlight the alert candle
    if start <= idx < end:
        rel_x = idx - start
        ax.axvline(rel_x, color=accent, linestyle="--", linewidth=1.2, alpha=0.85, zorder=0)

    # entry/exit
    if entry_price is not None:
        ax.axhline(entry_price, color=accent, linestyle=(0, (4, 4)), linewidth=1.2, alpha=0.9)
    if exit_price is not None:
        ax.axhline(exit_price, color=accent, linestyle=(0, (2, 3)), linewidth=1.0, alpha=0.9)

    # axes / ticks
    ax.grid(color=grid, linestyle="-", linewidth=0.6, alpha=0.5)
    ax.set_xlim(-0.5, len(data) - 0.5)
    ax.tick_params(axis="x", colors=fg, labelsize=8)
    ax.tick_params(axis="y", colors=fg, labelsize=9)

    # sparse x tick labels
    ticks = list(range(0, len(data), max(1, len(data) // 6)))
    if ticks and ticks[-1] != len(data)-1:
        ticks[-1] = len(data)-1
    ax.set_xticks(ticks)
    ax.set_xticklabels([data.index[i].strftime("%Y-%m-%d\n%H:%M") for i in ticks])

    header = title
    if side: header = f"{header}  •  {side}"
    if outcome: header = f"{header}  •  {outcome}"
    ax.set_title(header, color=fg, fontsize=12, loc="left", pad=10)

    if subtitle:
        ax.text(0.99, 1.02, subtitle, transform=ax.transAxes,
                ha="right", va="bottom",
                fontsize=9, color=fg,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=panel, edgecolor=grid, alpha=0.9))

    if notes:
        ax.text(0.01, 0.02, "\n".join(f"• {n}" for n in notes),
                transform=ax.transAxes, ha="left", va="bottom", fontsize=8, color=fg,
                bbox=dict(boxstyle="round,pad=0.35", facecolor=panel, edgecolor=grid, alpha=0.9))

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=bg, dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
