# bot/utils.py
import os, re
import pandas as pd
from typing import Optional, Tuple

def parse_pair_tf(path_or_name: str) -> Tuple[str, str]:
    """
    Examples:
      r'D:\\...\\FX_GBPAUD, 5_93d11.csv' -> ('GBPAUD','5m')
      'FX_USDJPY.csv'                    -> ('USDJPY','unknown')
    """
    base = os.path.basename(path_or_name).replace(".csv", "")
    base = base.replace("FX_", "")
    core = base.split("_")[0]
    m = re.match(r"([A-Z]+),\s*(\d+)$", core)
    if m:
        pair, tf = m.groups()
        return pair, f"{tf}m"
    m2 = re.match(r"([A-Z]+)", core)
    return (m2.group(1) if m2 else core), "unknown"

def find_time_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["time", "timestamp", "date", "datetime"]
    for c in df.columns:
        if c.lower() in candidates:
            return c
    # fallback: try any parseable column
    for c in df.columns:
        try:
            pd.to_datetime(df[c])
            return c
        except Exception:
            pass
    return None

def coerce_dt(s: pd.Series) -> pd.Series:
    dt = pd.to_datetime(s, errors="coerce", utc=False)
    return dt.dt.floor("min")

def nearest_index_by_time(df: pd.DataFrame, time_col: str, target_time_str: str, max_diff="30min") -> Optional[int]:
    if not target_time_str:
        return None
    target = pd.to_datetime(str(target_time_str), errors="coerce")
    if pd.isna(target):
        return None
    tser = coerce_dt(df[time_col])
    diffs = (tser - target).abs()
    i = diffs.idxmin()
    if pd.isna(i):
        return None
    if diffs.loc[i] > pd.to_timedelta(max_diff):
        return None
    return df.index.get_loc(i)

def extract_bar_time(df: pd.DataFrame) -> str:
    """Return the actual last candle time as string, else 'NA'."""
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
        return str(df.index[-1])
    tcol = find_time_column(df)
    if tcol:
        try:
            return str(pd.to_datetime(df[tcol].iloc[-1]))
        except Exception:
            return str(df[tcol].iloc[-1])
    return "NA"
