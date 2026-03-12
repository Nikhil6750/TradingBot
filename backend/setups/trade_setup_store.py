from __future__ import annotations

from bisect import bisect_left
from typing import Any, Dict, List, Optional, Tuple


_SETUP_CACHE: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
_LATEST_TIMEFRAME_BY_DATASET: Dict[str, str] = {}


def _find_candle_index(candle_times: List[int], timestamp: int) -> int:
    if not candle_times:
        return -1

    position = bisect_left(candle_times, timestamp)
    if position < len(candle_times) and candle_times[position] == timestamp:
        return position
    if position == 0:
        return 0
    if position >= len(candle_times):
        return len(candle_times) - 1
    before = candle_times[position - 1]
    after = candle_times[position]
    return position if abs(after - timestamp) < abs(timestamp - before) else position - 1


def build_trade_setups(
    candles: List[Dict[str, Any]],
    buy_signals: List[Dict[str, Any]],
    sell_signals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    candle_times = [int(candle.get("time", 0)) for candle in candles]
    combined_signals: List[Tuple[str, Dict[str, Any]]] = []
    combined_signals.extend(("BUY", signal) for signal in (buy_signals or []))
    combined_signals.extend(("SELL", signal) for signal in (sell_signals or []))

    setups: List[Dict[str, Any]] = []
    for signal_type, signal in sorted(
        combined_signals,
        key=lambda item: (int(item[1].get("time", 0)), 0 if item[0] == "BUY" else 1),
    ):
        timestamp = int(signal.get("time", 0))
        candle_index = _find_candle_index(candle_times, timestamp)
        reference_price = signal.get("price")
        if reference_price is None and 0 <= candle_index < len(candles):
            reference_price = candles[candle_index].get("close", 0)

        setups.append({
            "index": candle_index,
            "price": float(reference_price or 0.0),
            "type": signal_type,
        })

    return setups


def store_trade_setups(dataset_id: str, timeframe: str, setups: List[Dict[str, Any]]) -> None:
    normalized_timeframe = str(timeframe or "1m")
    key = (str(dataset_id), normalized_timeframe)
    _SETUP_CACHE[key] = list(setups or [])
    _LATEST_TIMEFRAME_BY_DATASET[str(dataset_id)] = normalized_timeframe


def get_trade_setups(dataset_id: str, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
    normalized_dataset_id = str(dataset_id)
    normalized_timeframe = str(timeframe) if timeframe else _LATEST_TIMEFRAME_BY_DATASET.get(normalized_dataset_id)
    if not normalized_timeframe:
        return []
    return list(_SETUP_CACHE.get((normalized_dataset_id, normalized_timeframe), []))


def get_latest_trade_setup_timeframe(dataset_id: str) -> Optional[str]:
    return _LATEST_TIMEFRAME_BY_DATASET.get(str(dataset_id))
