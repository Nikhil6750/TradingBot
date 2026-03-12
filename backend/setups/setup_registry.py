from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_PINE_SCRIPT = """//@version=5
strategy("MA Crossover", overlay=true)
fastLength = input.int(12, "Fast Length")
slowLength = input.int(26, "Slow Length")
fast = ta.ema(close, fastLength)
slow = ta.ema(close, slowLength)
longCondition = ta.crossover(fast, slow)
shortCondition = ta.crossunder(fast, slow)

if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.entry("Short", strategy.short)
"""


_SETUPS: List[Dict[str, Any]] = [
    {
        "id": "ma_crossover",
        "name": "Moving Average Crossover",
        "mode": "template",
        "strategy": "ma_crossover",
        "parameters": {
            "fast_period": 10,
            "slow_period": 30,
            "ma_type": "EMA",
        },
    },
    {
        "id": "rsi_reversal",
        "name": "RSI Reversal",
        "mode": "template",
        "strategy": "rsi_reversal",
        "parameters": {
            "rsi_length": 14,
            "oversold": 30,
            "overbought": 70,
        },
    },
    {
        "id": "breakout",
        "name": "Breakout",
        "mode": "template",
        "strategy": "breakout",
        "parameters": {
            "lookback_period": 20,
            "breakout_threshold": 0.25,
        },
    },
    {
        "id": "mean_reversion",
        "name": "Mean Reversion",
        "mode": "template",
        "strategy": "mean_reversion",
        "parameters": {
            "lookback_period": 20,
            "deviation_threshold": 2.0,
        },
    },
    {
        "id": "pine_script",
        "name": "Pine Script Setup",
        "mode": "pine",
        "strategy": "pine_script",
        "parameters": {},
    },
]


def list_setups() -> List[Dict[str, Any]]:
    return [
        {
            "id": setup["id"],
            "name": setup["name"],
            "mode": setup["mode"],
            "strategy": setup["strategy"],
        }
        for setup in _SETUPS
    ]


def get_setup(setup_id: str) -> Dict[str, Any]:
    for setup in _SETUPS:
        if setup["id"] == setup_id:
            return setup
    raise ValueError(f"Unknown setup: {setup_id}")


def build_setup_config(
    setup_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    pine_script: str = "",
) -> Dict[str, Any]:
    setup = get_setup(setup_id)
    parameter_values = dict(setup.get("parameters", {}))
    if parameters:
        parameter_values.update({
            key: value
            for key, value in parameters.items()
            if value is not None
        })

    if setup["mode"] == "pine":
        return {
            "mode": "pine",
            "pine_script": pine_script.strip() or DEFAULT_PINE_SCRIPT,
        }

    return {
        "mode": "template",
        "strategy": setup["strategy"],
        "parameters": parameter_values,
    }
