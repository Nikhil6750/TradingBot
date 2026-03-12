import pandas as pd
from backend.backtesting.metrics import compute_metrics


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs    = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def run_rsi_reversal(df: pd.DataFrame, params: dict) -> dict:
    rsi_period  = int(params.get("rsi_length", params.get("rsi_period", 14)))
    oversold    = float(params.get("oversold", params.get("oversold_level", 30)))
    overbought  = float(params.get("overbought", params.get("overbought_level", 70)))
    stop_loss   = float(params.get("stop_loss",   0.02))
    take_profit = float(params.get("take_profit", 0.04))

    df = df.copy()
    df["rsi"] = calculate_rsi(df["close"], period=rsi_period)

    buy_signals  = []
    sell_signals = []
    trades       = []

    in_trade    = False
    entry_price = 0.0
    entry_time  = None
    trade_type  = ""

    for i in range(1, len(df)):
        current = df.iloc[i]

        if pd.isna(current["rsi"]):
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

        # ── RSI signals ───────────────────────────────────────────────────────
        if current["rsi"] < oversold:
            buy_signals.append({"time": current["time"], "price": current["close"]})
            if not in_trade:
                in_trade    = True
                entry_price = current["close"]
                entry_time  = current["time"]
                trade_type  = "BUY"
        elif current["rsi"] > overbought:
            sell_signals.append({"time": current["time"], "price": current["close"]})
            if not in_trade:
                in_trade    = True
                entry_price = current["close"]
                entry_time  = current["time"]
                trade_type  = "SELL"

    # ── RSI indicator series ──────────────────────────────────────────────────
    indicators = {
        "rsi": [
            {"time": int(row["time"]), "value": round(float(row["rsi"]), 4)}
            for _, row in df.iterrows()
            if pd.notna(row["rsi"])
        ],
        "rsi_oversold":   oversold,
        "rsi_overbought": overbought,
    }

    return {
        "buy_signals":  buy_signals,
        "sell_signals": sell_signals,
        "trades":       trades,
        "indicators":   indicators,
        "metrics":      compute_metrics(trades),
    }
