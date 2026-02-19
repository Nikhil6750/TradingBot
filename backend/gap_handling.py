from __future__ import annotations

from typing import Final, List

from bot.strategy_engine import generate_trades, generate_trades_and_setups

EXPECTED_STEP_SECONDS: Final[int] = 300


def split_candles_on_gaps(candles: List[dict], *, expected_step_seconds: int = EXPECTED_STEP_SECONDS) -> List[List[dict]]:
    if not candles:
        return []

    segments: list[list[dict]] = []
    start = 0
    for i in range(1, len(candles)):
        try:
            prev_time = int(candles[i - 1]["time"])
            curr_time = int(candles[i]["time"])
        except Exception:
            # Candle validation should guarantee this, but keep the split deterministic.
            continue

        if curr_time - prev_time > int(expected_step_seconds):
            seg = candles[start:i]
            if seg:
                segments.append(seg)
            start = i

    tail = candles[start:]
    if tail:
        segments.append(tail)
    return segments


def generate_trades_with_gap_resets(candles: List[dict], *, expected_step_seconds: int = EXPECTED_STEP_SECONDS) -> List[dict]:
    """
    Runs the locked strategy engine while ensuring trades do not span time gaps.

    When a gap (> expected_step_seconds) is detected between consecutive candles, strategy state is reset by
    splitting the candle stream into continuous segments and running the engine independently per segment.
    """
    trades: list[dict] = []
    for segment in split_candles_on_gaps(candles, expected_step_seconds=expected_step_seconds):
        trades.extend(generate_trades(segment))
    return trades


def generate_trades_and_setups_with_gap_resets(
    candles: List[dict], *, expected_step_seconds: int = EXPECTED_STEP_SECONDS
) -> tuple[List[dict], List[dict]]:
    """
    Runs the locked strategy engine while ensuring trades and setups do not span time gaps.

    When a gap (> expected_step_seconds) is detected between consecutive candles, strategy state is reset by
    splitting the candle stream into continuous segments and running the engine independently per segment.
    """
    trades: list[dict] = []
    setups: list[dict] = []
    for segment in split_candles_on_gaps(candles, expected_step_seconds=expected_step_seconds):
        seg_trades, seg_setups = generate_trades_and_setups(segment)
        trades.extend(seg_trades)
        setups.extend(seg_setups)
    return trades, setups
