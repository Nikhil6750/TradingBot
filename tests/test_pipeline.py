import pandas as pd
import pytest

from bot.backtest import NoStrategy, Trade, candles_from_dataframe, run_backtest


def _sample_df():
    return pd.DataFrame(
        {
            "time": [
                "2024-01-01T00:00:00Z",
                "2024-01-01T00:01:00Z",
                "2024-01-01T00:02:00Z",
            ],
            "open": [1.0, 1.1, 1.2],
            "high": [1.05, 1.15, 1.25],
            "low": [0.95, 1.05, 1.15],
            "close": [1.02, 1.12, 1.22],
        }
    )


def test_no_strategy_produces_zero_trades():
    candles = candles_from_dataframe(_sample_df(), tz_name="UTC")
    trades = run_backtest(candles, strategy=NoStrategy())
    assert trades == []


def test_trade_requires_explanation():
    class BadStrategy:
        def generate_trades(self, candles):
            return [
                Trade(
                    entry_time=pd.Timestamp("2024-01-01T00:00:00Z"),
                    entry_price=1.0,
                    exit_time=pd.Timestamp("2024-01-01T00:01:00Z"),
                    exit_price=1.1,
                    direction="long",
                    streak_length=4,
                    pullback_length=1,
                    target=1.05,
                    explanation="",
                )
            ]

    candles = candles_from_dataframe(_sample_df(), tz_name="UTC")
    with pytest.raises(ValueError):
        run_backtest(candles, strategy=BadStrategy())


def test_candles_require_time_column():
    df = pd.DataFrame({"open": [1], "high": [1], "low": [1], "close": [1]})
    with pytest.raises(ValueError):
        candles_from_dataframe(df, tz_name="UTC")
