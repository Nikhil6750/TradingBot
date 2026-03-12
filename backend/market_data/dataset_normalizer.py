from __future__ import annotations

from pathlib import Path
import re
from typing import Final, Optional, Union

import pandas as pd
from fastapi import HTTPException

CANONICAL_COLUMNS: Final[list[str]] = ["timestamp", "open", "high", "low", "close", "volume"]
REQUIRED_COLUMNS: Final[set[str]] = {"timestamp", "open", "high", "low", "close"}
OPTIONAL_DEFAULTS: Final[dict[str, float]] = {"volume": 0.0}

COLUMN_ALIASES: Final[dict[str, str]] = {
    "timestamp": "timestamp",
    "time": "timestamp",
    "date": "timestamp",
    "datetime": "timestamp",
    "open": "open",
    "open_price": "open",
    "o": "open",
    "high": "high",
    "high_price": "high",
    "h": "high",
    "low": "low",
    "low_price": "low",
    "l": "low",
    "close": "close",
    "close_price": "close",
    "c": "close",
    "volume": "volume",
    "vol": "volume",
    "tick_volume": "volume",
}


def normalize_column_name(value: str) -> str:
    normalized = str(value or "").lstrip("\ufeff").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return COLUMN_ALIASES.get(normalized, normalized)


def _coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    merged: dict[str, pd.Series] = {}

    for column in df.columns:
        series = df[column]
        if column not in merged:
            merged[column] = series
            continue
        merged[column] = merged[column].combine_first(series)

    return pd.DataFrame(merged)


def _parse_timestamps(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    numeric_values = numeric.dropna()

    if len(numeric_values) == len(series):
        max_abs = numeric_values.abs().max()
        if max_abs >= 10**14:
            unit = "ns"
        elif max_abs >= 10**11:
            unit = "ms"
        else:
            unit = "s"
        parsed = pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
    else:
        parsed = pd.to_datetime(series, utc=True, errors="coerce")

    if parsed.isna().any():
        bad_rows = parsed[parsed.isna()].index.tolist()[:5]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timestamp values found in CSV at rows: {bad_rows}",
        )

    return parsed


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    if result[columns].isna().any().any():
        bad_rows = result.index[result[columns].isna().any(axis=1)].tolist()[:5]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid numeric OHLCV values found in CSV at rows: {bad_rows}",
        )

    return result


def normalize_dataset_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [normalize_column_name(column) for column in normalized.columns]
    normalized = _coalesce_duplicate_columns(normalized)

    missing = REQUIRED_COLUMNS - set(normalized.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {sorted(missing)}",
        )

    for column, default in OPTIONAL_DEFAULTS.items():
        if column not in normalized.columns:
            normalized[column] = default

    normalized = normalized[[column for column in CANONICAL_COLUMNS if column in normalized.columns]].copy()
    normalized = _coerce_numeric(normalized, ["open", "high", "low", "close", "volume"])
    normalized["timestamp"] = _parse_timestamps(normalized["timestamp"])
    normalized = normalized.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)

    return normalized[CANONICAL_COLUMNS]


def get_dataset_csv_path(dataset_id: str, datasets_dir: Union[str, Path]) -> Path:
    return Path(datasets_dir) / f"{dataset_id}.csv"


def load_dataset_dataframe(dataset_id: str, datasets_dir: Union[str, Path]) -> pd.DataFrame:
    csv_path = get_dataset_csv_path(dataset_id, datasets_dir)
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset {dataset_id} not found")

    raw_df = pd.read_csv(csv_path)
    return normalize_dataset_dataframe(raw_df)
