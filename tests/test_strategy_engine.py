from bot.strategy_engine import generate_trades


def _c(t, o, h, l, c, v=0.0):
    return {"time": int(t), "open": float(o), "high": float(h), "low": float(l), "close": float(c), "volume": float(v)}


def test_bullish_case_a_executes_one_trade():
    # Streak: 4 bullish
    # Pullback: 1 bearish that touches LSC midpoint
    # Breaking: bullish close < target
    # Confirmation: bullish
    # Exit: first touch of target after entry
    candles = [
        _c(0, 1.00, 1.01, 1.00, 1.01),
        _c(300, 1.01, 1.02, 1.01, 1.02),
        _c(600, 1.02, 1.03, 1.02, 1.03),
        _c(900, 1.03, 1.04, 1.03, 1.04),  # LSC (mid=1.035, low=1.03)
        _c(1200, 1.04, 1.04, 1.032, 1.035),  # pullback bearish, low>=LSC.open, touches mid
        _c(1500, 1.020, 1.026, 1.018, 1.025),  # breaking bullish close < target(1.03)
        _c(1800, 1.024, 1.029, 1.023, 1.028),  # confirmation bullish -> entry
        _c(2100, 1.028, 1.032, 1.027, 1.031),  # touches target -> exit
    ]

    trades = generate_trades(candles)
    assert len(trades) == 1

    t = trades[0]
    assert t["direction"] == "BUY"
    assert t["streak_length"] == 4
    assert t["pullback_length"] == 1
    assert t["target"] == 1.03
    assert t["breaking_candle_time"] == 1500
    assert t["entry"]["time"] == 1800
    assert t["entry"]["price"] == 1.028
    assert t["exit"]["time"] == 2100
    assert t["exit"]["price"] == 1.03


def test_bearish_case_b_executes_one_trade():
    # Bearish streak with a 2-candle bullish pullback that does NOT touch midpoint (Case B).
    candles = [
        _c(0, 1.10, 1.10, 1.09, 1.09),
        _c(300, 1.09, 1.09, 1.08, 1.08),
        _c(600, 1.08, 1.08, 1.07, 1.07),
        _c(900, 1.07, 1.07, 1.06, 1.06),  # LSC (mid=1.065, open=1.07)
        _c(1200, 1.066, 1.069, 1.066, 1.068),  # pullback bullish, low>mid, high<=open
        _c(1500, 1.068, 1.070, 1.066, 1.069),  # pullback bullish, low>mid, high<=open
        _c(1800, 1.080, 1.081, 1.072, 1.075),  # breaking bearish close > target(1.07)
        _c(2100, 1.076, 1.077, 1.071, 1.071),  # confirmation bearish -> entry at close 1.071 (> target)
        _c(2400, 1.071, 1.072, 1.068, 1.069),  # touches target -> exit
    ]

    trades = generate_trades(candles)
    assert len(trades) == 1

    t = trades[0]
    assert t["direction"] == "SELL"
    assert t["streak_length"] == 4
    assert t["pullback_length"] == 2
    assert t["target"] == 1.07
    assert t["breaking_candle_time"] == 1800
    assert t["entry"]["time"] == 2100
    assert t["exit"]["time"] == 2400
    assert t["exit"]["price"] == 1.07


def test_entry_without_exit_is_not_included_and_blocks_further_trades():
    candles = [
        _c(0, 1.00, 1.01, 1.00, 1.01),
        _c(300, 1.01, 1.02, 1.01, 1.02),
        _c(600, 1.02, 1.03, 1.02, 1.03),
        _c(900, 1.03, 1.04, 1.03, 1.04),  # LSC (target=1.03)
        _c(1200, 1.04, 1.04, 1.032, 1.035),  # pullback touches mid -> Case A
        _c(1500, 1.020, 1.026, 1.018, 1.025),  # breaking close < target
        _c(1800, 1.024, 1.029, 1.023, 1.028),  # confirmation -> entry
        # After entry: never touches target 1.03 (high always < 1.03)
        _c(2100, 1.028, 1.029, 1.020, 1.021),
        _c(2400, 1.021, 1.025, 1.015, 1.018),
    ]

    trades = generate_trades(candles)
    assert trades == []

