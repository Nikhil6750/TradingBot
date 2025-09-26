import os, pandas as pd, numpy as np

RR = float(os.getenv("RR", 1.5))
AUDIT = "backtest_trade_audit.csv"

def section(name, part):
    if part.empty:
        print(f"{name}: no data")
        return
    wins=(part.outcome_r>0).sum()
    losses=(part.outcome_r<0).sum()
    pf=(wins*RR)/(losses or np.nan)
    avgR=part.outcome_r.mean()
    netR=part.outcome_r.sum()
    wr=wins/max(wins+losses,1)*100
    print(f"{name}: trades={len(part)}, WR={wr:.1f}%, PF={pf:.2f}, AvgR={avgR:.3f}, NetR={netR:.1f}")

def main():
    if not os.path.exists(AUDIT):
        print(f"⚠️ {AUDIT} not found. Run backtester first.")
        return
    df=pd.read_csv(AUDIT, parse_dates=["local_time"])
    df=df.dropna(subset=["local_time"])
    if df.empty:
        print("Audit contains no rows with timestamps.")
        return
    cut=df["local_time"].sort_values().iloc[int(0.7*len(df))]
    section("Train (70%)", df[df["local_time"]<=cut])
    section("Test (30%)", df[df["local_time"]>cut])

if __name__ == "__main__":
    main()
