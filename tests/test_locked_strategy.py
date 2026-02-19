import pandas as pd

from bot.backtest import candles_from_dataframe, run_backtest
from bot.locked_strategy import LockedStreakPullbackStrategy


def _df(rows):
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close"])


def test_bullish_setup_pullback_len_1_case_a_executes_one_trade():
    # Streak: 4 bullish candles
    # Pullback: 1 bearish candle that touches LSC 50%
    # Breaking candle: bullish close < target
    # Confirmation: bullish
    # Exit: first touch of target after entry
    rows = [
        ("2024-01-01T00:00:00Z", 1.00, 1.01, 1.00, 1.01),
        ("2024-01-01T00:05:00Z", 1.01, 1.02, 1.01, 1.02),
        ("2024-01-01T00:10:00Z", 1.02, 1.03, 1.02, 1.03),
        ("2024-01-01T00:15:00Z", 1.03, 1.04, 1.03, 1.04),  # LSC (open=1.03, low=1.03, high=1.04, mid=1.035)
        ("2024-01-01T00:20:00Z", 1.04, 1.04, 1.032, 1.035),  # pullback bearish (low>=LSC.open, touches mid)
        ("2024-01-01T00:25:00Z", 1.020, 1.026, 1.018, 1.025),  # breaking bullish close < target(1.03)
        ("2024-01-01T00:30:00Z", 1.024, 1.029, 1.023, 1.028),  # confirmation bullish -> entry at close 1.028
        ("2024-01-01T00:35:00Z", 1.028, 1.032, 1.027, 1.031),  # touches target 1.03 -> exit
    ]

    candles = candles_from_dataframe(_df(rows), tz_name="UTC")
    trades = run_backtest(candles, strategy=LockedStreakPullbackStrategy())
    assert len(trades) == 1

    t = trades[0]
    assert t.direction == "long"
    assert t.streak_length == 4
    assert t.pullback_length == 1
    assert t.entry_price == 1.028
    assert t.exit_price == 1.03  # Case A bullish target = LSC.low


def test_bearish_setup_pullback_len_2_case_b_executes_one_trade():
    # Mirror the rules for a bearish setup.
    rows = [
        ("2024-01-01T00:00:00Z", 1.10, 1.10, 1.09, 1.09),
        ("2024-01-01T00:05:00Z", 1.09, 1.09, 1.08, 1.08),
        ("2024-01-01T00:10:00Z", 1.08, 1.08, 1.07, 1.07),
        ("2024-01-01T00:15:00Z", 1.07, 1.07, 1.06, 1.06),  # LSC (open=1.07, high=1.07, low=1.06, mid=1.065)
        # Pullback: 2 bullish candles, must NOT retrace past LSC.open (high <= 1.07)
        ("2024-01-01T00:20:00Z", 1.060, 1.066, 1.058, 1.064),
        ("2024-01-01T00:25:00Z", 1.064, 1.069, 1.063, 1.068),
        # Case B: pullback does NOT touch/cross mid (1.065) -> ensure lows/highs stay above mid? For bearish,
        # we avoid touching by keeping pullback range entirely above mid: low > 1.065.
        # Adjust rows accordingly: second candle low > 1.065, first candle low > 1.065.
    ]

    # Overwrite with a non-touch pullback where both lows are above LSC.mid=1.065, and highs <= LSC.open=1.07.
    rows = [
        ("2024-01-01T00:00:00Z", 1.10, 1.10, 1.09, 1.09),
        ("2024-01-01T00:05:00Z", 1.09, 1.09, 1.08, 1.08),
        ("2024-01-01T00:10:00Z", 1.08, 1.08, 1.07, 1.07),
        ("2024-01-01T00:15:00Z", 1.07, 1.07, 1.06, 1.06),  # LSC (open=1.07, high=1.07, low=1.06, mid=1.065)
        ("2024-01-01T00:20:00Z", 1.066, 1.069, 1.066, 1.068),  # pullback bullish, low=1.066 > mid
        ("2024-01-01T00:25:00Z", 1.068, 1.070, 1.066, 1.069),  # pullback bullish, high <= 1.07, low > mid
        ("2024-01-01T00:30:00Z", 1.069, 1.080, 1.068, 1.075),  # breaking close > target (target=pb_high=1.07)
        ("2024-01-01T00:35:00Z", 1.074, 1.074, 1.060, 1.062),  # confirmation bearish -> entry at close 1.062
        ("2024-01-01T00:40:00Z", 1.062, 1.071, 1.061, 1.065),  # touches target 1.07 -> exit
    ]

    candles = candles_from_dataframe(_df(rows), tz_name="UTC")
    trades = run_backtest(candles, strategy=LockedStreakPullbackStrategy())
    assert len(trades) == 1

    t = trades[0]
    assert t.direction == "short"
    assert t.streak_length == 4
    assert t.pullback_length == 2
    assert t.exit_price == 1.07  # Case B bearish target = highest HIGH of pullback


def test_doji_in_pullback_invalidates_setup():
    rows = [
        ("2024-01-01T00:00:00Z", 1.00, 1.01, 1.00, 1.01),
        ("2024-01-01T00:05:00Z", 1.01, 1.02, 1.01, 1.02),
        ("2024-01-01T00:10:00Z", 1.02, 1.03, 1.02, 1.03),
        ("2024-01-01T00:15:00Z", 1.03, 1.04, 1.03, 1.04),
        ("2024-01-01T00:20:00Z", 1.04, 1.04, 1.04, 1.04),  # doji where pullback would be
        ("2024-01-01T00:25:00Z", 1.03, 1.04, 1.02, 1.03),
    ]
    candles = candles_from_dataframe(_df(rows), tz_name="UTC")
    trades = run_backtest(candles, strategy=LockedStreakPullbackStrategy())
    assert trades == []

