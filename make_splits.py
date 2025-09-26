# make_splits.py
import os, sys, pandas as pd
from datetime import datetime

DATA_DIR   = os.getenv("DATA_DIR", "data")
OUT_TRAIN  = "data_train"
OUT_TEST   = "data_test"
CUTOFF     = os.getenv("SPLIT_CUTOFF", "2025-01-01")  # adjust if needed

os.makedirs(OUT_TRAIN, exist_ok=True)
os.makedirs(OUT_TEST,  exist_ok=True)

def norm_cols(df):
    # normalize common timestamp column variants
    for c in ["timestamp","time","datetime","Date","date","Time"]:
        if c in df.columns:
            if c != "timestamp":
                df = df.rename(columns={c:"timestamp"})
            break
    # ensure pandas datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True).dropna()
    return df

for fn in os.listdir(DATA_DIR):
    if not fn.lower().endswith(".csv"): continue
    src = os.path.join(DATA_DIR, fn)
    try:
        df = pd.read_csv(src)
        df = norm_cols(df)
        cutoff = pd.Timestamp(CUTOFF, tz="UTC")
        df_train = df[df["timestamp"] < cutoff]
        df_test  = df[df["timestamp"] >= cutoff]
        if len(df_train): df_train.to_csv(os.path.join(OUT_TRAIN, fn), index=False)
        if len(df_test):  df_test.to_csv(os.path.join(OUT_TEST , fn), index=False)
        print(f"Split {fn}: train={len(df_train)} rows, test={len(df_test)} rows")
    except Exception as e:
        print(f"Skip {fn}: {e}")
