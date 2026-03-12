import pandas as pd
import numpy as np
from backend.backtesting.metrics import compute_metrics


def run_mean_reversion(df: pd.DataFrame, params: dict) -> dict:
    lookback      = int(params.get("lookback_period",    20))
    dev_threshold = float(params.get("deviation_threshold", 2.0))
    stop_loss     = float(params.get("stop_loss",   0.02))
    take_profit   = float(params.get("take_profit", 0.04))

    df = df.copy()
    df["sma"]      = df["close"].rolling(window=lookback).mean()
    df["std"]      = df["close"].rolling(window=lookback).std()
    df["upper_bb"] = df["sma"] + (df["std"] * dev_threshold)
    df["lower_bb"] = df["sma"] - (df["std"] * dev_threshold)

    buy_signals  = []
    sell_signals = []
    trades       = []

    in_trade    = False
    entry_price = 0.0
    entry_time  = None
    trade_type  = ""

    for i in range(1, len(df)):
        current = df.iloc[i]

        if pd.isna(current["sma"]):
            continue

        # ── Check SL / TP ─────────────────────────────────────────────────────
        if in_trade:
            pl_pct = (current["close"] - entry_price) / entry_price
            hit_sl = pl_pct <= -stop_loss
            hit_tp = pl_pct >=  take_profit

            if trade_type == "BUY" and (hit_sl or hit_tp):
                in_trade = False
                trades.append({
                    "entry_price": entry_price,
                    "exit_price":  current["close"],
                    "type":        "BUY",
                    "pnl":         pl_pct,
                    "entry_time":  entry_time,
                    "exit_time":   current["time"],
                    "stop_loss":   entry_price * (1 - stop_loss),
                    "take_profit": entry_price * (1 + take_profit),
                })
            elif trade_type == "SELL" and (hit_sl or hit_tp):
                in_trade = False
                trades.append({
                    "entry_price": entry_price,
                    "exit_price":  current["close"],
                    "type":        "SELL",
                    "pnl":         -pl_pct,
                    "entry_time":  entry_time,
                    "exit_time":   current["time"],
                    "stop_loss":   entry_price * (1 + stop_loss),
                    "take_profit": entry_price * (1 - take_profit),
                })

        # ── Bollinger Band signals ─────────────────────────────────────────────
        if current["close"] < current["lower_bb"]:
            buy_signals.append({"time": current["time"], "price": current["close"]})
            if not in_trade:
                in_trade    = True
                entry_price = current["close"]
                entry_time  = current["time"]
                trade_type  = "BUY"
        elif current["close"] > current["upper_bb"]:
            sell_signals.append({"time": current["time"], "price": current["close"]})
            if not in_trade:
                in_trade    = True
                entry_price = current["close"]
                entry_time  = current["time"]
                trade_type  = "SELL"

    # ── Bollinger Band indicator series ───────────────────────────────────────
    def series_to_points(col):
        return [
            {"time": int(row["time"]), "value": round(float(row[col]), 6)}
            for _, row in df.iterrows()
            if pd.notna(row[col])
        ]

    indicators = {
        "sma":      series_to_points("sma"),
        "upper_bb": series_to_points("upper_bb"),
        "lower_bb": series_to_points("lower_bb"),
    }

    return {
        "buy_signals":  buy_signals,
        "sell_signals": sell_signals,
        "trades":       trades,
        "indicators":   indicators,
        "metrics":      compute_metrics(trades),
    }
