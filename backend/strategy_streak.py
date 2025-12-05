# backend/strategy_streak.py
from __future__ import annotations
from typing import List, Dict
import pandas as pd


def detect_streak_alerts(df: pd.DataFrame) -> List[Dict]:
    """
    Reimplements your Pine logic (alerts fire on continuation after a 4+ bar streak).
    Required df columns: time (datetime-like), open, high, low, close
    """
    # Basic sanity
    if not {"time", "open", "high", "low", "close"}.issubset(df.columns):
        raise ValueError("DataFrame must contain columns: time, open, high, low, close")

    # Ensure datetime
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])

    streak = 0
    streak_bullish = None
    streak_open = None
    waiting = False
    opposite = 0

    alerts: List[Dict] = []

    for i in range(len(df)):
        O = float(df.iloc[i]["open"])
        H = float(df.iloc[i]["high"])
        L = float(df.iloc[i]["low"])
        C = float(df.iloc[i]["close"])
        t = df.iloc[i]["time"]

        this_bullish = C > O
        alert = False

        if not waiting:
            if streak == 0:
                streak = 1
                streak_bullish = this_bullish
                streak_open = O  # anchor when streak starts
            elif this_bullish == streak_bullish:
                streak += 1
                # To match your Pine exactly (tighter guard), uncomment:
                # streak_open = O
            else:
                if streak >= 4:
                    waiting = True
                    opposite = 1
                    # Immediate guard check
                    guard_break = (streak_bullish and L <= streak_open) or ((not streak_bullish) and H >= streak_open)
                    if guard_break:
                        # invalidate → flip to new streak
                        streak = 1
                        streak_bullish = this_bullish
                        streak_open = O
                        waiting = False
                        opposite = 0
                else:
                    streak = 1
                    streak_bullish = this_bullish
                    streak_open = O
        else:
            if this_bullish != streak_bullish:
                opposite += 1
                if opposite > 2:
                    # cancel and flip
                    streak = 1
                    streak_bullish = this_bullish
                    waiting = False
                    opposite = 0
                    streak_open = O
            else:
                if opposite == 2:
                    guard_break = (streak_bullish and L <= streak_open) or ((not streak_bullish) and H >= streak_open)
                    if guard_break:
                        # invalidate
                        streak = 1
                        streak_bullish = this_bullish
                        waiting = False
                        opposite = 0
                        streak_open = O
                    else:
                        alert = True
                elif opposite == 1:
                    alert = True

                # reset after decision
                if alert or (opposite in (1, 2)):
                    streak = 1
                    streak_bullish = this_bullish
                    waiting = False
                    opposite = 0
                    streak_open = O

        if alert:
            alerts.append({
                "index": i,
                "time": t,
                "side": "LONG" if streak_bullish else "SHORT",
                "anchor_open": float(streak_open),
            })

    return alerts


def backtest_streak(
    df: pd.DataFrame,
    hour_from: int,
    hour_to: int,
    horizon_bars: int = 3,
) -> Dict:
    """
    Turns alerts into simple trades:
      - TAKE alert only if alert.time.hour in [hour_from, hour_to]
      - Enter next bar open; exit after `horizon_bars` bars (direction check)
      - WIN if exit moved in trade direction vs entry; else LOSS
    Returns summary + alerts list (for UI table).
    """
    alerts = detect_streak_alerts(df)
    rows: List[Dict] = []
    wins = 0
    losses = 0
    taken = 0

    for a in alerts:
        i = a["index"]
        t = a["time"]
        side = a["side"]
        take = (int(hour_from) <= int(t.hour) <= int(hour_to))

        entry_i = i + 1
        exit_i = i + 1 + horizon_bars

        entry = None
        exitp = None
        outcome = None
        reason = None

        if not take:
            reason = "outside_hours"
        elif entry_i >= len(df) or exit_i >= len(df):
            take = False
            reason = "insufficient_bars"
        else:
            taken += 1
            entry = float(df.iloc[entry_i]["open"])
            exitp = float(df.iloc[exit_i]["close"])
            if side == "LONG":
                outcome = "WIN" if exitp > entry else "LOSS"
            else:
                outcome = "WIN" if exitp < entry else "LOSS"
            if outcome == "WIN":
                wins += 1
            else:
                losses += 1

        rows.append({
            "time": t.isoformat(),
            "side": side,
            "take": take,
            "reason": reason,
            "entry_index": entry_i if entry is not None else None,
            "entry_price": entry,
            "exit_index": exit_i if exitp is not None else None,
            "exit_price": exitp,
            "outcome": outcome,
        })

    win_rate = (wins / taken * 100.0) if taken else 0.0

    return {
        "ok": True,
        "summary": {
            "trades": taken,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
        },
        "alerts": rows,
    }
