from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.data_loader import CandleCSVError, load_candles_from_csv_path


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> Path:
    path.write_text(
        "\n".join([",".join(header)] + [",".join(map(str, r)) for r in rows]) + "\n",
        encoding="utf-8",
    )
    return path


def test_time_column_is_accepted_as_timestamp_alias(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["time", "open", "high", "low", "close", "volume"],
        rows=[
            [0, 1.0, 1.1, 0.9, 1.05, 10],
            [300, 1.05, 1.2, 1.0, 1.15, 11],
        ],
    )
    candles = load_candles_from_csv_path(csv_path)
    assert [c["time"] for c in candles] == [0, 300]


def test_epoch_milliseconds_are_converted_to_seconds_before_continuity_checks(tmp_path: Path):
    # 300 seconds == 300_000 ms
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["Time", "Open", "High", "Low", "Close", "Volume"],
        rows=[
            [1_700_000_000_000, 1.0, 1.1, 0.9, 1.05, 10],
            [1_700_000_300_000, 1.05, 1.2, 1.0, 1.15, 11],
        ],
    )
    candles = load_candles_from_csv_path(csv_path)
    assert [c["time"] for c in candles] == [1_700_000_000, 1_700_000_300]


def test_iso_datetime_strings_are_parsed_to_epoch_seconds(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["datetime", "open", "high", "low", "close", "volume"],
        rows=[
            ["2024-01-01T00:00:00Z", 1.0, 1.1, 0.9, 1.05, 10],
            ["2024-01-01T00:05:00Z", 1.05, 1.2, 1.0, 1.15, 11],
        ],
    )
    candles = load_candles_from_csv_path(csv_path)
    base = int(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    assert [c["time"] for c in candles] == [base, base + 300]


def test_missing_timestamp_alias_is_rejected_with_clear_error(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["open", "high", "low", "close", "volume"],
        rows=[[1.0, 1.1, 0.9, 1.05, 10]],
    )
    with pytest.raises(CandleCSVError, match=r"Missing required timestamp column"):
        load_candles_from_csv_path(csv_path)


def test_multiple_timestamp_columns_are_rejected(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["timestamp", "time", "open", "high", "low", "close", "volume"],
        rows=[[0, 0, 1.0, 1.1, 0.9, 1.05, 10], [300, 300, 1.05, 1.2, 1.0, 1.15, 11]],
    )
    with pytest.raises(CandleCSVError, match=r"Multiple timestamp columns"):
        load_candles_from_csv_path(csv_path)


def test_unparseable_string_timestamp_is_rejected(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["date", "open", "high", "low", "close", "volume"],
        rows=[["not-a-date", 1.0, 1.1, 0.9, 1.05, 10]],
    )
    with pytest.raises(CandleCSVError, match=r"Invalid timestamp"):
        load_candles_from_csv_path(csv_path)

