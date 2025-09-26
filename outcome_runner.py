# outcome_runner.py — robust outcome resolution
import os
import pandas as pd
import numpy as np

from bot.config import DATA_DIR, RESULTS_PATH, MAX_BARS_TO_RESOLVE
from bot.utils import find_time_column, coerce_dt, nearest_index_by_time

def simulate_future(fut_df, entry, sl, tp, direction):
    for j, r in enumerate(fut_df.itertuples(index=False), 1):
        hi, lo, cl = r.high, r.low, r.close
        if direction == "BUY":
            if lo <= sl:  return "LOSS", sl, j
            if hi >= tp:  return "WIN",  tp, j
        else:
            if hi >= sl:  return "LOSS", sl, j
            if lo <= tp:  return "WIN",  tp, j
    # if no hit, expire at last close
    return "EXPIRED", (fut_df.iloc[-1].close if len(fut_df) else np.nan), (j if len(fut_df) else 0)

def _safe_start_index(df, bar_time, time_col):
    """Find entry index; tolerate bad bar_time (e.g., 1970/NA)."""
    start_i = None
    # try timestamp match first
    if time_col and pd.notna(bar_time) and str(bar_time) not in ("", "NA"):
        try:
            # ignore obviously bad epoch values
            if not str(bar_time).startswith("1970"):
                start_i = nearest_index_by_time(df, time_col, bar_time)
        except Exception:
            start_i = None
    # fallbacks: last-1 (so we at least have future bars), else last
    if start_i is None:
        if len(df) >= 2:
            start_i = len(df) - 2
        else:
            start_i = max(len(df) - 1, 0)
    return start_i

def update_outcomes():
    if not os.path.exists(RESULTS_PATH):
        print(f"[WARN] {RESULTS_PATH} not found.")
        return

    res = pd.read_csv(RESULTS_PATH)

    req = ["file", "bar_time", "direction", "entry_price", "sl", "tp"]
    missing = [c for c in req if c not in res.columns]
    if missing:
        raise RuntimeError(f"results.csv missing columns: {missing}")

    # ensure output columns exist
    for c in ["outcome", "exit_price", "bars_held", "resolved_time"]:
        if c not in res.columns:
            res[c] = np.nan
    if "max_bars" not in res.columns:
        res["max_bars"] = MAX_BARS_TO_RESOLVE

    updated = 0

    for idx, row in res.iterrows():
        if str(row.get("outcome")).upper() in ("WIN", "LOSS", "EXPIRED"):
            continue

        file_path = str(row["file"])
        if not os.path.isabs(file_path):
            file_path = os.path.join(DATA_DIR, os.path.basename(file_path))
        if not os.path.exists(file_path):
            print(f"[SKIP] data file not found: {file_path}")
            continue

        try:
            df = pd.read_csv(file_path)
            for c in ["open","high","low","close"]:
                if c not in df.columns:
                    raise ValueError(f"CSV missing OHLC column: {c}")

            time_col = find_time_column(df)
            if time_col:
                df["_dt"] = coerce_dt(df[time_col])

            start_i = _safe_start_index(df, row.get("bar_time"), time_col)
            max_bars = int(row.get("max_bars")) if pd.notna(row.get("max_bars")) else MAX_BARS_TO_RESOLVE
            future = df.iloc[start_i+1:start_i+1+max_bars][["high","low","close"]]

            outcome, exit_px, bars = simulate_future(
                future,
                float(row["entry_price"]),
                float(row["sl"]),
                float(row["tp"]),
                str(row["direction"]).upper()
            )

            res.at[idx, "outcome"] = outcome
            res.at[idx, "exit_price"] = round(exit_px, 5) if pd.notna(exit_px) else exit_px
            res.at[idx, "bars_held"] = int(bars)
            if time_col and len(future) and "_dt" in df.columns and bars > 0:
                exit_row = future.index[0] + bars - 1
                if exit_row in df.index:
                    res.at[idx, "resolved_time"] = str(df.loc[exit_row, "_dt"])

            updated += 1

        except Exception as e:
            print(f"[ERROR][{file_path}] {e}")

    res.to_csv(RESULTS_PATH, index=False)
    print(f"✅ outcomes updated in {RESULTS_PATH} | rows resolved: {updated}")

if __name__ == "__main__":
    update_outcomes()
