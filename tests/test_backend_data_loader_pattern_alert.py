from __future__ import annotations

from pathlib import Path

import pytest

from backend.data_loader import CandleCSVError, load_candles_from_csv_path
from bot.strategy_engine import generate_trades


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> Path:
    path.write_text(
        "\n".join([",".join(header)] + [",".join(map(str, r)) for r in rows]) + "\n",
        encoding="utf-8",
    )
    return path


def test_csv_with_pattern_alert_is_parsed_as_optional_metadata(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "FX_EURUSD.csv",
        header=["Timestamp", "Open", "High", "Low", "Close", "Volume", "PATTERN ALERT", "ignored"],
        rows=[
            [0, 1.0, 1.1, 0.9, 1.05, 10, "", "x"],
            [300, 1.05, 1.2, 1.0, 1.15, 11, "1", "y"],
            [600, 1.15, 1.3, 1.1, 1.2, 12, "Bearish Engulfing", "z"],
        ],
    )

    candles = load_candles_from_csv_path(csv_path)
    assert candles[0]["pattern_alert"] is None
    assert candles[1]["pattern_alert"] is True
    assert candles[2]["pattern_alert"] == "Bearish Engulfing"


def test_csv_without_pattern_alert_sets_pattern_alert_to_null(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "FX_EURUSD.csv",
        header=["timestamp", "open", "high", "low", "close", "volume", "extra"],
        rows=[
            [0, 1.0, 1.1, 0.9, 1.05, 10, "x"],
            [300, 1.05, 1.2, 1.0, 1.15, 11, "y"],
        ],
    )

    candles = load_candles_from_csv_path(csv_path)
    assert all("pattern_alert" in c for c in candles)
    assert all(c["pattern_alert"] is None for c in candles)


def test_pattern_alert_does_not_change_trade_generation(tmp_path: Path):
    rows = [
        [0, 1.00, 1.01, 1.00, 1.01, 0, 0],
        [300, 1.01, 1.02, 1.01, 1.02, 0, 0],
        [600, 1.02, 1.03, 1.02, 1.03, 0, 1],
        [900, 1.03, 1.04, 1.03, 1.04, 0, 0],
        [1200, 1.04, 1.04, 1.032, 1.035, 0, "pb"],
        [1500, 1.020, 1.026, 1.018, 1.025, 0, "break"],
        [1800, 1.024, 1.029, 1.023, 1.028, 0, "confirm"],
        [2100, 1.028, 1.032, 1.027, 1.031, 0, ""],
    ]

    with_pa = _write_csv(
        tmp_path / "with_pa.csv",
        header=["timestamp", "open", "high", "low", "close", "volume", "Pattern Alert"],
        rows=rows,
    )
    without_pa = _write_csv(
        tmp_path / "without_pa.csv",
        header=["timestamp", "open", "high", "low", "close", "volume"],
        rows=[r[:6] for r in rows],
    )

    candles_with = load_candles_from_csv_path(with_pa)
    candles_without = load_candles_from_csv_path(without_pa)

    trades_with = generate_trades(candles_with)
    trades_without = generate_trades(candles_without)

    assert trades_with == trades_without


def test_pattern_alert_is_never_required(tmp_path: Path):
    # This test asserts we do not accidentally enforce Pattern Alert as a required column.
    csv_path = _write_csv(
        tmp_path / "no_pa.csv",
        header=["timestamp", "open", "high", "low", "close", "volume"],
        rows=[[0, 1.0, 1.0, 1.0, 1.0, 0], [300, 1.0, 1.0, 1.0, 1.0, 0]],
    )

    candles = load_candles_from_csv_path(csv_path)
    assert len(candles) == 2


def test_missing_required_columns_still_fails_strictly(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "bad.csv",
        header=["timestamp", "open", "high", "low", "close"],
        rows=[[0, 1.0, 1.0, 1.0, 1.0]],
    )

    with pytest.raises(CandleCSVError):
        load_candles_from_csv_path(csv_path)

