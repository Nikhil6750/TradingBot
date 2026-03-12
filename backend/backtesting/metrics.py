"""
Shared metrics helper for all AlgoTradeX strategy engines.
"""
from __future__ import annotations

import numpy as np
from typing import List, Dict, Any, Optional


def compute_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute a full set of performance metrics from a list of trade dicts.
    Each trade must have pnl (float, fractional e.g. 0.023 = +2.3%).
    """
    EMPTY = {
        "total_trades":  0,
        "win_rate":      0.0,
        "total_return":  0.0,
        "avg_trade":     0.0,
        "best_trade":    0.0,
        "worst_trade":   0.0,
        "profit_factor": 0.0,
        "sharpe_ratio":  None,   # None → display "—"
        "max_drawdown":  0.0,
        "expectancy":    0.0,
    }

    if not trades:
        return EMPTY

    pnls = np.array([float(t.get("pnl", 0)) for t in trades])
    n    = len(pnls)

    # ── Win / loss split ──────────────────────────────────────────────────────
    wins   = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    win_rate  = len(wins) / n if n else 0.0
    avg_win   = float(wins.mean())   if len(wins)   > 0 else 0.0
    avg_loss  = float(losses.mean()) if len(losses) > 0 else 0.0  # negative

    # ── Total / avg / best / worst ────────────────────────────────────────────
    total_return = float(pnls.sum())
    avg_trade    = float(pnls.mean())
    best_trade   = float(pnls.max())
    worst_trade  = float(pnls.min())

    # ── Profit factor ─────────────────────────────────────────────────────────
    gross_profit = float(wins.sum())
    gross_loss   = float(abs(losses.sum()))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )

    # ── Sharpe (annualised, equity-curve based) ───────────────────────────────
    # Require at least 5 trades; use multiplicative equity curve pct changes.
    if n >= 5:
        equity   = np.cumprod(1 + pnls)           # multiplicative NAV
        ret_pct  = np.diff(equity) / equity[:-1]  # period-to-period returns
        if len(ret_pct) > 1 and ret_pct.std() > 1e-10:
            sharpe_ratio: Optional[float] = round(
                float(ret_pct.mean() / ret_pct.std() * np.sqrt(252)), 4
            )
        else:
            sharpe_ratio = None
    else:
        sharpe_ratio = None   # "Not enough trades"

    # ── Max drawdown (peak-to-trough on multiplicative equity) ────────────────
    equity_full  = np.concatenate([[1.0], np.cumprod(1 + pnls)])
    peaks        = np.maximum.accumulate(equity_full)
    dd           = equity_full / peaks - 1          # negative numbers
    max_drawdown = round(float(dd.min()), 6)        # most negative value

    # ── Expectancy ────────────────────────────────────────────────────────────
    loss_rate  = 1.0 - win_rate
    expectancy = round(win_rate * avg_win - loss_rate * abs(avg_loss), 6)

    return {
        "total_trades":  n,
        "win_rate":      round(win_rate, 4),
        "total_return":  round(total_return, 6),
        "avg_trade":     round(avg_trade, 6),
        "best_trade":    round(best_trade, 6),
        "worst_trade":   round(worst_trade, 6),
        "profit_factor": profit_factor,
        "sharpe_ratio":  sharpe_ratio,   # None when < 5 trades
        "max_drawdown":  max_drawdown,   # negative fraction
        "expectancy":    expectancy,
    }
