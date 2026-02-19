from __future__ import annotations

from pathlib import Path

from backend.data_loader import load_candles_from_csv_path
from backend.gap_handling import generate_trades_with_gap_resets
from bot.strategy_engine import generate_trades


def _c(t, o, h, l, c, v=0.0):
    return {
        "time": int(t),
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
        "volume": float(v),
        "pattern_alert": None,
    }


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> Path:
    path.write_text(
        "\n".join([",".join(header)] + [",".join(map(str, r)) for r in rows]) + "\n",
        encoding="utf-8",
    )
    return path


def test_loader_allows_missing_candles_without_error(tmp_path: Path):
    csv_path = _write_csv(
        tmp_path / "candles.csv",
        header=["time", "open", "high", "low", "close", "volume"],
        rows=[
            [0, 1.0, 1.0, 1.0, 1.0, 0],
            [300, 1.0, 1.0, 1.0, 1.0, 0],
            # Missing candle at 600 -> next is 900 (gap=600s)
            [900, 1.0, 1.0, 1.0, 1.0, 0],
        ],
    )
    candles = load_candles_from_csv_path(csv_path)
    assert [c["time"] for c in candles] == [0, 300, 900]


def test_trades_do_not_span_across_gaps():
    # This is the same bullish setup used in tests/test_strategy_engine.py, but we insert a gap between entry and exit.
    candles = [
        _c(0, 1.00, 1.01, 1.00, 1.01),
        _c(300, 1.01, 1.02, 1.01, 1.02),
        _c(600, 1.02, 1.03, 1.02, 1.03),
        _c(900, 1.03, 1.04, 1.03, 1.04),  # LSC (target=1.03)
        _c(1200, 1.04, 1.04, 1.032, 1.035),  # pullback touches mid -> Case A
        _c(1500, 1.020, 1.026, 1.018, 1.025),  # breaking close < target
        _c(1800, 1.024, 1.029, 1.023, 1.028),  # confirmation -> entry
        _c(3000, 1.028, 1.032, 1.027, 1.031),  # gap here (1800 -> 3000), touches target -> would exit
    ]

    # Strategy engine alone would produce a trade that spans the gap.
    direct = generate_trades(candles)
    assert len(direct) == 1
    assert direct[0]["entry"]["time"] == 1800
    assert direct[0]["exit"]["time"] == 3000

    # Gap-aware wrapper must drop trades that would span gaps.
    wrapped = generate_trades_with_gap_resets(candles)
    assert wrapped == []


def test_strategy_resets_at_gaps_and_continues_processing():
    # Segment 1: creates an entry but never exits (blocks further trades in the engine).
    seg1 = [
        _c(0, 1.00, 1.01, 1.00, 1.01),
        _c(300, 1.01, 1.02, 1.01, 1.02),
        _c(600, 1.02, 1.03, 1.02, 1.03),
        _c(900, 1.03, 1.04, 1.03, 1.04),  # LSC (target=1.03)
        _c(1200, 1.04, 1.04, 1.032, 1.035),  # pullback touches mid -> Case A
        _c(1500, 1.020, 1.026, 1.018, 1.025),  # breaking close < target
        _c(1800, 1.024, 1.029, 1.023, 1.028),  # confirmation -> entry
        # After entry: never touches target 1.03 (high always < 1.03)
        _c(2100, 1.028, 1.029, 1.020, 1.021),
        _c(2400, 1.021, 1.025, 1.015, 1.018),
    ]

    # Gap to segment 2 (reset) and run a complete trade there.
    off = 3600
    seg2 = [
        # Use a distinct price region to ensure segment 1's open trade target is never touched across the gap.
        _c(off + 0, 2.00, 2.01, 2.00, 2.01),
        _c(off + 300, 2.01, 2.02, 2.01, 2.02),
        _c(off + 600, 2.02, 2.03, 2.02, 2.03),
        _c(off + 900, 2.03, 2.04, 2.03, 2.04),  # LSC (target=2.03)
        _c(off + 1200, 2.04, 2.04, 2.032, 2.035),
        _c(off + 1500, 2.020, 2.026, 2.018, 2.025),
        _c(off + 1800, 2.024, 2.029, 2.023, 2.028),  # entry
        _c(off + 2100, 2.028, 2.032, 2.027, 2.031),  # exit
    ]

    candles = seg1 + seg2

    # Engine alone returns early at the open trade and never reaches segment 2.
    assert generate_trades(candles) == []

    wrapped = generate_trades_with_gap_resets(candles)
    assert len(wrapped) == 1
    assert wrapped[0]["entry"]["time"] == off + 1800
    assert wrapped[0]["exit"]["time"] == off + 2100
