import os
import pandas as pd
from time import perf_counter

def clean_summary(path: str):
    if not os.path.exists(path):
        print(f"⚠️ {path} not found — skipping")
        return
    t0 = perf_counter()
    df = pd.read_csv(path)
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    df.to_csv(path, index=False)
    print(f"✅ Cleaned {path} | removed {before - after} rows | now {after} rows | {perf_counter()-t0:.3f}s")

def clean_trades(path: str):
    if not os.path.exists(path):
        print(f"⚠️ {path} not found — skipping")
        return
    t0 = perf_counter()
    df = pd.read_csv(path)
    before = len(df)
    if "result_r" in df.columns:
        df = df.dropna(subset=["result_r"])
    after = len(df)
    df.to_csv(path, index=False)
    print(f"✅ Cleaned {path} | removed {before - after} rows | now {after} rows | {perf_counter()-t0:.3f}s")

def main():
    clean_summary("backtest_results.csv")
    clean_trades("backtest_results_trades.csv")

if __name__ == "__main__":
    main()
