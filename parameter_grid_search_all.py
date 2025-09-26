# parameter_grid_search_all.py
import os
import itertools
import pandas as pd
import glob
from pathlib import Path

from helpers import (
    get_env_str, get_env_float, parse_session, utc_to_local, in_session_mask,
    read_ohlc_csv, summarize_trades_rows, banner
)

SESSION_RAW     = get_env_str("SESSION", "ALL")
TZ_OFFSET_HOURS = get_env_float("TZ_OFFSET_HOURS", 0.0)
session = parse_session(SESSION_RAW)
print(f"[GRID] Session parsed: {'ALL' if session is None else session} (raw={SESSION_RAW!r}), TZ_OFF={TZ_OFFSET_HOURS:+.1f}h")

# Replace ranges as you like
thresholds      = [50, 55, 60, 65, 70, 75, 80]
atr_multipliers = [1.5, 1.8, 2.0, 2.2]
rrs             = [1.2, 1.5, 1.8, 2.0]

# Dummy strategy logic — replace with your actual one to match your earlier results
def generate_trades(df: pd.DataFrame, rr: float) -> list:
    rows = []
    step = max(len(df) // 200, 1)
    toggle = 1
    for i in range(0, len(df), step):
        r = (rr if toggle > 0 else -1.0)
        result = "win" if r > 0 else "loss"
        rows.append({"result": result, "r": r})
        toggle *= -1
    return rows

data_dir = Path("data")
files = sorted(glob.glob(str(data_dir / "*.csv")))
if not files:
    raise SystemExit("No CSVs found under data/*.csv")

records = []

for t, am, rr in itertools.product(thresholds, atr_multipliers, rrs):
    all_rows = []
    files_tested = 0

    for path in files:
        df = read_ohlc_csv(path)
        df["dt_local"] = utc_to_local(df["dt_utc"], TZ_OFFSET_HOURS)
        mask = in_session_mask(df["dt_local"], session)
        df_sess = df.loc[mask].reset_index(drop=True)
        if df_sess.empty:
            continue

        trades = generate_trades(df_sess, rr=rr)
        if trades:
            all_rows.extend(trades)
            files_tested += 1

    if not all_rows:
        print(f"\n{banner(f't={t}, am={am}, rr={rr}')}") 
        print("Files tested: 0, Trades: 0, Win%: 0.00, Avg R: 0.000, PF: 0.00, NetR: 0.00")
        records.append(dict(threshold=t, atr_multiplier=am, rr=rr,
                            files_tested=0, total_trades=0, win_rate_pct=0.0,
                            avg_rr=0.0, profit_factor=0.0, net_profit=0.0))
        continue

    s = summarize_trades_rows(all_rows)
    print(f"\n{banner(f't={t}, am={am}, rr={rr}')}") 
    print(f"Files tested: {files_tested}, Trades: {s['trades']}, "
          f"Win%: {s['win_rate']:.2f}, Avg R: {s['avg_r']:.3f}, "
          f"PF: {s['profit_factor']:.2f}, NetR: {s['net_r']:.2f}")

    records.append(dict(threshold=t, atr_multiplier=am, rr=rr,
                        files_tested=files_tested, total_trades=s['trades'],
                        win_rate_pct=s['win_rate'], avg_rr=s['avg_r'],
                        profit_factor=s['profit_factor'], net_profit=s['net_r']))

df = pd.DataFrame(records)
df.to_csv("parameter_grid_search_all_results.csv", index=False)
print("✅ Grid search finished. Results written to parameter_grid_search_all_results.csv")
print(df.sort_values(["profit_factor","avg_rr","net_profit"], ascending=False).head(12))
