# tests/test_indicators.py
import pandas as pd
from bot.indicators import add_indicators, compute_factors

def test_add_indicators_basic():
    n = 20  # >= 14 for ATR14
    df = pd.DataFrame({
        "open":  [float(i) for i in range(1, n + 1)],
        "high":  [float(i) + 1 for i in range(1, n + 1)],
        "low":   [float(i) - 1 for i in range(1, n + 1)],
        "close": [1.4 + i*0.1 for i in range(n)],
        "volume":[100 + i*10 for i in range(n)],
    })
    out = add_indicators(df)
    for col in ["ema20","ema50","rsi14","atr14","roll_high","roll_low","dist_to_res","dist_to_sup"]:
        assert col in out.columns


def test_compute_factors_lastrow():
    # 60 bars with gentle uptrend on close
    df = pd.DataFrame({
        "open":  [22.0] * 60,
        "high":  [23.0] * 60,
        "low":   [21.0] * 60,
        "close": [10.0 + (i * 0.02) for i in range(60)],
        "volume":[3] * 60,
    })
    out = add_indicators(df)
    factors = compute_factors(out)
    assert set(["trend_ok","momentum_ok","vol_ok","sr_ok"]).issubset(factors.keys())
