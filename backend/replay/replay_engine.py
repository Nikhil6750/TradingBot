from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from backend.data_providers.data_manager import data_manager
from backend.strategy_engine import run_strategy
from backend.utils.helpers import clean_data


def evaluate_replay(
    dataset_id: str,
    timeframe: str,
    config: Optional[dict[str, Any]] = None,
    cursor: Optional[int] = None,
) -> dict[str, Any]:
    candles = data_manager.load_candles(dataset_id, timeframe)
    if not candles:
        raise ValueError(f"No market data available for {dataset_id} {timeframe}")

    normalized_cursor = None
    visible_candles = candles
    if cursor is not None:
        normalized_cursor = max(0, min(int(cursor), len(candles) - 1))
        visible_candles = candles[: normalized_cursor + 1]

    strategy_config = config or {}
    df = pd.DataFrame(visible_candles)
    result = clean_data(run_strategy(df, strategy_config))

    current_candle = visible_candles[-1] if visible_candles else None
    return {
        "cursor": normalized_cursor,
        "candles": candles,
        "visible_candles": visible_candles,
        "current_candle": current_candle,
        "buy_signals": result.get("buy_signals", []),
        "sell_signals": result.get("sell_signals", []),
        "trades": result.get("trades", []),
        "metrics": result.get("metrics", {}),
        "indicators": result.get("indicators", {}),
    }
