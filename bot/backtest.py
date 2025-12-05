# bot/backtest.py
import math
import numpy as np
import pandas as pd

# ----------------------- internal helpers -----------------------
def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize columns and parse timestamp if present."""
    if df is None or df.empty:
        return pd.DataFrame()

    # Lowercase aliases for OHLC
    cols = {c.lower(): c for c in df.columns}
    need = ["open", "high", "low", "close"]
    for n in need:
        if n not in cols:
            raise ValueError(f"missing OHLC column: {n}")

    # Try to find a time-like column and standardize to 'timestamp'
    tcol = None
    for cand in ("timestamp", "time", "date", "Datetime", "Date"):
        if cand in df.columns:
            tcol = cand
            break

    out = df.rename(columns={
        cols["open"]: "open",
        cols["high"]: "high",
        cols["low"]:  "low",
        cols["close"]: "close",
    }).copy()

    if tcol:
        out = out.rename(columns={tcol: "timestamp"})
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")

    # Ensure numeric
    for c in ["open","high","low","close"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    return out.dropna(subset=["open","high","low","close"]).reset_index(drop=True)


def _ensure_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add ATR_14 if missing. (Wilder ATR via EWM)"""
    if "ATR_14" not in df.columns:
        high = df["high"].astype(float)
        low  = df["low"].astype(float)
        close = df["close"].astype(float)
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low).abs(),
            (high - prev_close).abs(),
            (low  - prev_close).abs()
        ], axis=1).max(axis=1)
        df["ATR_14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    return df


def _fallback_score_and_direction(df: pd.DataFrame) -> pd.DataFrame:
    """If your pipeline didn't precompute score/direction, create a simple one."""
    if "score" in df.columns and "direction" in df.columns:
        return df

    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    mom_up = (df["close"] > ema20).astype(int)
    dist = (df["close"] - ema20)
    scale = df["close"].rolling(20).std().replace(0, np.nan)
    sc = 50 + 50 * (dist / scale).clip(-1, 1)
    df["score"] = sc.fillna(50)
    df["direction"] = np.where(
        (mom_up == 1) & (ema20 > ema50), "BUY",
        np.where((mom_up == 0) & (ema20 < ema50), "SELL", "HOLD")
    )
    return df


# ----------------------- public API ------------------------------
def backtest(
    df: pd.DataFrame,
    threshold: float = 65,
    atr_mult: float = 1.8,
    rr: float = 1.5,
    max_bars: int = 100000,
    session_filter: tuple[int, int] | None = None,  # e.g., (9, 16) local hours
    tz_offset_hours: float = 0.0,                   # shift timestamps for session check
) -> pd.DataFrame:
    """
    Deterministic bar-by-bar simulator (single position).
    - Enter on next bar's open when score >= threshold.
    - SL/TP from ATR_14 * atr_mult and rr.
    - Intrabar check: SL first (conservative), then TP.
    Returns trades DataFrame with:
      entry_time, exit_time, entry_price, exit_price, direction, sl, tp, outcome
    """

    df = _prepare(df)
    if df.empty or len(df) < 50:
        return pd.DataFrame(columns=[
            "entry_time","exit_time","entry_price","exit_price",
            "direction","sl","tp","outcome"
        ])

    df = _ensure_indicators(df)
    df = _fallback_score_and_direction(df)

    trades = []
    in_pos = False
    entry_i = entry_px = sl = tp = direction = None

    # Warmup until ATR valid
    first_idx = df["ATR_14"].first_valid_index()
    start = max(14, int(first_idx) if first_idx is not None else 14)
    end = min(len(df) - 2, start + max_bars)  # leave space for next-bar entry

    for i in range(start, end):
        # If in a trade, check exits on current bar
        if in_pos:
            hi, lo = float(df.at[i, "high"]), float(df.at[i, "low"])
            if direction == "BUY":
                if lo <= sl:
                    exit_px, outcome = sl, "LOSS"
                elif hi >= tp:
                    exit_px, outcome = tp, "WIN"
                else:
                    continue
            else:  # SELL
                if hi >= sl:
                    exit_px, outcome = sl, "LOSS"
                elif lo <= tp:
                    exit_px, outcome = tp, "WIN"
                else:
                    continue

            trades.append({
                "entry_time": df.at[entry_i, "timestamp"] if "timestamp" in df.columns else entry_i,
                "exit_time":  df.at[i, "timestamp"] if "timestamp" in df.columns else i,
                "entry_price": float(entry_px),
                "exit_price": float(exit_px),
                "direction": direction,
                "sl": float(sl),
                "tp": float(tp),
                "outcome": outcome
            })
            in_pos = False
            entry_i = entry_px = sl = tp = direction = None
            continue

        # Evaluate signal on bar i; we will enter at next bar's open (i+1).
        sc = float(df.at[i, "score"])
        dirn = str(df.at[i, "direction"]).upper()
        if sc >= float(threshold) and dirn in ("BUY", "SELL"):
            if i + 1 >= len(df):
                break

            # Session filter applies to the **entry bar** hour (i+1) after TZ shift
            if session_filter and "timestamp" in df.columns:
                ts_next = df.at[i+1, "timestamp"]
                if pd.notna(ts_next):
                    adj = ts_next + pd.to_timedelta(tz_offset_hours, unit="h")
                    h0, h1 = session_filter
                    hr = int(adj.hour)
                    if not (h0 <= hr <= h1):
                        # Skip this signal because entry would occur outside session
                        continue

            atr = float(df.at[i, "ATR_14"])
            if not math.isfinite(atr) or atr <= 0:
                continue

            entry_px = float(df.at[i+1, "open"])  # next bar open
            if dirn == "BUY":
                sl = entry_px - atr * float(atr_mult)
                tp = entry_px + atr * float(atr_mult) * float(rr)
            else:
                sl = entry_px + atr * float(atr_mult)
                tp = entry_px - atr * float(atr_mult) * float(rr)

            in_pos = True
            entry_i = i + 1
            direction = dirn

    # If last trade is still open, expire at last close
    if in_pos:
        last_i = len(df) - 1
        trades.append({
            "entry_time": df.at[entry_i, "timestamp"] if "timestamp" in df.columns else entry_i,
            "exit_time":  df.at[last_i, "timestamp"] if "timestamp" in df.columns else last_i,
            "entry_price": float(entry_px),
            "exit_price": float(df.at[last_i, "close"]),
            "direction": direction,
            "sl": float(sl),
            "tp": float(tp),
            "outcome": "EXPIRED"
        })

    return pd.DataFrame(trades, columns=[
        "entry_time","exit_time","entry_price","exit_price",
        "direction","sl","tp","outcome"
    ])


def summarize_results(trades_df: pd.DataFrame) -> None:
    """Print compact metrics from a trades DataFrame."""
    if trades_df is None or trades_df.empty:
        print("\n=== Backtest Summary ===\nNo trades.")
        return

    total = len(trades_df)
    wins = int((trades_df["outcome"] == "WIN").sum())
    losses = int((trades_df["outcome"] == "LOSS").sum())
    expired = int((trades_df["outcome"] == "EXPIRED").sum())

    def r_mult(row):
        entry, sl, exitp = float(row["entry_price"]), float(row["sl"]), float(row["exit_price"])
        side = str(row["direction"]).upper()
        risk = abs(entry - sl)
        if risk <= 0 or not math.isfinite(risk):
            return np.nan
        gain = (exitp - entry) if side == "BUY" else (entry - exitp)
        return gain / risk

    r = trades_df.apply(r_mult, axis=1)
    r = r[np.isfinite(r)]

    if len(r):
        avg_r = float(r.mean())
        gross_win = float(r[r > 0].sum())
        gross_loss = float(-r[r < 0].sum())
        pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
        net_r = gross_win - gross_loss
    else:
        avg_r = pf = net_r = 0.0

    win_rate = (wins / total * 100.0) if total else 0.0

    print("\n=== Backtest Summary ===")
    print(f"Trades       : {total}")
    print(f"Wins/Losses  : {wins}/{losses}  Expired: {expired}")
    print(f"Win Rate     : {win_rate:.2f}%")
    print(f"Avg R        : {avg_r:.3f}")
    print(f"ProfitFactor : {pf:.3f}")
    print(f"Net R        : {net_r:.3f}")
