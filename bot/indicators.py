# bot/indicators.py
import pandas as pd
import numpy as np

def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    h, l = df["high"], df["low"]

    # EMA20 / EMA50
    df["EMA_20"] = _ema(c, 20)
    df["EMA_50"] = _ema(c, 50)

    # RSI14 (Wilder)
    delta = c.diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/14, adjust=False).mean()
    roll_down = down.ewm(alpha=1/14, adjust=False).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # ATR14
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR_14"] = tr.ewm(alpha=1/14, adjust=False).mean()

    return df
