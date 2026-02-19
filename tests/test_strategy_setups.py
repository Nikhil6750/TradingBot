from bot.strategy_engine import generate_trades, generate_trades_and_setups


def _c(t, o, h, l, c, v=0.0):
    return {"time": int(t), "open": float(o), "high": float(h), "low": float(l), "close": float(c), "volume": float(v)}


def test_generate_trades_and_setups_emits_setup_when_pullback_completes():
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

    trades_only = generate_trades(candles)
    trades, setups = generate_trades_and_setups(candles)

    assert trades == trades_only
    assert setups == [{"time": 1500, "direction": "BUY", "streak_length": 4, "pullback_length": 1, "target": 1.03}]


def test_setup_is_emitted_even_if_no_trade_executes():
    candles = [
        _c(0, 1.00, 1.01, 1.00, 1.01),
        _c(300, 1.01, 1.02, 1.01, 1.02),
        _c(600, 1.02, 1.03, 1.02, 1.03),
        _c(900, 1.03, 1.04, 1.03, 1.04),  # LSC (target=1.03)
        _c(1200, 1.04, 1.04, 1.032, 1.035),  # pullback
        _c(1500, 1.020, 1.040, 1.018, 1.035),  # pullback ended, but breaking condition fails (close >= target)
    ]

    trades, setups = generate_trades_and_setups(candles)
    assert trades == []
    assert setups == [{"time": 1500, "direction": "BUY", "streak_length": 4, "pullback_length": 1, "target": 1.03}]


def test_invalid_pullback_does_not_emit_setup():
    candles = [
        _c(0, 1.00, 1.01, 1.00, 1.01),
        _c(300, 1.01, 1.02, 1.01, 1.02),
        _c(600, 1.02, 1.03, 1.02, 1.03),
        _c(900, 1.03, 1.04, 1.03, 1.04),  # LSC (open=1.03)
        _c(1200, 1.04, 1.04, 1.020, 1.030),  # pullback bearish, breaches LSC.open -> invalid
        _c(1500, 1.030, 1.040, 1.028, 1.035),  # would end pullback
    ]

    trades, setups = generate_trades_and_setups(candles)
    assert trades == []
    assert setups == []

