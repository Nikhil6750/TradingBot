#!/usr/bin/env python3
import os
import pandas as pd
from pathlib import Path

SUMMARY_FILE = "backtest_results.csv"
TRADES_FILE  = "backtest_results_trades.csv"

def pretty_pct(x):
    try:
        return f"{float(x):.2f}%"
    except Exception:
        return str(x)

def main():
    if not os.path.exists(SUMMARY_FILE):
        raise SystemExit(f"[ERROR] Missing {SUMMARY_FILE}")

    # Read the summary file you already produce in backtest_runner.py
    s = pd.read_csv(SUMMARY_FILE)

    # Normalize column names just in case
    s.columns = [c.strip().lower() for c in s.columns]

    # Expecting columns like: file, trades, win_rate, profit_factor, net_r
    required = {"file", "trades", "win_rate", "profit_factor", "net_r"}
    if not required.issubset(set(s.columns)):
        raise SystemExit(
            f"[ERROR] {SUMMARY_FILE} must have columns {sorted(required)}. "
            f"Found: {list(s.columns)}"
        )

    # Clean display
    s["trades"] = s["trades"].astype(int)
    # win_rate is already a percent string in your latest run; make it uniform
    s["win_rate"] = s["win_rate"].astype(str).str.replace("%", "", regex=False)
    s["win_rate"] = s["win_rate"].astype(float).map(lambda v: f"{v:.2f}%")

    # Profit factor & net_r as float
    s["profit_factor"] = pd.to_numeric(s["profit_factor"], errors="coerce")
    s["net_r"]         = pd.to_numeric(s["net_r"], errors="coerce")

    s = s.set_index("file")[["trades", "win_rate", "profit_factor", "net_r"]]
    print(s.to_string())

    # Overall roll-up from summary
    tot_trades = int(s["trades"].sum())
    # average win rate (weighted by trades per file)
    wr_vals = s["win_rate"].str.replace("%","", regex=False).astype(float)
    weights = s["trades"].astype(float)
    overall_wr = (wr_vals * weights).sum() / max(weights.sum(), 1.0)

    overall_net_r = float(s["net_r"].sum())

    print("\n=== Overall (from summary) ===")
    print(f"Trades       : {tot_trades}")
    print(f"Win Rate     : {overall_wr:.2f}%")
    print(f"ProfitFactor : n/a (needs per-trade P/L)")
    print(f"Avg R        : n/a (needs per-trade P/L)")
    print(f"Net R        : {overall_net_r:.3f}")

    # If we also have per-trade file, compute richer stats
    if os.path.exists(TRADES_FILE):
        t = pd.read_csv(TRADES_FILE)
        t.columns = [c.strip().lower() for c in t.columns]
        if {"result_r", "file"}.issubset(t.columns):
            r = pd.to_numeric(t["result_r"], errors="coerce").dropna()
            wins = (r > 0).sum()
            losses = (r < 0).sum()
            exp = (r == 0).sum()
            trades = len(r)
            win_rate = 100.0 * wins / trades if trades else 0.0
            gross_profit = r[r > 0].sum()
            gross_loss   = -r[r < 0].sum()
            pf = (gross_profit / gross_loss) if gross_loss > 0 else float("nan")
            avg_r = r.mean() if trades else float("nan")
            net_r = r.sum()

            print("\n=== Overall (from per-trade log) ===")
            print(f"Trades       : {trades}")
            print(f"Wins/Losses  : {wins}/{losses}  Expired: {exp}")
            print(f"Win Rate     : {win_rate:.2f}%")
            print(f"Avg R        : {avg_r:.3f}")
            print(f"ProfitFactor : {pf:.3f}")
            print(f"Net R        : {net_r:.3f}")

if __name__ == "__main__":
    main()
