from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

from bot.backtest import Trade


@dataclass(frozen=True, slots=True)
class LockedStreakPullbackStrategy:
    allow_long: bool = True
    allow_short: bool = True

    def generate_trades(self, candles: pd.DataFrame) -> list[Trade]:
        if candles is None or candles.empty:
            return []

        times = pd.to_datetime(candles["time"], utc=True, errors="coerce").to_numpy()
        open_ = candles["open"].to_numpy(dtype="float64")
        high = candles["high"].to_numpy(dtype="float64")
        low = candles["low"].to_numpy(dtype="float64")
        close = candles["close"].to_numpy(dtype="float64")

        bull = close > open_
        bear = close < open_
        doji = close == open_
        color = np.where(bull, 1, np.where(bear, -1, 0)).astype("int8")

        n: Final[int] = int(len(close))
        trades: list[Trade] = []

        i = 0
        while i < n:
            if color[i] == 0:
                i += 1
                continue

            streak_dir = int(color[i])  # 1 bullish, -1 bearish
            streak_start = i
            j = i
            while j < n and color[j] == streak_dir:
                j += 1
            streak_len = j - streak_start
            if streak_len < 4:
                i = j
                continue

            lsc_idx = j - 1

            pb_start = j
            if pb_start >= n:
                break

            if color[pb_start] != -streak_dir:
                # No opposite candle immediately after the streak -> no pullback setup here.
                i = pb_start
                continue

            pb_len = 1
            if pb_start + 1 < n and color[pb_start + 1] == -streak_dir:
                pb_len = 2

            lsc_open = float(open_[lsc_idx])
            pb_low = float(np.min(low[pb_start : pb_start + pb_len]))
            pb_high = float(np.max(high[pb_start : pb_start + pb_len]))

            if streak_dir == 1:
                if pb_low < lsc_open:
                    i = pb_start + pb_len
                    continue
            else:
                if pb_high > lsc_open:
                    i = pb_start + pb_len
                    continue

            lsc_mid = (float(high[lsc_idx]) + float(low[lsc_idx])) / 2.0
            touched_50 = bool(
                np.any((low[pb_start : pb_start + pb_len] <= lsc_mid) & (high[pb_start : pb_start + pb_len] >= lsc_mid))
            )

            if touched_50:
                target = float(low[lsc_idx]) if streak_dir == 1 else float(high[lsc_idx])
            else:
                target = pb_low if streak_dir == 1 else pb_high

            breaking_idx = pb_start + pb_len
            if breaking_idx >= n:
                break
            if color[breaking_idx] == 0:
                i = breaking_idx + 1
                continue

            breaking_close = float(close[breaking_idx])
            if streak_dir == 1:
                if not (breaking_close < target):
                    i = breaking_idx
                    continue
            else:
                if not (breaking_close > target):
                    i = breaking_idx
                    continue

            confirm_idx = breaking_idx + 1
            if confirm_idx >= n:
                break

            if color[confirm_idx] != streak_dir:
                i = confirm_idx
                continue

            if streak_dir == 1 and not self.allow_long:
                i = confirm_idx + 1
                continue
            if streak_dir == -1 and not self.allow_short:
                i = confirm_idx + 1
                continue

            entry_time = pd.Timestamp(times[confirm_idx]).tz_convert("UTC")
            entry_price = float(close[confirm_idx])
            direction = "long" if streak_dir == 1 else "short"

            exit_idx = _find_first_touch_after(low, high, target=target, start_idx=confirm_idx + 1)
            if exit_idx is None:
                break  # No overlap: an open trade blocks any further setups

            exit_time = pd.Timestamp(times[exit_idx]).tz_convert("UTC")
            exit_price = float(target)

            explanation = _explain_trade(
                direction=direction,
                streak_len=int(streak_len),
                pullback_len=int(pb_len),
                lsc_open=lsc_open,
                lsc_mid=lsc_mid,
                touched_50=touched_50,
                target=target,
                breaking_close=breaking_close,
                entry_price=entry_price,
                exit_price=exit_price,
            )

            trades.append(
                Trade(
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=exit_time,
                    exit_price=exit_price,
                    direction=direction,
                    streak_length=int(streak_len),
                    pullback_length=int(pb_len),
                    target=float(target),
                    explanation=explanation,
                )
            )

            # No overlap: skip to the first candle after exit
            i = exit_idx + 1

        return trades


def _find_first_touch_after(low: np.ndarray, high: np.ndarray, target: float, start_idx: int) -> int | None:
    for k in range(int(start_idx), int(len(low))):
        if float(low[k]) <= target <= float(high[k]):
            return int(k)
    return None


def _explain_trade(
    *,
    direction: str,
    streak_len: int,
    pullback_len: int,
    lsc_open: float,
    lsc_mid: float,
    touched_50: bool,
    target: float,
    breaking_close: float,
    entry_price: float,
    exit_price: float,
) -> str:
    side = "Bullish" if direction == "long" else "Bearish"
    pb = "bearish" if direction == "long" else "bullish"
    case = "A (pullback touched 50%)" if touched_50 else "B (pullback did not touch 50%)"
    break_rel = "<" if direction == "long" else ">"
    return (
        f"{side} setup: streak={streak_len}, pullback={pullback_len} ({pb}). "
        f"LSC.open={lsc_open:.5f}, LSC.50%={lsc_mid:.5f}. "
        f"Case {case} -> target={target:.5f}. "
        f"Breaking candle close {break_rel} target ({breaking_close:.5f}). "
        f"Entry at confirmation close={entry_price:.5f}; exit at target={exit_price:.5f}."
    )
