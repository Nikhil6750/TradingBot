import pandas as pd
from backend.backtesting.metrics import compute_metrics


def run_breakout(df: pd.DataFrame, params: dict) -> dict:
    breakout_period = int(params.get("lookback_period", params.get("breakout_period", 20)))
    breakout_threshold = float(params.get("breakout_threshold", 0.0))
    volume_conf     = bool(params.get("volume_confirmation", False))
    stop_loss       = float(params.get("stop_loss",   0.02))
    take_profit     = float(params.get("take_profit", 0.04))

    if breakout_period <= 1:
        raise ValueError("Lookback period must be greater than 1.")
    if breakout_threshold < 0:
        raise ValueError("Breakout threshold must be zero or greater.")

    df = df.copy()
    df["highest_high"] = df["high"].rolling(window=breakout_period).max().shift(1)
    df["lowest_low"]   = df["low"].rolling(window=breakout_period).min().shift(1)
    df["avg_volume"]   = df["volume"].rolling(window=breakout_period).mean().shift(1)
    threshold_multiplier = breakout_threshold / 100.0

    buy_signals  = []
    sell_signals = []
    trades       = []

    in_trade    = False
    entry_price = 0.0
    entry_time  = None
    trade_type  = ""

    for i in range(1, len(df)):
        current = df.iloc[i]

        if pd.isna(current["highest_high"]):
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

        # ── Breakout signals ──────────────────────────────────────────────────
        vol_ok = (current["volume"] > current["avg_volume"]) if volume_conf else True
        upper_breakout_level = current["highest_high"] * (1 + threshold_multiplier)
        lower_breakout_level = current["lowest_low"] * (1 - threshold_multiplier)

        if current["close"] > upper_breakout_level and vol_ok:
            buy_signals.append({"time": current["time"], "price": current["close"]})
            if not in_trade:
                in_trade    = True
                entry_price = current["close"]
                entry_time  = current["time"]
                trade_type  = "BUY"
        elif current["close"] < lower_breakout_level and vol_ok:
            sell_signals.append({"time": current["time"], "price": current["close"]})
            if not in_trade:
                in_trade    = True
                entry_price = current["close"]
                entry_time  = current["time"]
                trade_type  = "SELL"

    # ── Channel indicator series ──────────────────────────────────────────────
    def series_to_points(col):
        return [
            {"time": int(row["time"]), "value": round(float(row[col]), 6)}
            for _, row in df.iterrows()
            if pd.notna(row[col])
        ]

    indicators = {
        "highest_high": series_to_points("highest_high"),
        "lowest_low":   series_to_points("lowest_low"),
        "breakout_threshold": breakout_threshold,
    }

    return {
        "buy_signals":  buy_signals,
        "sell_signals": sell_signals,
        "trades":       trades,
        "indicators":   indicators,
        "metrics":      compute_metrics(trades),
    }
