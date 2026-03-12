"""
Strategy Insights
─────────────────────────────────────────────────────────────────────────────
Statistical analysis of backtest results → natural-language insight strings.
Analyses:
  1. Win rate per market regime
  2. PnL distribution by trade type (BUY / SELL)
  3. RSI range at entry for winning vs losing trades
  4. Trade duration patterns
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List, Dict, Any

# Re-use RSI helper without importing the full trade_scoring module
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _nearest_index(times: np.ndarray, target: float) -> int:
    diffs = np.abs(times - target)
    return int(np.argmin(diffs))


def generate_insights(candles: List[Dict], trades: List[Dict]) -> List[str]:
    """
    Return a list of insight strings derived from statistical analysis of the
    backtest trade list. Requires at least 3 trades to produce meaningful output.
    """
    insights: List[str] = []

    if len(trades) < 3:
        return ["Not enough trades for statistical analysis (need ≥ 3)."]

    df = pd.DataFrame(candles)
    df.columns = df.columns.str.lower()
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    times = df["time"].values if "time" in df.columns else np.arange(len(df))
    close = df["close"]
    rsi   = _rsi(close, 14).values

    trade_records = []
    for t in trades:
        entry_t = t.get("entry_time") or t.get("exit_time")
        exit_t  = t.get("exit_time")  or t.get("entry_time")
        if entry_t is None:
            continue
        idx     = _nearest_index(times, entry_t)
        rsi_val = rsi[idx] if 0 <= idx < len(rsi) else np.nan
        duration = (exit_t - entry_t) if (exit_t and entry_t) else 0
        trade_records.append({
            "pnl":       float(t.get("pnl", 0)),
            "type":      t.get("type", "BUY"),
            "regime":    t.get("regime", "Unknown"),
            "rsi":       rsi_val,
            "duration":  duration,
            "score":     float(t.get("trade_score", 0.5)),
        })

    tr = pd.DataFrame(trade_records)
    wins   = tr[tr["pnl"] > 0]
    losses = tr[tr["pnl"] <= 0]

    # ── 1. Overall win rate ───────────────────────────────────────────────────
    wr = len(wins) / len(tr) * 100
    insights.append(
        f"Overall win rate is {wr:.1f}% across {len(tr)} trades."
    )

    # ── 2. Trade type breakdown ───────────────────────────────────────────────
    for ttype in ["BUY", "SELL"]:
        sub = tr[tr["type"] == ttype]
        if len(sub) == 0:
            continue
        sub_wr = len(sub[sub["pnl"] > 0]) / len(sub) * 100
        avg_pnl = sub["pnl"].mean() * 100
        direction = "positive" if avg_pnl >= 0 else "negative"
        insights.append(
            f"{ttype} trades: {sub_wr:.0f}% win rate, avg PnL {avg_pnl:+.2f}% "
            f"({direction} expectancy)."
        )

    # ── 3. RSI at entry: winners vs losers ────────────────────────────────────
    if not tr["rsi"].isna().all():
        win_rsi  = wins["rsi"].dropna()
        loss_rsi = losses["rsi"].dropna()
        if len(win_rsi) > 1 and len(loss_rsi) > 1:
            win_med  = win_rsi.median()
            loss_med = loss_rsi.median()
            if win_med < 40:
                insights.append(
                    f"Winning trades typically entered with RSI ≈ {win_med:.0f} "
                    f"(oversold zone) vs {loss_med:.0f} for losing trades — "
                    "strategy favours oversold reversals."
                )
            elif win_med > 60:
                insights.append(
                    f"Winning trades entered with RSI ≈ {win_med:.0f} "
                    f"(momentum zone) vs {loss_med:.0f} for losing trades — "
                    "strategy benefits from trending conditions."
                )
            else:
                insights.append(
                    f"Winning trade RSI at entry: median {win_med:.0f} "
                    f"(vs {loss_med:.0f} for losses)."
                )

    # ── 4. Regime analysis (if regime data embedded in trades) ───────────────
    regimes = tr["regime"].unique()
    if len(regimes) > 1 or (len(regimes) == 1 and regimes[0] != "Unknown"):
        best_regime = None
        best_wr     = -1
        for reg in regimes:
            sub = tr[tr["regime"] == reg]
            if len(sub) < 2:
                continue
            cur_wr = len(sub[sub["pnl"] > 0]) / len(sub) * 100
            if cur_wr > best_wr:
                best_wr     = cur_wr
                best_regime = reg
        worst_regime = None
        worst_wr     = 101
        for reg in regimes:
            sub = tr[tr["regime"] == reg]
            if len(sub) < 2:
                continue
            cur_wr = len(sub[sub["pnl"] > 0]) / len(sub) * 100
            if cur_wr < worst_wr:
                worst_wr     = cur_wr
                worst_regime = reg
        if best_regime and best_regime != worst_regime:
            insights.append(
                f"Best performance in {best_regime} market regime "
                f"({best_wr:.0f}% win rate) vs weakest in {worst_regime} "
                f"({worst_wr:.0f}% win rate)."
            )

    # ── 5. Trade duration ────────────────────────────────────────────────────
    if tr["duration"].abs().sum() > 0:
        win_dur  = wins["duration"].median()  / 3600  # hours
        loss_dur = losses["duration"].median() / 3600
        if win_dur > 0 and loss_dur > 0:
            if win_dur < loss_dur:
                insights.append(
                    f"Winning trades resolve faster ({win_dur:.1f} h median) than "
                    f"losing trades ({loss_dur:.1f} h median) — losses tend to be held too long."
                )
            else:
                insights.append(
                    f"Winning trades held longer ({win_dur:.1f} h) than "
                    f"losses ({loss_dur:.1f} h median)."
                )

    # ── 6. AI score correlation ───────────────────────────────────────────────
    if tr["score"].std() > 0.01:
        win_score  = wins["score"].mean()
        loss_score = losses["score"].mean()
        if win_score > loss_score + 0.05:
            insights.append(
                f"AI confidence score correlates with outcome — winners averaged "
                f"{win_score:.2f} vs {loss_score:.2f} for losing trades."
            )

    # ── 7. Drawdown warning ───────────────────────────────────────────────────
    consecutive_losses = 0
    max_consec = 0
    for pnl in tr["pnl"]:
        if pnl <= 0:
            consecutive_losses += 1
            max_consec = max(max_consec, consecutive_losses)
        else:
            consecutive_losses = 0
    if max_consec >= 3:
        insights.append(
            f"Maximum consecutive losing streak: {max_consec} trades — "
            "consider tightening drawdown controls."
        )

    return insights if insights else ["No significant patterns detected in this backtest."]
