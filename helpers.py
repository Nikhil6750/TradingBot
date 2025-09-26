# helpers.py
import os
from typing import Optional, Tuple, Iterable
import pandas as pd

# ---------- ENV ----------
def _get_env_raw(name: str, default: Optional[str]) -> Optional[str]:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip()

def get_env_float(name: str, default: float) -> float:
    raw = _get_env_raw(name, None)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)

def get_env_str(name: str, default: str) -> str:
    return _get_env_raw(name, default) or default

# ---------- SESSION ----------
def parse_session(raw: str) -> Optional[Tuple[int, int]]:
    """
    Accepts:
      - "ALL" (case-insensitive) -> None (no filtering)
      - "7-17" -> (7, 17)
      - "  07 - 17 " -> (7, 17)
    Returns None for ALL, else (start_hour, end_hour) inclusive of start, exclusive of end.
    """
    if not raw:
        return None
    r = raw.strip().upper()
    if r == "ALL":
        return None
    # allow quotes users sometimes add in setx
    if r.startswith('"') and r.endswith('"'):
        r = r[1:-1].strip().upper()
    if r == "ALL":
        return None

    if "-" not in r:
        raise ValueError(f"Bad SESSION value: {raw!r}. Use ALL or e.g. 7-17")
    a, b = r.split("-", 1)
    start = int(a.strip())
    end = int(b.strip())
    if not (0 <= start <= 23 and 0 <= end <= 24):
        raise ValueError("SESSION hours must be within 0..24 (e.g. 7-17)")
    return (start, end)

def utc_to_local(utc_series: pd.Series, tz_offset_hours: float) -> pd.Series:
    return utc_series + pd.to_timedelta(tz_offset_hours, unit="h")

def in_session_mask(local_dt: pd.Series, session: Optional[Tuple[int, int]]) -> pd.Series:
    if session is None:
        return pd.Series(True, index=local_dt.index)
    start, end = session
    hours = local_dt.dt.hour
    # inclusive start, exclusive end (like typical trading sessions)
    if start < end:
        return (hours >= start) & (hours < end)
    # overnight window (e.g., 22-3)
    return (hours >= start) | (hours < end)

# ---------- IO ----------
def read_ohlc_csv(path: str) -> pd.DataFrame:
    """
    Expects at least columns: time, open, high, low, close
    Extra columns (like Pattern Alert, Volume) are tolerated.
    """
    df = pd.read_csv(path)
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path} missing columns: {missing}")

    # time -> UTC datetime
    df["dt_utc"] = pd.to_datetime(df["time"], unit="s", utc=True, errors="coerce")
    return df

# ---------- Pretty ----------
def banner(msg: str) -> str:
    return f"=== {msg} ==="

def summarize_trades_rows(rows: Iterable[dict]) -> dict:
    """
    Expect rows with keys: result ('win'|'loss'|'expired'), r (float)
    Returns summary dict.
    """
    wins = sum(1 for r in rows if r.get("result") == "win")
    losses = sum(1 for r in rows if r.get("result") == "loss")
    expired = sum(1 for r in rows if r.get("result") == "expired")
    n = wins + losses + expired
    net_r = sum(float(r.get("r", 0.0)) for r in rows)
    avg_r = (net_r / n) if n else 0.0

    gross_profit = sum(float(r.get("r", 0.0)) for r in rows if float(r.get("r", 0.0)) > 0)
    gross_loss   = -sum(float(r.get("r", 0.0)) for r in rows if float(r.get("r", 0.0)) < 0)
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) else 0.0
    return dict(
        trades=n, wins=wins, losses=losses, expired=expired,
        win_rate=win_rate, avg_r=avg_r, profit_factor=pf, net_r=net_r
    )
