# parameter_grid_search_all.py
import os
import math
import pandas as pd
from glob import glob
from bot.backtest import backtest  # uses your existing backtest()
# from bot.backtest import backtest, summarize_results  # optional

DATA_DIR = "data"
# grid to test
thresholds = [10, 30, 50, 70]
atr_multipliers = [1.5, 2.0, 2.5]
# other params (can adjust)
rr = 2
max_bars = 20

# Helper: normalize columns
def normalize_ohlcv_columns(df):
    # map common variants to expected lowercase names
    rename_map = {}
    # some files use 'time' / 'Time' etc.
    for c in df.columns:
        lc = c.lower()
        if lc == "time" or lc == "timestamp" or lc == "date":
            rename_map[c] = "timestamp"
        elif lc == "open":
            rename_map[c] = "open"
        elif lc == "high":
            rename_map[c] = "high"
        elif lc == "low":
            rename_map[c] = "low"
        elif lc == "close":
            rename_map[c] = "close"
    if rename_map:
        df = df.rename(columns=rename_map)
    return df

# Compute per-trade profit for buy/sell
def compute_trade_profit(row):
    entry = row['entry_price']
    exitp = row['exit_price']
    direction = row['direction'].upper()
    if pd.isna(entry) or pd.isna(exitp):
        return 0.0
    if direction == "BUY":
        return exitp - entry
    else:
        return entry - exitp

# Compute R:R per trade (safe)
def compute_trade_rr(row):
    entry = row['entry_price']
    sl = row['sl']
    exitp = row['exit_price']
    if pd.isna(entry) or pd.isna(sl) or entry == sl:
        return float('nan')
    profit = abs(exitp - entry)
    risk = abs(entry - sl)
    if risk == 0:
        return float('nan')
    return profit / risk

grid_rows = []

# find files
files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv") and f.startswith("FX_")]
if not files:
    print("No FX_*.csv files found in data/ - aborting.")
    raise SystemExit(1)

for thr in thresholds:
    for atr_mult in atr_multipliers:
        print(f"\n=== Testing threshold={thr}, atr_mult={atr_mult} ===")
        all_trades = []  # collect trade DataFrames from each file
        total_files = 0
        for file in files:
            fp = os.path.join(DATA_DIR, file)
            # load
            try:
                df = pd.read_csv(fp)
            except Exception as e:
                print(f"Failed to read {file}: {e}")
                continue

            df = normalize_ohlcv_columns(df)

            # Must have required cols
            required = {"open", "high", "low", "close", "timestamp"}
            if not required.issubset(set(df.columns)):
                print(f"Skipping {file} — missing required columns ({file})")
                continue

            total_files += 1
            # run backtest on this file
            trades_df = backtest(df, threshold=thr, atr_mult=atr_mult, rr=rr, max_bars=max_bars)

            # attach symbol/file if returned trades
            if not trades_df.empty:
                trades_df = trades_df.copy()
                trades_df["symbol"] = file
                all_trades.append(trades_df)

        # aggregate across files for this param set
        if not all_trades:
            print("  -> No trades produced for this param set.")
            grid_rows.append({
                "threshold": thr,
                "atr_multiplier": atr_mult,
                "files_tested": total_files,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "expired": 0,
                "win_rate_pct": 0.0,
                "avg_rr": float('nan'),
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "profit_factor": float('nan'),
                "net_profit": 0.0
            })
            continue

        big = pd.concat(all_trades, ignore_index=True)
        big["profit"] = big.apply(compute_trade_profit, axis=1)
        big["abs_loss"] = big["profit"].apply(lambda x: -x if x < 0 else 0.0)
        big["abs_profit"] = big["profit"].apply(lambda x: x if x > 0 else 0.0)
        big["rr"] = big.apply(compute_trade_rr, axis=1)

        total_trades = len(big)
        wins = (big["outcome"] == "WIN").sum()
        losses = (big["outcome"] == "LOSS").sum()
        expired = (big["outcome"] == "EXPIRED").sum()
        win_rate = wins / total_trades * 100 if total_trades else 0.0
        # avg RR — average only where rr is finite
        rr_vals = big["rr"].dropna()
        avg_rr = rr_vals.mean() if len(rr_vals) else float('nan')
        gross_profit = big["abs_profit"].sum()
        gross_loss = big["abs_loss"].sum()
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        net_profit = gross_profit - gross_loss

        print(f"Files tested: {total_files}, Trades: {total_trades}, Win%: {win_rate:.2f}, Avg R:R: {avg_rr if not math.isnan(avg_rr) else 'nan'}, PF: {profit_factor:.2f}")

        # Save aggregated row
        grid_rows.append({
            "threshold": thr,
            "atr_multiplier": atr_mult,
            "files_tested": total_files,
            "total_trades": total_trades,
            "wins": int(wins),
            "losses": int(losses),
            "expired": int(expired),
            "win_rate_pct": round(win_rate, 2),
            "avg_rr": round(avg_rr, 3) if not math.isnan(avg_rr) else None,
            "gross_profit": round(gross_profit, 6),
            "gross_loss": round(gross_loss, 6),
            "profit_factor": round(profit_factor, 3) if gross_loss>0 else None,
            "net_profit": round(net_profit, 6)
        })

# Save grid results
grid_df = pd.DataFrame(grid_rows)
grid_df = grid_df.sort_values(by=["profit_factor", "win_rate_pct"], ascending=[False, False])
grid_df.to_csv("parameter_grid_search_all_results.csv", index=False)
print("\n✅ Grid search finished. Results written to parameter_grid_search_all_results.csv")
print(grid_df)
