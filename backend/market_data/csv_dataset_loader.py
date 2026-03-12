from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd
from fastapi import HTTPException

from backend.market_data.dataset_normalizer import CANONICAL_COLUMNS, load_dataset_dataframe

TIMEFRAME_RULES = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


def _filter_dataframe(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    filtered = df.copy()

    if start:
        start_ts = pd.to_datetime(start, utc=True)
        filtered = filtered[filtered["timestamp"] >= start_ts]

    if end:
        end_ts = pd.to_datetime(end, utc=True)
        filtered = filtered[filtered["timestamp"] <= end_ts]

    if limit:
        filtered = filtered.tail(int(limit))

    return filtered.reset_index(drop=True)


def resample_dataset_dataframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    normalized_timeframe = (timeframe or "1m").lower()
    if normalized_timeframe in {"raw", "1m"}:
        return df.copy().reset_index(drop=True)

    if normalized_timeframe not in TIMEFRAME_RULES:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe: {timeframe}")

    resampled = (
        df.set_index("timestamp")
        .resample(TIMEFRAME_RULES[normalized_timeframe])
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )

    return resampled[CANONICAL_COLUMNS]


def dataframe_to_candles(df: pd.DataFrame) -> list[dict]:
    return [
        {
            "time": int(pd.Timestamp(row["timestamp"]).timestamp()),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for _, row in df[CANONICAL_COLUMNS].iterrows()
    ]


def load_dataset_candles(
    dataset_id: str,
    datasets_dir: Union[str, Path],
    timeframe: str = "1m",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    df = load_dataset_dataframe(dataset_id, datasets_dir)
    resampled = resample_dataset_dataframe(df, timeframe)
    filtered = _filter_dataframe(resampled, start=start, end=end, limit=limit)
    return dataframe_to_candles(filtered)


def load_dataset_summary(dataset_id: str, datasets_dir: Union[str, Path]) -> dict:
    df = load_dataset_dataframe(dataset_id, datasets_dir)
    start = pd.Timestamp(df["timestamp"].iloc[0]).isoformat() if not df.empty else None
    end = pd.Timestamp(df["timestamp"].iloc[-1]).isoformat() if not df.empty else None

    return {
        "id": dataset_id,
        "dataset_id": dataset_id,
        "rows": int(len(df)),
        "start": start,
        "end": end,
        "columns": CANONICAL_COLUMNS,
        "status": "ready",
    }
