from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Protocol, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    direction: Literal["long", "short"]
    streak_length: int
    pullback_length: int
    target: float
    explanation: str

    def to_dict(self) -> dict:
        return {
            "entry_time": _to_epoch_seconds(self.entry_time),
            "entry_price": float(self.entry_price),
            "exit_time": _to_epoch_seconds(self.exit_time),
            "exit_price": float(self.exit_price),
            "direction": self.direction,
            "streak_length": int(self.streak_length),
            "pullback_length": int(self.pullback_length),
            "target": float(self.target),
            "explanation": str(self.explanation),
        }


class Strategy(Protocol):
    def generate_trades(self, candles: pd.DataFrame) -> list[Trade]:
        """
        Input: Candle Series DataFrame with columns:
          time (UTC tz-aware), open, high, low, close, volume
        Output: Closed trades only (every trade must include both entry and exit).
        """


class NoStrategy:
    def generate_trades(self, candles: pd.DataFrame) -> list[Trade]:
        return []


def _to_utc_time(series: pd.Series, tz_name: str) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        v = pd.to_numeric(series, errors="coerce").astype("float64")
        finite = v[np.isfinite(v)]
        mx = float(finite.max()) if finite.size else 0.0
        unit = "s" if mx < 1e11 else ("ms" if mx < 1e14 else "ns")
        return pd.to_datetime(v, unit=unit, utc=True, errors="coerce")

    dt = pd.to_datetime(series, utc=False, errors="coerce")
    if getattr(dt.dt, "tz", None) is not None:
        return dt.dt.tz_convert("UTC")
    return dt.dt.tz_localize(tz_name or "UTC", nonexistent="shift_forward", ambiguous="NaT").dt.tz_convert("UTC")


def candles_from_dataframe(df: pd.DataFrame, tz_name: str = "UTC") -> pd.DataFrame:
    """
    CSV → Candle Series

    Produces a normalized candle series DataFrame with:
      time (UTC tz-aware), open, high, low, close, volume
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    cols = {str(c).strip().lower(): c for c in df.columns}
    time_col = cols.get("time") or cols.get("timestamp") or cols.get("date") or cols.get("datetime")
    if not time_col:
        raise ValueError("CSV must have a time column (time|timestamp|date|datetime).")

    def _col(name: str) -> str:
        c = cols.get(name)
        if not c:
            raise ValueError(f"CSV missing required column: {name}")
        return c

    open_col = _col("open")
    high_col = _col("high")
    low_col = _col("low")
    close_col = _col("close")
    volume_col = cols.get("volume") or cols.get("vol")

    out = pd.DataFrame(
        {
            "time": _to_utc_time(df[time_col], tz_name),
            "open": pd.to_numeric(df[open_col], errors="coerce"),
            "high": pd.to_numeric(df[high_col], errors="coerce"),
            "low": pd.to_numeric(df[low_col], errors="coerce"),
            "close": pd.to_numeric(df[close_col], errors="coerce"),
            "volume": pd.to_numeric(df[volume_col], errors="coerce") if volume_col else 0.0,
        }
    )

    out = out.dropna(subset=["time", "open", "high", "low", "close"])
    out = out.sort_values("time").reset_index(drop=True)
    out["volume"] = out["volume"].fillna(0.0).astype(float)
    return out


def run_backtest(candles: pd.DataFrame, strategy: Strategy | None = None) -> list[Trade]:
    """
    Candle Series → Strategy → Trades

    Trades must always include both entry and exit.
    """
    impl = strategy or NoStrategy()
    trades = impl.generate_trades(candles)

    for t in trades:
        if t.entry_time is None or t.exit_time is None:
            raise ValueError("Invalid trade: missing entry_time or exit_time.")
        if not np.isfinite(float(t.entry_price)) or not np.isfinite(float(t.exit_price)):
            raise ValueError("Invalid trade: entry_price/exit_price must be finite numbers.")
        if t.direction not in ("long", "short"):
            raise ValueError("Invalid trade: direction must be 'long' or 'short'.")
        if int(t.streak_length) < 4:
            raise ValueError("Invalid trade: streak_length must be >= 4.")
        if int(t.pullback_length) not in (1, 2):
            raise ValueError("Invalid trade: pullback_length must be 1 or 2.")
        if not np.isfinite(float(t.target)):
            raise ValueError("Invalid trade: target must be a finite number.")
        if not str(t.explanation).strip():
            raise ValueError("Invalid trade: explanation is required.")

    return trades


def compute_metrics(trades: Sequence[Trade]) -> dict:
    """
    Trades → Metrics
    """
    return {"trades": int(len(trades))}


def trades_to_frame(trades: Sequence[Trade], symbol: str | None = None) -> pd.DataFrame:
    rows = []
    for t in trades:
        r = asdict(t)
        r["entry_time"] = pd.to_datetime(r["entry_time"], utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
        r["exit_time"] = pd.to_datetime(r["exit_time"], utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
        if symbol:
            r["symbol"] = symbol
        rows.append(r)
    cols = [
        "symbol",
        "entry_time",
        "entry_price",
        "exit_time",
        "exit_price",
        "direction",
        "streak_length",
        "pullback_length",
        "target",
        "explanation",
    ]
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]


def _to_epoch_seconds(ts: pd.Timestamp) -> int:
    t = pd.to_datetime(ts, utc=True, errors="coerce")
    if pd.isna(t):
        return 0
    return int(t.value // 1_000_000_000)
