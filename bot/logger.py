# bot/logger.py
import os, csv
import pandas as pd
from bot.config import RESULTS_PATH

# Keep a clear schema
HEADERS = [
    "timestamp","file","timeframe","bar_time","score","label","sent","direction",
    "entry_price","sl","tp",
    "trend_ok","momentum_ok","sr_ok",
    "EMA_20","EMA_50","RSI_14","ATR_14",
    "outcome","max_bars","exit_price","bars_held","resolved_time"
]

def ensure_header():
    # Don't overwrite if file already exists
    if not os.path.exists(RESULTS_PATH) or os.path.getsize(RESULTS_PATH) == 0:
        with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADERS)

def log_result(path, pair, timeframe, bar_time, score, label, sent, row, factors,
               entry_price, sl, tp, max_bars=None):
    ensure_header()
    now = pd.Timestamp.now().isoformat(timespec="seconds")
    mb = max_bars if max_bars is not None else ""
    with open(RESULTS_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            now, os.path.basename(path), timeframe, bar_time, round(float(score),1), label, bool(sent),
            factors.get("direction"),
            round(float(entry_price),5), round(float(sl),5), round(float(tp),5),
            int(bool(factors.get("trend_ok", False))),
            int(bool(factors.get("momentum_ok", False))),
            int(bool(factors.get("sr_ok", False))),
            round(float(row["EMA_20"]),5), round(float(row["EMA_50"]),5),
            round(float(row["RSI_14"]),2), round(float(row["ATR_14"]),5),
            "", mb, "", "", ""
        ])
