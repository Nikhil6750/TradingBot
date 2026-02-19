from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, List, Literal


TradeDirection = Literal["BUY", "SELL"]
SetupDirection = TradeDirection


class _State(str, Enum):
    SEEK_STREAK = "SEEK_STREAK"
    IN_STREAK = "IN_STREAK"
    IN_PULLBACK = "IN_PULLBACK"
    AWAIT_CONFIRMATION = "AWAIT_CONFIRMATION"


@dataclass(frozen=True, slots=True)
class _PendingSetup:
    streak_dir: int  # 1 bullish, -1 bearish
    streak_length: int
    pullback_start_idx: int
    pullback_length: int
    target: float
    breaking_candle_time: int


def generate_trades(candles: List[dict]) -> List[dict]:
    trades, _setups = generate_trades_and_setups(candles)
    return trades


def generate_trades_and_setups(candles: List[dict]) -> tuple[List[dict], List[dict]]:
    """
    Locked Forex 5-minute strategy engine.

    Input candles are assumed validated (time-sorted, continuous 300s steps, correct fields).

    Returns:
      - executed/closed trades ONLY in the required normalized dict format
      - strategy setups for visualization (setups are not trades)
    """
    if not candles:
        return [], []

    trades: list[dict] = []
    setups: list[dict] = []
    n: Final[int] = len(candles)

    state: _State = _State.SEEK_STREAK

    streak_dir: int = 0
    streak_start_idx: int = 0
    streak_length: int = 0

    lsc_idx: int | None = None
    setup_streak_length: int | None = None
    pullback_start_idx: int | None = None
    pullback_length: int | None = None

    pending: _PendingSetup | None = None

    i = 0
    while i < n:
        candle = candles[i]
        c_dir = _candle_dir(candle)

        if state == _State.SEEK_STREAK:
            if c_dir == 0:
                i += 1
                continue
            streak_dir = c_dir
            streak_start_idx = i
            streak_length = 1
            state = _State.IN_STREAK
            i += 1
            continue

        if state == _State.IN_STREAK:
            if c_dir == streak_dir:
                streak_length += 1
                i += 1
                continue

            if c_dir == 0:
                state = _State.SEEK_STREAK
                i += 1
                continue

            # Opposite candle encountered
            if streak_length >= 4:
                lsc_idx = i - 1
                setup_streak_length = streak_length
                pullback_start_idx = i
                pullback_length = 1
                state = _State.IN_PULLBACK
                i += 1
                continue

            # Streak too short -> start a new streak from this candle
            streak_dir = c_dir
            streak_start_idx = i
            streak_length = 1
            i += 1
            continue

        if state == _State.IN_PULLBACK:
            assert lsc_idx is not None
            assert setup_streak_length is not None
            assert pullback_start_idx is not None
            assert pullback_length is not None

            if c_dir == 0:
                # Doji invalidates setup
                state = _State.SEEK_STREAK
                i += 1
                continue

            if c_dir == -streak_dir:
                # Extend pullback (max 2)
                if pullback_length == 1:
                    pullback_length = 2
                    i += 1
                    continue

                # 3rd opposite candle -> pullback too long; discard setup and roll into new streak from pullback start
                streak_dir = c_dir
                streak_start_idx = pullback_start_idx
                streak_length = pullback_length + 1
                state = _State.IN_STREAK
                i += 1
                continue

            # Pullback ended; current candle is breaking candle (must be same direction as the original streak)
            if c_dir != streak_dir:
                # Defensive: should not happen with the candle_dir tri-state, but keep strict.
                state = _State.SEEK_STREAK
                i += 1
                continue

            pullback = candles[pullback_start_idx : pullback_start_idx + pullback_length]
            lsc = candles[lsc_idx]

            if _pullback_invalid(streak_dir=streak_dir, lsc_open=lsc["open"], pullback=pullback):
                # Discard setup; start new streak from this candle
                streak_dir = c_dir
                streak_start_idx = i
                streak_length = 1
                state = _State.IN_STREAK
                i += 1
                continue

            target = _compute_target(
                streak_dir=streak_dir,
                lsc_high=lsc["high"],
                lsc_low=lsc["low"],
                pullback=pullback,
            )

            setups.append(
                {
                    "time": int(candle["time"]),
                    "direction": "BUY" if streak_dir == 1 else "SELL",
                    "streak_length": int(setup_streak_length),
                    "pullback_length": int(pullback_length),
                    "target": float(target),
                }
            )

            if not _breaking_condition(streak_dir=streak_dir, close_price=candle["close"], target=target):
                # Discard setup; start new streak from this candle
                streak_dir = c_dir
                streak_start_idx = i
                streak_length = 1
                state = _State.IN_STREAK
                i += 1
                continue

            pending = _PendingSetup(
                streak_dir=streak_dir,
                streak_length=setup_streak_length,
                pullback_start_idx=pullback_start_idx,
                pullback_length=pullback_length,
                target=target,
                breaking_candle_time=int(candle["time"]),
            )
            state = _State.AWAIT_CONFIRMATION
            i += 1
            continue

        if state == _State.AWAIT_CONFIRMATION:
            assert pending is not None

            # Confirmation candle must be NEXT candle only and must match original streak direction.
            if c_dir != pending.streak_dir:
                # Discard setup permanently; this candle may start a new streak.
                if c_dir == 0:
                    state = _State.SEEK_STREAK
                    i += 1
                    continue

                streak_dir = c_dir
                streak_start_idx = i
                streak_length = 1
                state = _State.IN_STREAK
                i += 1
                continue

            # Entry at close of confirmation candle.
            entry_time = int(candle["time"])
            entry_price = float(candle["close"])
            direction: TradeDirection = "BUY" if pending.streak_dir == 1 else "SELL"

            exit_idx = _find_first_target_touch(candles, start_idx=i + 1, target=pending.target)
            if exit_idx is None:
                # Entry happened; exit never happens -> do not include the trade, and no overlap blocks further trades.
                return trades, setups

            exit_candle = candles[exit_idx]
            trades.append(
                {
                    "direction": direction,
                    "streak_length": int(pending.streak_length),
                    "pullback_length": int(pending.pullback_length),
                    "target": float(pending.target),
                    "breaking_candle_time": int(pending.breaking_candle_time),
                    "entry": {"time": entry_time, "price": entry_price},
                    "exit": {"time": int(exit_candle["time"]), "price": float(pending.target)},
                }
            )

            # No overlap: resume scanning after the exit candle.
            pending = None
            state = _State.SEEK_STREAK
            i = exit_idx + 1
            continue

        raise RuntimeError(f"Unknown state: {state}")

    return trades, setups


def _candle_dir(c: dict) -> int:
    o = c["open"]
    cl = c["close"]
    if cl > o:
        return 1
    if cl < o:
        return -1
    return 0


def _pullback_invalid(*, streak_dir: int, lsc_open: float, pullback: list[dict]) -> bool:
    if streak_dir == 1:
        pb_low = min(float(x["low"]) for x in pullback)
        return pb_low < float(lsc_open)
    pb_high = max(float(x["high"]) for x in pullback)
    return pb_high > float(lsc_open)


def _compute_target(*, streak_dir: int, lsc_high: float, lsc_low: float, pullback: list[dict]) -> float:
    mid = (float(lsc_high) + float(lsc_low)) / 2.0
    touched = any(float(pb["low"]) <= mid <= float(pb["high"]) for pb in pullback)

    if touched:
        return float(lsc_low) if streak_dir == 1 else float(lsc_high)

    if streak_dir == 1:
        return min(float(pb["low"]) for pb in pullback)
    return max(float(pb["high"]) for pb in pullback)


def _breaking_condition(*, streak_dir: int, close_price: float, target: float) -> bool:
    close_val = float(close_price)
    tgt = float(target)
    if streak_dir == 1:
        return close_val < tgt
    return close_val > tgt


def _find_first_target_touch(candles: List[dict], *, start_idx: int, target: float) -> int | None:
    tgt = float(target)
    for k in range(int(start_idx), len(candles)):
        low = float(candles[k]["low"])
        high = float(candles[k]["high"])
        if low <= tgt <= high:
            return k
    return None
