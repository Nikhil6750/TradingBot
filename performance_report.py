import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

RR = float(os.getenv("RR", os.getenv("BT_RR", 1.5)))
TRADES_CSV = "backtest_results_trades.csv"

def main():
    if not os.path.exists(TRADES_CSV):
        print(f"⚠️ {TRADES_CSV} not found. Run: python backtest_runner.py")
        return

    df = pd.read_csv(TRADES_CSV)
    if "result_r" not in df.columns:
        print(f"⚠️ {TRADES_CSV} missing 'result_r' column")
        return

    wins    = (df["result_r"] > 0).sum()
    losses  = (df["result_r"] < 0).sum()
    expired = (df["result_r"] == 0).sum()
    trades  = len(df)

    net_r = df["result_r"].sum()
    gross_profit = wins * RR
    gross_loss   = losses * 1.0

    wl = wins + losses
    win_rate = (wins / wl * 100.0) if wl else 0.0
    avg_r    = (net_r / trades) if trades else 0.0

    if losses == 0 and wins == 0:
        pf = float("nan")
    elif losses == 0:
        pf = float("inf")
    elif wins == 0:
        pf = 0.0
    else:
        pf = gross_profit / gross_loss

    print("=== Performance Report (per-trade) ===")
    print(f"Trades       : {trades}")
    print(f"Wins/Losses  : {wins}/{losses}  Expired: {expired}")
    print(f"Win Rate     : {win_rate:.2f}%")
    print(f"Avg R        : {avg_r:.3f}")
    print(f"ProfitFactor : {pf:.3f}" if pd.notna(pf) and np.isfinite(pf) else "ProfitFactor : nan")
    print(f"Net R        : {net_r:.3f}")

if __name__ == "__main__":
    main()
