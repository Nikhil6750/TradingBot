import os, sys, itertools, subprocess, pandas as pd, numpy as np, textwrap

# Ensure UTF-8 on Windows consoles
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

RRs  = [1.1, 1.2, 1.3]
ATRs = [1.4, 1.6, 1.8]
MAXB = [60, 90, 120]
SESS = os.getenv("SESSION", "12-18")  # keep your session, use env if set

PY = sys.executable  # same Python as current venv

def run_once(rr, atr, maxb):
    env = os.environ.copy()
    env["TRUNCATE_RESULTS"] = "1"
    env["SESSION"] = SESS
    env["RR"] = str(rr)
    env["ATR_MULTIPLIER"] = str(atr)
    env["MAX_BARS"] = str(maxb)

    p = subprocess.run([PY, "backtest_runner.py"], env=env, capture_output=True, text=True)
    if p.returncode != 0:
        print("\n⚠️  Backtest FAILED for combo:", rr, atr, maxb)
        if p.stdout:
            print("---- STDOUT ----")
            print(textwrap.shorten(p.stdout, width=2000, placeholder="..."))
        if p.stderr:
            print("---- STDERR ----")
            print(p.stderr)
        return None

    trades_csv = "backtest_results_trades.csv"
    if not os.path.exists(trades_csv):
        print("⚠️  No trades CSV produced for combo:", rr, atr, maxb)
        return None

    df = pd.read_csv(trades_csv)
    if "result_r" not in df.columns or df.empty:
        print("⚠️  Trades CSV empty/missing result_r for combo:", rr, atr, maxb)
        return None

    wins = (df["result_r"] > 0).sum()
    losses = (df["result_r"] < 0).sum()
    expired = (df["result_r"] == 0).sum()
    trades = len(df)
    net_r = df["result_r"].sum()

    if wins == 0 and losses == 0: pf = np.nan
    elif losses == 0:             pf = np.inf
    elif wins == 0:               pf = 0.0
    else:                         pf = (wins * rr) / (losses * 1.0)

    wl = wins + losses
    win_rate = (wins / wl * 100.0) if wl else 0.0
    avg_r = net_r / trades if trades else 0.0

    return {"RR": rr, "ATR": atr, "MAX_BARS": maxb,
            "trades": trades, "wins": wins, "losses": losses, "expired": expired,
            "pf": pf, "win_rate": win_rate, "avg_r": avg_r, "net_r": net_r}

def main():
    rows = []
    for rr, atr, mb in itertools.product(RRs, ATRs, MAXB):
        res = run_once(rr, atr, mb)
        if res: rows.append(res)

    if not rows:
        print("No successful runs. Check errors above.")
        return

    out = pd.DataFrame(rows)

    def pf_rank(x):
        if pd.isna(x): return -1e9
        if np.isinf(x): return 1e9
        return float(x)
    out["_pf_rank"] = out["pf"].apply(pf_rank)
    out = out.sort_values(by=["_pf_rank","avg_r","net_r"], ascending=[False, False, False]).drop(columns=["_pf_rank"])

    print("\n=== Top Results ===")
    cols = ["RR","ATR","MAX_BARS","trades","wins","losses","expired","pf","win_rate","avg_r","net_r"]
    print(out[cols].to_string(index=False))
    out.to_csv("sweep_quick_results.csv", index=False)
    print("\nSaved sweep_quick_results.csv")

if __name__ == "__main__":
    main()
