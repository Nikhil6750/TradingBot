from __future__ import annotations

import pandas as pd

from backend.backtesting.metrics import compute_metrics


def _resolve_period(params: dict, primary: str, fallback: str, default: int) -> int:
    value = params.get(primary, params.get(fallback, default))
    period = int(value)
    if period <= 0:
        raise ValueError("Moving average periods must be positive integers.")
    return period


def _resolve_ma_type(params: dict) -> str:
    ma_type = str(params.get("ma_type", "EMA")).strip().upper()
    if ma_type not in {"EMA", "SMA"}:
        raise ValueError("ma_type must be EMA or SMA.")
    return ma_type


def _moving_average(series: pd.Series, period: int, ma_type: str) -> pd.Series:
    if ma_type == "SMA":
        return series.rolling(window=period).mean()
    return series.ewm(span=period, adjust=False).mean()


def run_ma_crossover(df: pd.DataFrame, params: dict) -> dict:
    short_period = _resolve_period(params, "fast_period", "short_period", 10)
    if "fast_period" not in params and "short_period" not in params:
        short_period = _resolve_period(params, "short_ma_period", "short_ma_period", 10)

    long_period = _resolve_period(params, "slow_period", "long_period", 30)
    if "slow_period" not in params and "long_period" not in params:
        long_period = _resolve_period(params, "long_ma_period", "long_ma_period", 30)
    ma_type = _resolve_ma_type(params)

    if short_period >= long_period:
        raise ValueError("Fast MA period must be smaller than slow MA period.")

    working = df.copy()
    working["fast_ma"] = _moving_average(working["close"], short_period, ma_type)
    working["slow_ma"] = _moving_average(working["close"], long_period, ma_type)

    buy_signals = []
    sell_signals = []
    trades = []

    position = None
    entry_price = None
    entry_time = None

    for index in range(1, len(working)):
        previous = working.iloc[index - 1]
        current = working.iloc[index]

        if pd.isna(previous["fast_ma"]) or pd.isna(previous["slow_ma"]):
            continue
        if pd.isna(current["fast_ma"]) or pd.isna(current["slow_ma"]):
            continue

        crossed_up = previous["fast_ma"] <= previous["slow_ma"] and current["fast_ma"] > current["slow_ma"]
        crossed_down = previous["fast_ma"] >= previous["slow_ma"] and current["fast_ma"] < current["slow_ma"]

        if crossed_up:
            buy_signals.append({
                "time": int(current["time"]),
                "price": float(current["close"]),
                "type": "BUY",
            })
            if position == "SELL" and entry_price is not None and entry_time is not None:
                pnl = (entry_price - float(current["close"])) / entry_price
                trades.append({
                    "entry_time": int(entry_time),
                    "exit_time": int(current["time"]),
                    "entry_price": float(entry_price),
                    "exit_price": float(current["close"]),
                    "type": "SELL",
                    "pnl": float(pnl),
                })
            position = "BUY"
            entry_price = float(current["close"])
            entry_time = int(current["time"])
        elif crossed_down:
            sell_signals.append({
                "time": int(current["time"]),
                "price": float(current["close"]),
                "type": "SELL",
            })
            if position == "BUY" and entry_price is not None and entry_time is not None:
                pnl = (float(current["close"]) - entry_price) / entry_price
                trades.append({
                    "entry_time": int(entry_time),
                    "exit_time": int(current["time"]),
                    "entry_price": float(entry_price),
                    "exit_price": float(current["close"]),
                    "type": "BUY",
                    "pnl": float(pnl),
                })
            position = "SELL"
            entry_price = float(current["close"])
            entry_time = int(current["time"])

    indicators = {
        "fast_ma": [
            {"time": int(row["time"]), "value": round(float(row["fast_ma"]), 6)}
            for _, row in working.iterrows()
            if pd.notna(row["fast_ma"])
        ],
        "slow_ma": [
            {"time": int(row["time"]), "value": round(float(row["slow_ma"]), 6)}
            for _, row in working.iterrows()
            if pd.notna(row["slow_ma"])
        ],
        "ma_type": ma_type,
    }

    return {
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "trades": trades,
        "metrics": compute_metrics(trades),
        "indicators": indicators,
    }
