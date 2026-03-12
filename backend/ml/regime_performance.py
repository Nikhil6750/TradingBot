"""
Regime Performance Breakdown
Assigns a market regime to every trade and computes per-regime statistics.
Reuses the regime_detection feature engineering for consistency.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from backend.ml.regime_detection import engineer_features, generate_labels, REGIME_LABELS

# ── Advice templates ─────────────────────────────────────────────────────────

def _regime_insight(breakdown: dict) -> str:
    """Generate a 1-2 sentence summary of best/worst performing regime."""
    if not breakdown:
        return "Not enough trade data to generate insights yet."

    # Sort regimes by avg_return
    sorted_by_return = sorted(
        [(r, d) for r, d in breakdown.items() if d["trades"] > 0],
        key=lambda x: x[1]["avg_return"],
        reverse=True,
    )
    if not sorted_by_return:
        return "No active regimes detected across recorded trades."

    best  = sorted_by_return[0]
    worst = sorted_by_return[-1]

    parts = [
        f"This strategy performs best during {best[0]} markets "
        f"(avg return: {best[1]['avg_return']*100:+.1f}%)."
    ]
    if len(sorted_by_return) > 1 and worst[1]["avg_return"] < 0:
        parts.append(
            f"It struggles during {worst[0]} conditions "
            f"(avg return: {worst[1]['avg_return']*100:+.1f}%)."
        )
    return " ".join(parts)


# ── Core function ─────────────────────────────────────────────────────────────

def compute_regime_performance(df: pd.DataFrame, trades: list[dict]) -> dict:
    """
    Assign a regime label to each trade and aggregate per-regime metrics.

    Returns
    -------
    {
      "breakdown": {
        "Trending":        {"trades": int, "avg_return": float, "win_rate": float},
        "Sideways":        {...},
        "High Volatility": {...},
        "Low Volatility":  {...},
      },
      "insight": str,
    }
    """
    df = df.copy()
    df.columns = df.columns.str.lower()

    #  Need at least 80 bars for meaningful regime labelling
    if len(df) < 80 or not trades:
        return {
            "breakdown": {},
            "insight": "Not enough data for a regime breakdown (need ≥ 80 bars and at least 1 trade).",
        }

    # 1. Generate per-bar regime labels using the same pipeline as regime_detection
    feat   = engineer_features(df)
    labels = generate_labels(feat)          # pd.Series aligned to feat's index

    # Build a time → regime mapping
    times = df["time"].values if "time" in df.columns else np.arange(len(df), dtype=float)
    # feat index maps into df rows that survived dropna; reassemble to full df index
    feat_idx = feat.index.tolist()

    regime_per_bar = {}
    for loc, regime_int in zip(feat_idx, labels.values):
        regime_per_bar[times[loc] if loc < len(times) else loc] = REGIME_LABELS[int(regime_int)]

    # 2. Assign regime to each trade (nearest bar by entry_time)
    time_arr    = np.array(list(regime_per_bar.keys()), dtype=float)
    regime_arr  = np.array(list(regime_per_bar.values()))

    def lookup_regime(entry_t):
        if len(time_arr) == 0:
            return "Unknown"
        idx = int(np.argmin(np.abs(time_arr - float(entry_t))))
        return regime_arr[idx]

    enriched = []
    for t in trades:
        entry_t = t.get("entry_time") or t.get("exit_time") or 0
        enriched.append({**t, "regime": lookup_regime(entry_t)})

    # 3. Group and compute per-regime stats
    all_regimes = list(REGIME_LABELS.values())
    breakdown: dict[str, dict] = {}

    for regime_name in all_regimes:
        group = [t for t in enriched if t.get("regime") == regime_name]
        if not group:
            continue
        pnls    = [t["pnl"] for t in group]
        wins    = [p for p in pnls if p > 0]
        breakdown[regime_name] = {
            "trades":     len(group),
            "avg_return": round(float(np.mean(pnls)), 6),
            "win_rate":   round(len(wins) / len(pnls), 4) if pnls else 0.0,
        }

    return {
        "breakdown": breakdown,
        "insight":   _regime_insight(breakdown),
    }
