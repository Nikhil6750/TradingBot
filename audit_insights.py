import os
import pandas as pd
import numpy as np

AUDIT = "backtest_trade_audit.csv"

def pf_from_counts(wins, losses, rr):
    if wins == 0 and losses == 0: return np.nan
    if losses == 0: return np.inf
    if wins == 0: return 0.0
    return (wins * rr) / (losses * 1.0)

def summarize(df, rr):
    g = df.groupby("symbol", dropna=False)["outcome_r"]
    by_symbol = g.agg(
        trades="count",
        wins=lambda s: (s > 0).sum(),
        losses=lambda s: (s < 0).sum(),
        expired=lambda s: (s == 0).sum(),
        avg_r="mean",
        net_r="sum",
    ).reset_index()
    by_symbol["pf"] = [
        pf_from_counts(r.wins, r.losses, rr) for r in by_symbol.itertuples(index=False)
    ]
    by_symbol["win_rate_%"] = by_symbol.apply(
        lambda r: (r["wins"] / max(r["wins"] + r["losses"], 1)) * 100, axis=1
    )
    by_symbol = by_symbol.sort_values(["pf", "avg_r", "net_r"], ascending=[False, False, False])

    # Hour buckets from local_time (if present)
    if "local_time" in df.columns:
        t = pd.to_datetime(df["local_time"], errors="coerce")
        hrs = t.dt.hour
    else:
        hrs = pd.Series([-1]*len(df))
    df = df.assign(hour=hrs)
    df["hour_bucket"] = pd.cut(df["hour"], bins=[-1, 6, 9, 12, 15, 18, 21, 24],
                               labels=["0-6","6-9","9-12","12-15","15-18","18-21","21-24"])
    g2 = df.groupby("hour_bucket", observed=False)["outcome_r"]
    by_hour = g2.agg(
        trades="count",
        wins=lambda s: (s > 0).sum(),
        losses=lambda s: (s < 0).sum(),
        expired=lambda s: (s == 0).sum(),
        avg_r="mean",
        net_r="sum",
    ).reset_index()
    by_hour["pf"] = [
        pf_from_counts(r.wins, r.losses, rr) for r in by_hour.itertuples(index=False)
    ]
    by_hour["win_rate_%"] = by_hour.apply(
        lambda r: (r["wins"] / max(r["wins"] + r["losses"], 1)) * 100, axis=1
    )
    by_hour = by_hour.sort_values(["pf","avg_r","net_r"], ascending=[False, False, False])

    return by_symbol, by_hour

def main():
    rr = float(os.getenv("RR", os.getenv("BT_RR", 1.5)))
    if not os.path.exists(AUDIT):
        print(f"⚠️ {AUDIT} not found. Run the backtester that writes the audit CSV.")
        return
    df = pd.read_csv(AUDIT)
    if df.empty:
        print("No audit rows.")
        return
    by_symbol, by_hour = summarize(df, rr)
    print("\n=== PF by SYMBOL ===")
    print(by_symbol.to_string(index=False))
    print("\n=== PF by HOUR BUCKET (local) ===")
    print(by_hour.to_string(index=False))

    by_symbol.to_csv("audit_by_symbol.csv", index=False)
    by_hour.to_csv("audit_by_hour.csv", index=False)
    print("\nSaved audit_by_symbol.csv and audit_by_hour.csv")

if __name__ == "__main__":
    main()
