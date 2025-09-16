import os
import csv
from datetime import datetime

RESULTS_FILE = os.path.join("data", "results.csv")

def log_result(filepath, score, label, sent, factors, df):
    """
    Append a row to results.csv with trade info, including SL/TP.
    """
    # Ensure file exists with header
    file_exists = os.path.isfile(RESULTS_FILE)

    # Grab last candle data
    last_row = df.iloc[-1]
    close = last_row["close"]
    ema20 = last_row.get("EMA_20", None)
    ema50 = last_row.get("EMA_50", None)
    rsi14 = last_row.get("RSI_14", None)
    atr14 = last_row.get("ATR_14", None)

    # Define direction: simple rule → EMA20 > EMA50 = BUY else SELL
    direction = "BUY" if ema20 > ema50 else "SELL"

    # Stop Loss & Take Profit using ATR multiplier
    if direction == "BUY":
        sl = close - 1.5 * atr14 if atr14 else None
        tp = close + 3.0 * atr14 if atr14 else None
    else:
        sl = close + 1.5 * atr14 if atr14 else None
        tp = close - 3.0 * atr14 if atr14 else None

    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file": os.path.basename(filepath),
        "timeframe": factors.get("timeframe", ""),
        "bar_time": factors.get("bar_time", ""),
        "score": score,
        "label": label,
        "sent": sent,
        "direction": direction,
        "entry_price": close,
        "sl": sl,
        "tp": tp,
        "trend_ok": factors.get("trend_ok", ""),
        "momentum_ok": factors.get("momentum_ok", ""),
        "sr_ok": factors.get("sr_ok", ""),
        "EMA_20": ema20,
        "EMA_50": ema50,
        "RSI_14": rsi14,
        "ATR_14": atr14,
        "outcome": ""  # leave empty, will be updated later
    }

    # Write header if file doesn’t exist
    with open(RESULTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
