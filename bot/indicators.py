import pandas as pd

# === Indicator Functions ===

def add_indicators(df):
    """
    Adds EMA20, EMA50, RSI14, and ATR14 to the dataframe.
    """
    df = df.copy()

    # EMA20 and EMA50
    df["EMA_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["close"].ewm(span=50, adjust=False).mean()

    # RSI14
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain / loss
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # ATR14
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = high_low.to_frame(name="hl")
    tr["hc"] = high_close
    tr["lc"] = low_close
    tr["tr"] = tr.max(axis=1)
    df["ATR_14"] = tr["tr"].rolling(14).mean()

    return df


# === Factor Logic ===

def compute_factors(df):
    """
    Derives boolean trade factors from indicators.
    """
    factors = {}

    factors["trend_ok"] = int(df["EMA_20"].iloc[-1] > df["EMA_50"].iloc[-1])

    factors["momentum_ok"] = int(40 < df["RSI_14"].iloc[-1] < 60)

    close = df["close"].iloc[-1]
    ema20 = df["EMA_20"].iloc[-1]
    factors["sr_ok"] = int(abs(close - ema20) / ema20 < 0.005)

    return factors
