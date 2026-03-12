from pathlib import Path
import sys

import pandas as pd
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.server import app
from backend.strategies.breakout import run_breakout
from backend.strategies.ma_crossover import run_ma_crossover
from backend.strategies.pine_script_strategy import run_pine_script_strategy


def _frame(rows):
    return pd.DataFrame(rows)


def test_ma_crossover_supports_ema_parameters():
    frame = _frame([
        {"time": 1, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 10},
        {"time": 2, "open": 1.0, "high": 1.2, "low": 0.95, "close": 1.1, "volume": 12},
        {"time": 3, "open": 1.1, "high": 1.4, "low": 1.05, "close": 1.3, "volume": 11},
        {"time": 4, "open": 1.3, "high": 1.45, "low": 1.2, "close": 1.4, "volume": 9},
        {"time": 5, "open": 1.4, "high": 1.45, "low": 1.0, "close": 1.05, "volume": 15},
    ])

    result = run_ma_crossover(frame, {"fast_period": 2, "slow_period": 3, "ma_type": "EMA"})

    assert result["buy_signals"]
    assert result["sell_signals"]
    assert result["indicators"]["ma_type"] == "EMA"


def test_breakout_uses_threshold_percentage():
    frame = _frame([
        {"time": 1, "open": 10.0, "high": 10.2, "low": 9.8, "close": 10.0, "volume": 10},
        {"time": 2, "open": 10.0, "high": 10.3, "low": 9.9, "close": 10.1, "volume": 12},
        {"time": 3, "open": 10.1, "high": 10.4, "low": 10.0, "close": 10.2, "volume": 11},
        {"time": 4, "open": 10.2, "high": 10.45, "low": 10.1, "close": 10.22, "volume": 10},
        {"time": 5, "open": 10.22, "high": 10.55, "low": 10.2, "close": 10.51, "volume": 14},
    ])

    no_threshold = run_breakout(frame, {"lookback_period": 3, "breakout_threshold": 0})
    strong_threshold = run_breakout(frame, {"lookback_period": 3, "breakout_threshold": 2.5})

    assert no_threshold["buy_signals"]
    assert strong_threshold["buy_signals"] == []


def test_pine_script_engine_generates_buy_and_sell_signals():
    frame = _frame([
        {"time": 1, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"time": 2, "open": 100, "high": 100, "low": 98, "close": 99, "volume": 12},
        {"time": 3, "open": 99, "high": 99, "low": 97, "close": 98, "volume": 11},
        {"time": 4, "open": 98, "high": 103, "low": 97, "close": 102, "volume": 13},
        {"time": 5, "open": 102, "high": 105, "low": 101, "close": 104, "volume": 15},
        {"time": 6, "open": 104, "high": 104, "low": 100, "close": 101, "volume": 14},
        {"time": 7, "open": 101, "high": 102, "low": 96, "close": 97, "volume": 16},
    ])
    pine_script = """
//@version=5
strategy("EMA Cross", overlay=true)
fast = ta.ema(close, 2)
slow = ta.sma(close, 3)
goLong = ta.crossover(fast, slow)
goShort = ta.crossunder(fast, slow)

if goLong
    strategy.entry("Long", strategy.long)

if goShort
    strategy.entry("Short", strategy.short)
"""

    result = run_pine_script_strategy(frame, {"pine_script": pine_script})

    assert result["buy_signals"]
    assert result["sell_signals"]


def test_run_strategy_alias_returns_candles_and_indexed_setups(monkeypatch):
    candles = [
        {"time": 1, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 1.0},
        {"time": 2, "open": 1.0, "high": 1.2, "low": 0.95, "close": 1.1, "volume": 1.0},
    ]

    def fake_load_dataset_candles(*_args, **_kwargs):
        return candles

    def fake_run_strategy(*_args, **_kwargs):
        return {
            "buy_signals": [{"time": 2, "price": 1.1, "type": "BUY"}],
            "sell_signals": [],
            "trades": [],
            "metrics": {},
            "indicators": {},
        }

    monkeypatch.setattr("backend.api.backtest_routes.load_dataset_candles", fake_load_dataset_candles)
    monkeypatch.setattr("backend.api.backtest_routes.run_strategy", fake_run_strategy)

    client = TestClient(app)
    response = client.post("/run-strategy", json={
        "symbol": "demo-dataset",
        "timeframe": "1h",
        "config": {"mode": "template", "strategy": "ma_crossover", "parameters": {"fast_period": 10, "slow_period": 30, "ma_type": "EMA"}},
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["candles"] == candles
    assert payload["trade_setups"] == [{"index": 1, "type": "BUY", "price": 1.1}]
