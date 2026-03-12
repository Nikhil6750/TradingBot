from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.setups.trade_setup_store import build_trade_setups


def _candle(time, close):
    return {
        "time": int(time),
        "open": float(close),
        "high": float(close),
        "low": float(close),
        "close": float(close),
        "volume": 0.0,
    }


def test_build_trade_setups_returns_indexed_signals_only():
    candles = [
        _candle(100, 1.1000),
        _candle(200, 1.2000),
        _candle(300, 1.3000),
    ]

    setups = build_trade_setups(
        candles,
        buy_signals=[{"time": 200}],
        sell_signals=[{"time": 290, "price": 1.2950}],
    )

    assert setups == [
        {"index": 1, "type": "BUY", "price": 1.2},
        {"index": 2, "type": "SELL", "price": 1.295},
    ]


def test_build_trade_setups_uses_nearest_candle_index():
    candles = [
        _candle(1_000, 2.0100),
        _candle(2_000, 2.0200),
        _candle(3_000, 2.0300),
    ]

    setups = build_trade_setups(
        candles,
        buy_signals=[],
        sell_signals=[{"time": 2_499}],
    )

    assert setups == [{"index": 1, "type": "SELL", "price": 2.02}]
