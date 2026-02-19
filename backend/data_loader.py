from __future__ import annotations

import csv
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, List

EXPECTED_COLUMNS: Final[list[str]] = ["timestamp", "open", "high", "low", "close", "volume"]
_PATTERN_ALERT_COLUMN: Final[str] = "pattern alert"
_TIMESTAMP_ALIASES: Final[tuple[str, ...]] = ("timestamp", "time", "date", "datetime")
ALLOWED_MARKETS: Final[set[str]] = {"forex", "crypto"}
_PAIR_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z0-9_]+$")


class CandleCSVError(ValueError):
    pass


def _normalize_header(value: str) -> str:
    v = str(value or "").lstrip("\ufeff").strip().lower()
    v = re.sub(r"\s+", " ", v)
    return v


def _parse_pattern_alert(value: str) -> bool | str | None:
    v = str(value or "").strip()
    if not v:
        return None

    v_norm = v.lower()
    if v_norm in {"1", "true", "t", "yes", "y"}:
        return True
    if v_norm in {"0", "false", "f", "no", "n"}:
        return False
    return v


def _parse_timestamp(value: str) -> int:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("empty timestamp")

    # Numeric timestamps: seconds or milliseconds.
    try:
        num = float(raw)
    except Exception:
        num = None

    if num is not None:
        if not math.isfinite(num):
            raise ValueError("non-finite timestamp")
        seconds = num / 1000.0 if num > 1e12 else num
        return int(seconds)

    # ISO timestamps.
    iso = raw
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(iso)
    except Exception as e:
        raise ValueError(str(e)) from e

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp())


def resolve_latest_csv(data_dir: Path, prefix: str) -> Path:
    pattern = f"{prefix}*.csv"
    matches = list(data_dir.glob(pattern))
    files = [p for p in matches if p.is_file()]
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir} matching {pattern}")

    # Choose the single latest file by last-modified time. Ties are broken deterministically by filename.
    return max(files, key=lambda p: (p.stat().st_mtime, p.name))


def load_candles_from_csv_path(csv_path: Path) -> List[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if not csv_path.is_file():
        raise CandleCSVError(f"Expected a file but found: {csv_path}")

    candles: list[dict] = []
    prev_ts: int | None = None

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                raise CandleCSVError(f"CSV is empty: {csv_path}")

            header_norm = [_normalize_header(c) for c in header]
            positions: dict[str, list[int]] = {}
            for idx, name in enumerate(header_norm):
                positions.setdefault(name, []).append(idx)

            ts_candidates: list[tuple[str, int]] = []
            for name in _TIMESTAMP_ALIASES:
                idxs = positions.get(name, [])
                if len(idxs) > 1:
                    raise CandleCSVError(f"Duplicate '{name}' column in {csv_path}")
                if idxs:
                    ts_candidates.append((name, idxs[0]))

            if not ts_candidates:
                raise CandleCSVError(
                    f"Missing required timestamp column in {csv_path}. Expected one of: {list(_TIMESTAMP_ALIASES)}"
                )
            if len(ts_candidates) > 1:
                found = [n for n, _ in ts_candidates]
                raise CandleCSVError(
                    f"Multiple timestamp columns in {csv_path}: {found}. Keep only one of: {list(_TIMESTAMP_ALIASES)}"
                )
            ts_idx = ts_candidates[0][1]

            required_non_ts = ["open", "high", "low", "close", "volume"]
            missing = [c for c in required_non_ts if c not in positions]
            if missing:
                raise CandleCSVError(
                    f"Missing required columns in {csv_path}: {missing}. Required: {['timestamp', *required_non_ts]}"
                )

            duplicates = [c for c in required_non_ts if len(positions.get(c, [])) > 1]
            if duplicates:
                raise CandleCSVError(f"Duplicate required columns in {csv_path}: {duplicates}")

            pattern_positions = positions.get(_PATTERN_ALERT_COLUMN, [])
            if len(pattern_positions) > 1:
                raise CandleCSVError(f"Duplicate '{_PATTERN_ALERT_COLUMN}' column in {csv_path}")
            pattern_idx = pattern_positions[0] if pattern_positions else None

            idx_map = {name: positions[name][0] for name in required_non_ts}
            o_idx = idx_map["open"]
            h_idx = idx_map["high"]
            l_idx = idx_map["low"]
            c_idx = idx_map["close"]
            v_idx = idx_map["volume"]

            for line_no, row in enumerate(reader, start=2):
                if not row or not any(str(cell or "").strip() for cell in row):
                    continue

                max_required_idx = max(ts_idx, o_idx, h_idx, l_idx, c_idx, v_idx)
                if len(row) <= max_required_idx:
                    raise CandleCSVError(
                        f"Missing required column values in {csv_path} at line {line_no}: "
                        f"expected at least {max_required_idx + 1} columns, got {len(row)}"
                    )

                ts_raw = str(row[ts_idx]).strip()
                o_raw = str(row[o_idx]).strip()
                h_raw = str(row[h_idx]).strip()
                l_raw = str(row[l_idx]).strip()
                c_raw = str(row[c_idx]).strip()
                v_raw = str(row[v_idx]).strip()

                try:
                    ts = _parse_timestamp(ts_raw)
                except Exception as e:
                    msg = str(e) if str(e) else "unparseable timestamp"
                    raise CandleCSVError(
                        f"Invalid timestamp in {csv_path} at line {line_no}: '{ts_raw}'. {msg}"
                    )

                if prev_ts is not None:
                    if ts <= prev_ts:
                        raise CandleCSVError(
                            f"Timestamps must be strictly increasing in {csv_path}: {prev_ts} -> {ts} at line {line_no}"
                        )

                try:
                    o = float(o_raw)
                    h = float(h_raw)
                    l = float(l_raw)
                    c = float(c_raw)
                    v = float(v_raw)
                except Exception:
                    raise CandleCSVError(f"Invalid OHLCV number in {csv_path} at line {line_no}")

                if not all(map(math.isfinite, (o, h, l, c, v))):
                    raise CandleCSVError(f"Non-finite OHLCV value in {csv_path} at line {line_no}")

                pattern_alert: bool | str | None = None
                if pattern_idx is not None:
                    raw = str(row[pattern_idx]).strip() if pattern_idx < len(row) else ""
                    pattern_alert = _parse_pattern_alert(raw)

                candles.append(
                    {
                        "time": ts,
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c,
                        "volume": v,
                        "pattern_alert": pattern_alert,
                    }
                )
                prev_ts = ts
    except CandleCSVError:
        raise
    except Exception as e:
        raise CandleCSVError(f"Failed to load CSV {csv_path}: {e}") from e

    if not candles:
        raise CandleCSVError(f"CSV has no data rows: {csv_path}")

    candles.sort(key=lambda x: x["time"])
    return candles


def load_candles(market: str, pair: str) -> List[dict]:
    market_norm = str(market or "").strip().lower()
    if market_norm not in ALLOWED_MARKETS:
        raise CandleCSVError(f"Invalid market '{market}'. Expected one of: {sorted(ALLOWED_MARKETS)}")

    pair_norm = str(pair or "").strip().upper()
    if not pair_norm:
        raise CandleCSVError("Missing pair.")
    if not _PAIR_RE.match(pair_norm):
        raise CandleCSVError("Invalid pair. Use only letters, numbers, and underscore.")

    data_dir = Path(__file__).resolve().parent / "data" / market_norm
    if market_norm == "forex":
        prefix = pair_norm if pair_norm.startswith("FX_") else f"FX_{pair_norm}"
    else:
        prefix = pair_norm if pair_norm.startswith("BINANCE_") else f"BINANCE_{pair_norm}"
    csv_path = resolve_latest_csv(data_dir=data_dir, prefix=prefix)

    return load_candles_from_csv_path(csv_path)
