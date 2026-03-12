import pandas as pd

def calculate_sma(close: pd.Series, window: int = 20) -> pd.Series:
    return close.rolling(window=window).mean()

def calculate_ema(close: pd.Series, span: int = 50) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()

def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal_span: int = 9):
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_span, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

def calculate_bbands(close: pd.Series, window: int = 20, dev: float = 2.0):
    sma = calculate_sma(close, window)
    std = close.rolling(window=window).std()
    upper = sma + (std * dev)
    lower = sma - (std * dev)
    return upper, lower, sma
