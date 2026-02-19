from __future__ import annotations

import glob
import os
from typing import Final

import numpy as np
import pandas as pd

from bot.backtest import candles_from_dataframe

_ROOT: Final[str] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FOREX_DIR: Final[str] = os.path.join(_ROOT, "data", "forex")
_FOREX_SUFFIX: Final[str] = "_5m.csv"

_CANDLE_CACHE: dict[str, pd.DataFrame] = {}


def available_forex_pairs() -> list[str]:
    if not os.path.isdir(_FOREX_DIR):
        return []

    pairs: set[str] = set()
    for path in glob.glob(os.path.join(_FOREX_DIR, f"*{_FOREX_SUFFIX}")):
        base = os.path.basename(path)
        if not base.lower().endswith(_FOREX_SUFFIX):
            continue
        pair = base[: -len(_FOREX_SUFFIX)].strip().upper()
        if not pair or not pair.isalnum():
            continue
        pairs.add(pair)
    return sorted(pairs)


def load_forex_candles(pair: str) -> pd.DataFrame:
    sym = str(pair or "").strip().upper()
    if not sym:
        raise ValueError("Missing pair")

    if sym in _CANDLE_CACHE:
        return _CANDLE_CACHE[sym]

    path = os.path.join(_FOREX_DIR, f"{sym}{_FOREX_SUFFIX}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No internal forex CSV found for {sym} at {_FOREX_DIR}")

    raw = pd.read_csv(path)
    candles = candles_from_dataframe(raw, tz_name="UTC")
    _validate_5m_time_index(candles, symbol=sym)

    _CANDLE_CACHE[sym] = candles
    return candles


def _validate_5m_time_index(candles: pd.DataFrame, symbol: str) -> None:
    if candles.empty:
        raise ValueError(f"{symbol}: CSV produced zero candles")

    times = pd.to_datetime(candles["time"], utc=True, errors="coerce")
    if times.isna().any():
        raise ValueError(f"{symbol}: invalid time values in candles")

    t_sec = (times.astype("int64") // 1_000_000_000).to_numpy(dtype="int64")
    if (np.diff(t_sec) <= 0).any():
        raise ValueError(f"{symbol}: time index must be strictly increasing")

    diffs = np.diff(t_sec)
    if (diffs % 300 != 0).any():
        raise ValueError(f"{symbol}: expected 5-minute candles (diff must be multiple of 300 seconds)")
