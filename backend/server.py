from __future__ import annotations
import io, os, glob, base64
from typing import Optional, List, Dict
from dataclasses import dataclass

# near your other imports
from agent.tools import router as tools_router
from agent.agent import router as agent_router

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from urllib.parse import quote, unquote
from datetime import datetime
from dateutil import tz
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# App & CORS
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

app = FastAPI(title="Trading Bot API", version="3.1.0")
# Mount agent + tool routers
app.include_router(tools_router)
app.include_router(agent_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*","http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
# In-memory store for uploaded CSVs (MVP CSV window chart)
CSV_STORE: Dict[str, pd.DataFrame] = {}
CSV_TZ: Dict[str, str] = {}
CSV_MAX_BYTES = int(float(os.getenv("CSV_MAX_BYTES", str(25 * 1024 * 1024))))  # 25MB default

def _canon_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize required columns to: timestamp, open, high, low, close, volume, symbol (optional)."""
    lower = {c.lower().strip(): c for c in df.columns}
    # Accept common alias 'time' as well
    ts_col = lower.get("timestamp") or lower.get("time")
    if not ts_col:
        raise ValueError("CSV must have 'timestamp' column")
    need_ohlcv = ["open", "high", "low", "close", "volume"]
    for k in need_ohlcv:
        if k not in lower:
            raise ValueError("CSV must have 'open, high, low, close, volume' columns")
    ren = {ts_col: "timestamp", **{lower[k]: k for k in need_ohlcv}}
    if "symbol" in lower:
        ren[lower["symbol"]] = "symbol"
    df = df.rename(columns=ren)
    return df

def _parse_ts_to_utc(s: pd.Series, upload_tz: str) -> pd.Series:
    """Parse timestamp series into UTC tz-aware datetimes.
    - If numeric: detect probable unit (s/ms/ns) by magnitude and parse as UTC epoch.
    - If string/ts-like:
        • If tz-aware: convert to UTC.
        • If naive: localize with upload_tz, then convert to UTC.
    """
    # Numeric fast-path (handles epoch seconds/millis/nanos)
    if pd.api.types.is_numeric_dtype(s):
        v = pd.to_numeric(s, errors="coerce").astype("float64")
        # Heuristic like _coerce_time_any
        finite = v[np.isfinite(v)]
        mx = float(finite.max()) if finite.size else 0.0
        unit = "s" if mx < 1e11 else ("ms" if mx < 1e14 else "ns")
        return pd.to_datetime(v, unit=unit, utc=True, errors="coerce")

    # String/ts-like parsing
    dt = pd.to_datetime(s, utc=False, errors="coerce")
    if getattr(dt.dt, "tz", None) is not None:
        return dt.dt.tz_convert("UTC")
    loc = tz.gettz(upload_tz or "UTC")
    return dt.dt.tz_localize(loc, nonexistent="shift_forward", ambiguous="NaT").dt.tz_convert("UTC")

def _to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for k in ["open", "high", "low", "close", "volume"]:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    return df

def _parse_hhmm(s: str) -> tuple[int, int]:
    try:
        parts = str(s).strip().split(":")
        if len(parts) != 2:
            raise ValueError
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except Exception:
        raise HTTPException(400, "Invalid time format. Use HH:MM")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload-csv")
async def upload_csv(
    symbol: Optional[str] = Query(default=None, description="Symbol if CSV lacks symbol column"),
    tz_name: str = Query(default="UTC", alias="tz"),
    file: UploadFile = File(...),
):
    content = await file.read()
    if len(content) > CSV_MAX_BYTES:
        raise HTTPException(400, "File too large. Max 25 MB")
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Could not read CSV: {e}")

    try:
        df = _canon_cols(df)
    except ValueError as e:
        raise HTTPException(400, str(e))

    df = _to_numeric(df)
    try:
        ts_utc = _parse_ts_to_utc(df["timestamp"], tz_name)
    except Exception:
        raise HTTPException(400, "Invalid 'timestamp' values; ensure ISO-like strings")

    df["time_utc"] = ts_utc
    keep = df[["time_utc", "open", "high", "low", "close", "volume"]].notnull().all(axis=1)
    df = df[keep].copy()
    if df.empty:
        raise HTTPException(400, "CSV has no valid rows after parsing")

    loaded: List[str] = []
    if "symbol" in df.columns and df["symbol"].notnull().any():
        for sym, g in df.groupby(df["symbol"].astype(str)):
            symu = str(sym).upper().strip()
            if not symu:
                continue
            gg = g[["time_utc", "open", "high", "low", "close", "volume"]].sort_values("time_utc").reset_index(drop=True)
            CSV_STORE[symu] = gg
            CSV_TZ[symu] = tz_name
            loaded.append(symu)
    else:
        if not symbol:
            raise HTTPException(400, "CSV missing 'symbol' column; pass ?symbol=SYMBOL")
        symu = symbol.upper().strip()
        gg = df[["time_utc", "open", "high", "low", "close", "volume"]].sort_values("time_utc").reset_index(drop=True)
        CSV_STORE[symu] = gg
        CSV_TZ[symu] = tz_name
        loaded.append(symu)

    return {"status": "ok", "symbols_loaded": sorted(set(loaded))}

@app.get("/chart-data")
def chart_data(
    symbol: str = Query(..., description="Symbol to query"),
    start_time: str = Query(..., description="HH:MM inclusive"),
    end_time: str = Query(..., description="HH:MM inclusive"),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD in symbol's tz"),
    limit: int = Query(default=5000, ge=1, le=200000),
):
    symu = (symbol or "").upper().strip()
    if symu not in CSV_STORE:
        raise HTTPException(404, f"No data for symbol '{symu}'. Upload first.")
    h0, m0 = _parse_hhmm(start_time)
    h1, m1 = _parse_hhmm(end_time)
    if (h0, m0) > (h1, m1):
        raise HTTPException(400, "start_time must be <= end_time")

    df = CSV_STORE[symu]
    tz_name = CSV_TZ.get(symu, "UTC")
    zone = tz.gettz(tz_name)
    tloc = df["time_utc"].dt.tz_convert(zone)

    mask = (tloc.dt.hour > h0) | ((tloc.dt.hour == h0) & (tloc.dt.minute >= m0))
    mask &= (tloc.dt.hour < h1) | ((tloc.dt.hour == h1) & (tloc.dt.minute <= m1))

    if date:
        try:
            y, m, d = map(int, date.split("-"))
        except Exception:
            raise HTTPException(400, "Invalid date. Use YYYY-MM-DD")
        mask &= (tloc.dt.year == y) & (tloc.dt.month == m) & (tloc.dt.day == d)

    sel = df.loc[mask].copy()
    if sel.empty:
        return {"symbol": symu, "count": 0, "rows": []}

    sel = sel.sort_values("time_utc").head(int(limit))
    rows = [
        {
            "time": r.time_utc.isoformat(),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": float(r.volume),
        }
        for r in sel.itertuples(index=False)
    ]
    return {"symbol": symu, "count": len(rows), "rows": rows}


@app.get("/csv/store-debug")
def csv_store_debug(symbol: str):
    symu = (symbol or "").upper().strip()
    if symu not in CSV_STORE:
        raise HTTPException(404, f"No data for symbol '{symu}'. Upload first.")
    df = CSV_STORE[symu]
    if df.empty:
        return {"symbol": symu, "rows_total": 0}
    to_s = lambda x: pd.to_datetime(x).tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S %Z")
    return {
        "symbol": symu,
        "rows_total": int(df.shape[0]),
        "start_utc": to_s(df.iloc[0]["time_utc"]),
        "end_utc": to_s(df.iloc[-1]["time_utc"]),
        "first_3": [r.time_utc.isoformat() for r in df.head(3).itertuples(index=False)],
        "last_3": [r.time_utc.isoformat() for r in df.tail(3).itertuples(index=False)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chart window data for backtest alerts (JSON, not PNG)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/chart/window")
def chart_window(symbol: str, center_tidx: int, bars: int = 60, tz: str = "UTC"):
    path = _find_csv(symbol)
    if not path:
        raise HTTPException(404, f"No CSV found for {symbol}")
    try:
        df = _ensure_ohlc(pd.read_csv(path))
    except Exception as e:
        raise HTTPException(500, str(e))

    bars = max(10, int(bars))
    center = int(center_tidx)
    center = int(np.clip(center, 0, len(df)-1))
    half = bars // 2
    lo = max(0, center - half)
    hi = min(len(df), center + half)
    if hi <= lo:
        return {"symbol": symbol.upper(), "rows": []}

    win = df.iloc[lo:hi].copy().reset_index(drop=True)
    # Convert time to ISO with offset according to tz param (display only)
    try:
        tloc = pd.to_datetime(win["time"]).dt.tz_convert(tz)
    except Exception:
        tloc = pd.to_datetime(win["time"])  # naive

    out = []
    for r, tdisp in zip(win.itertuples(index=False), tloc):
        out.append({
            "time": pd.to_datetime(r.time).tz_convert("UTC").isoformat() if hasattr(r.time, 'tz_convert') else pd.to_datetime(r.time).isoformat(),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "time_disp": str(tdisp),
        })

    return {
        "symbol": symbol.upper(),
        "center_tidx": int(center_tidx),
        "rows": out,
    }
def _parse_hour_allow(hour_allow: str) -> tuple[int, int]:
    try:
        a, b = map(int, str(hour_allow).split("-"))
        a = min(max(a, 0), 23)
        b = min(max(b, 1), 24)  # end exclusive
        if a == b: return (0, 24)
        return (a, b)
    except Exception:
        return (0, 24)

def _find_csv(symbol: str) -> Optional[str]:
    sym = symbol.upper().strip()
    for pat in [
        os.path.join(DATA_DIR, f"{sym}.csv"),
        os.path.join(DATA_DIR, f"FX_{sym}*.csv"),
        os.path.join(DATA_DIR, f"*{sym}*.csv"),
    ]:
        m = sorted(glob.glob(pat))
        if m:
            m.sort(key=lambda p: os.path.getsize(p), reverse=True)
            return m[0]
    return None

def _coerce_time_any(s: pd.Series) -> pd.Series:
    if np.issubdtype(s.dtype, np.number):
        v = s.astype("float64")
        mx = np.nanmax(v)
        unit = "s" if mx < 1e11 else ("ms" if mx < 1e14 else "ns")
        return pd.to_datetime(v, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(s, utc=True, errors="coerce")

def _ensure_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize columns, numeric coercion, sort by time, attach time-sorted index (tidx)."""
    lower = {c.lower(): c for c in df.columns}
    for k in ["time","open","high","low","close"]:
        if k not in lower:
            raise ValueError(f"Missing '{k}' in CSV")
    df = df.rename(columns={
        lower["time"]:"time", lower["open"]:"open",
        lower["high"]:"high", lower["low"]:"low", lower["close"]:"close"
    })
    for k in ["open","high","low","close"]:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    df["time"] = _coerce_time_any(df["time"])
    df = df.dropna(subset=["time","open","high","low","close"])\
           .sort_values("time").reset_index(drop=True)
    df["tidx"] = np.arange(len(df), dtype=int)  # monotonic, time-sorted anchor
    return df

def _png_error_bytes(msg: str) -> bytes:
    fig, ax = plt.subplots(figsize=(6, 1.5))
    ax.axis("off")
    ax.text(0.02, 0.5, msg, fontsize=10, va="center", ha="left")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────────────────
def _body(o, c): return abs(float(c)-float(o))
def _upper(o, h, c): return float(h)-max(float(o),float(c))
def _lower(o, l, c): return min(float(o),float(c))-float(l)

def is_bullish_engulfing(o1,h1,l1,c1, o2,h2,l2,c2):
    return (c1<o1) and (c2>o2) and (o2<=c1) and (c2>=o1)

def is_bearish_engulfing(o1,h1,l1,c1, o2,h2,l2,c2):
    return (c1>o1) and (c2<o2) and (o2>=c1) and (c2<=o1)

def is_hammer(o,h,l,c):
    b=_body(o,c); return (_lower(o,l,c)>=2*b) and (_upper(o,h,c)<=0.5*b)

def is_shooting_star(o,h,l,c):
    b=_body(o,c); return (_upper(o,h,c)>=2*b) and (_lower(o,l,c)<=0.5*b)

# ─────────────────────────────────────────────────────────────────────────────
# Outcome evaluator (position-based using tidx)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class OutcomeParams:
    tp_pips: float = 10.0
    sl_pips: float = 10.0
    max_hold_bars: int = 12
    fill: str = "next_open"          # or "close"
    hit_order: str = "conservative"  # reserved

def _pip_point_for_symbol(sym: str, df: pd.DataFrame) -> float:
    try:
        s = (df["close"].astype(float).round(10)).diff().abs()
        step = s.replace(0, s[s>0].min()).head(200).min()
        if pd.isna(step) or step==0:
            return 0.001 if sym.endswith("JPY") else 0.0001
        for p in [0.00001,0.0001,0.001,0.01]:
            if step >= p: return p
        return step
    except Exception:
        return 0.001 if sym.endswith("JPY") else 0.0001

def evaluate_trade_pos(df: pd.DataFrame, entry_pos: int, side: str, entry_price: float, params: OutcomeParams):
    sym = df.attrs.get("symbol","UNKNOWN")
    point = _pip_point_for_symbol(sym, df)
    tp, sl = params.tp_pips*point, params.sl_pips*point
    target, stop = (entry_price+tp, entry_price-sl) if side=="LONG" else (entry_price-tp, entry_price+sl)

    last_pos = min(len(df)-1, entry_pos + params.max_hold_bars)
    outcome, exit_price = "timeout", float(df.iloc[last_pos]["close"])
    exit_time = pd.to_datetime(df.iloc[last_pos]["time"]).to_pydatetime()

    for i in range(entry_pos+1, last_pos+1):
        bar = df.iloc[i]; lo, hi = float(bar["low"]), float(bar["high"])
        if side=="LONG":
            if lo<=stop: outcome, exit_price, exit_time = "loss", stop, pd.to_datetime(bar["time"]).to_pydatetime(); break
            if hi>=target: outcome, exit_price, exit_time = "win", target, pd.to_datetime(bar["time"]).to_pydatetime(); break
        else:
            if hi>=stop: outcome, exit_price, exit_time = "loss", stop, pd.to_datetime(bar["time"]).to_pydatetime(); break
            if lo<=target: outcome, exit_price, exit_time = "win", target, pd.to_datetime(bar["time"]).to_pydatetime(); break

    risk = max(sl, 1e-12)
    r_mult = round(((exit_price-entry_price) if side=="LONG" else (entry_price-exit_price))/risk, 2)
    return {"outcome": outcome, "exit_time": exit_time, "exit_price": round(exit_price,6), "r_multiple": r_mult}

# ─────────────────────────────────────────────────────────────────────────────
# Inline chart renderer (returns PNG bytes)
# ─────────────────────────────────────────────────────────────────────────────
def render_candles_png(df: pd.DataFrame, center_pos: int, bars: int, tz: str, symbol: str, reason: Optional[str]) -> bytes:
    try:
        bars = max(10, int(bars))
        center_pos = int(np.clip(int(center_pos), 0, len(df)-1))
        half = bars // 2
        lo = max(0, center_pos-half)
        hi = min(len(df), center_pos+half)
        if hi <= lo:
            return _png_error_bytes("Empty window")

        win = df.iloc[lo:hi].copy().reset_index(drop=True)

        # local time ticks
        try:
            win["time_local"] = pd.to_datetime(win["time"]).dt.tz_convert(tz)
        except Exception:
            win["time_local"] = pd.to_datetime(win["time"])

        anchor_ts = pd.to_datetime(df.iloc[center_pos]["time"]).tz_convert("UTC")

        buf = io.BytesIO()
        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(len(win))

        # draw candles
        for i, r in enumerate(win.itertuples(index=False)):
            o, h, l, c = float(r.open), float(r.high), float(r.low), float(r.close)
            color = "#22c55e" if c >= o else "#ef4444"
            ax.vlines(i, l, h, color=color, linewidth=1.2)
            body_y = min(o, c)
            body_h = max(1e-10, abs(c-o))
            ax.add_patch(plt.Rectangle((i-0.3, body_y), 0.6, body_h, color=color, alpha=0.9, linewidth=0))

        # highlight anchor candle
        ax.axvline(int(np.clip(center_pos-lo, 0, len(win)-1)), color="#3b82f6", linewidth=1.0, alpha=0.6)

        # axes cosmetics
        ax.set_xlim(-1, len(win))
        step = max(1, len(x)//6)
        ax.set_xticks(x[::step])
        ax.set_xticklabels([t.strftime("%H:%M") for t in win["time_local"].iloc[::step]], rotation=30, ha="right", fontsize=8)

        ymin, ymax = float(win["low"].min()), float(win["high"].max())
        pad = (ymax - ymin) * 0.05 if ymax > ymin else 0.0001
        ax.set_ylim(ymin - pad, ymax + pad)

        # Title without pattern text
        ttl = f"{symbol.upper()} {anchor_ts.strftime('%Y-%m-%d %H:%M UTC')}"
        ax.set_title(ttl, fontsize=10, weight="bold")

        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception as e:
        return _png_error_bytes(f"Plot error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# API models
# ─────────────────────────────────────────────────────────────────────────────
class BacktestRunReq(BaseModel):
    symbol: str
    hour_allow: str = "0-24"     # end exclusive
    date: Optional[str] = None   # YYYY-MM-DD (UTC)
    tp_pips: float = 10.0
    sl_pips: float = 10.0
    max_hold_bars: int = 12
    max_alerts: int = 10
    cooldown_bars: int = 3
    fill: str = "next_open"
    hit_order: str = "conservative"
    tz: str = "UTC"
    bars_plot: int = 40

# ─────────────────────────────────────────────────────────────────────────────
# Minimal tool targets for the agent (safe defaults)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/prices/get")
def prices_get(payload: dict):
    """
    Stub for prices. Replace with your real data source later.
    Expected keys: symbol, timeframe, limit
    """
    return {
        "symbol": (payload or {}).get("symbol"),
        "timeframe": (payload or {}).get("timeframe", "1h"),
        "bars": [],   # TODO: fill from your CSV/feeder
        "limit": (payload or {}).get("limit", 200),
    }

@app.post("/orders/paper/place")
def paper_place(payload: dict):
    """
    Paper-order endpoint only. Live trading is intentionally not supported here.
    The agent’s policy defaults to PAPER; keep it that way.
    """
    order = {
        "symbol": (payload or {}).get("symbol"),
        "side": (payload or {}).get("side"),
        "qty": (payload or {}).get("qty"),
        "order_type": (payload or {}).get("order_type", "market"),
        "limit_price": (payload or {}).get("limit_price"),
        "mode": "paper",
        "status": "accepted",
    }
    return order


# ─────────────────────────────────────────────────────────────────────────────
# Routes — Backtest
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/backtest/run")
def backtest_run(req: BacktestRunReq):
    sym = req.symbol.upper().strip()
    path = _find_csv(sym)
    if not path:
        return JSONResponse({"ok": False, "error": f"No CSV found for {sym}"}, status_code=404)

    try:
        df_full = _ensure_ohlc(pd.read_csv(path))
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    df_full.attrs["symbol"] = sym

    # filter by date/hour but keep tidx from full df
    df_filt = df_full
    if req.date:
        d = pd.to_datetime(req.date).date()
        df_filt = df_filt[df_filt["time"].dt.date == d]
        if df_filt.empty:
            return JSONResponse({"ok": False, "error": f"No data for {req.date}"}, status_code=404)
    h0, h1 = _parse_hour_allow(req.hour_allow)
    df_filt = df_filt[(df_filt["time"].dt.hour >= h0) & (df_filt["time"].dt.hour < h1)]
    if df_filt.empty:
    # FIX: return empty successful response instead of 404
        return {
        "ok": True,
        "symbol": sym,
        "summary": {"trades": 0, "wins": 0, "losses": 0, "timeouts": 0, "win_rate": 0},
        "run": {"date_utc": req.date, "hour_allow": req.hour_allow},
        "alerts": []
    }


    df_filt = df_filt.reset_index(drop=True)
    params = OutcomeParams(req.tp_pips, req.sl_pips, req.max_hold_bars, req.fill, req.hit_order)

    alerts: List[dict] = []
    last_signal_i = -10**9

    for i in range(1, len(df_filt)):
        p, c = df_filt.iloc[i-1], df_filt.iloc[i]
        reason, side = None, None

        if is_bullish_engulfing(p["open"],p["high"],p["low"],p["close"], c["open"],c["high"],c["low"],c["close"]):
            reason, side = "bullish_engulfing", "LONG"
        elif is_bearish_engulfing(p["open"],p["high"],p["low"],p["close"], c["open"],c["high"],c["low"],c["close"]):
            reason, side = "bearish_engulfing", "SHORT"
        elif is_hammer(c["open"],c["high"],c["low"],c["close"]):
            reason, side = "hammer", "LONG"
        elif is_shooting_star(c["open"],c["high"],c["low"],c["close"]):
            reason, side = "shooting_star", "SHORT"
        else:
            continue

        if i - last_signal_i < max(0, int(req.cooldown_bars)):
            continue
        last_signal_i = i

        t_utc = pd.to_datetime(c["time"], utc=True)
        tidx = int(c["tidx"])
        entry_pos = min(tidx + 1, len(df_full)-1)
        entry_px = float(df_full.iloc[entry_pos]["open"]) if params.fill=="next_open" else float(c["close"])
        outc = evaluate_trade_pos(df_full, entry_pos, side, entry_px, params)

        # inline chart (base64)
        png_bytes = render_candles_png(df_full, center_pos=tidx, bars=req.bars_plot, tz=req.tz, symbol=sym, reason=reason)
        b64 = base64.b64encode(png_bytes).decode("ascii")

        qt = quote(t_utc.isoformat())
        alerts.append({
            "time": t_utc.isoformat(),
            "tidx": tidx,
            "side": side,
            "reason": reason,
            "entry_price": entry_px,
            "exit_price": outc["exit_price"],
            "exit_time": outc["exit_time"].isoformat(),
            "outcome": outc["outcome"],
            "r_multiple": outc["r_multiple"],
            "take": (outc["outcome"] == "win"),
            "plot_data_url": f"data:image/png;base64,{b64}",
            "plot_url": f"/backtest/plot?symbol={sym}&tidx={tidx}&time={qt}&tz={req.tz}&bars={req.bars_plot}&reason={reason}"
        })
        if len(alerts) >= req.max_alerts:
            break

    trades = len(alerts)
    wins = sum(a["outcome"] == "win" for a in alerts)
    losses = sum(a["outcome"] == "loss" for a in alerts)
    timeouts = sum(a["outcome"] == "timeout" for a in alerts)
    win_rate = round(100 * wins / max(trades,1), 2)

    return {
        "ok": True,
        "symbol": sym,
        "summary": {"trades": trades, "wins": wins, "losses": losses, "timeouts": timeouts, "win_rate": win_rate},
        "run": {"date_utc": req.date, "hour_allow": req.hour_allow},
        "alerts": alerts,
    }

# Classic plotting endpoint (debug/manual)
@app.get("/backtest/plot")
def backtest_plot(
    symbol: str = Query(...),
    tidx: Optional[int] = Query(None),
    time: Optional[str] = Query(None),
    tz: str = Query("UTC"),
    bars: int = Query(40),
    reason: Optional[str] = Query(None),
):
    path = _find_csv(symbol)
    if not path:
        return StreamingResponse(io.BytesIO(_png_error_bytes(f"No CSV for {symbol}")), media_type="image/png")
    try:
        df = _ensure_ohlc(pd.read_csv(path))
    except Exception as e:
        return StreamingResponse(io.BytesIO(_png_error_bytes(str(e))), media_type="image/png")

    if tidx is not None:
        center_pos = int(np.clip(int(tidx), 0, len(df)-1))
    else:
        if not time:
            return StreamingResponse(io.BytesIO(_png_error_bytes("Missing tidx/time")), media_type="image/png")
        t_utc = pd.to_datetime(unquote(time).strip(), utc=True, errors="coerce")
        if pd.isna(t_utc):
            return StreamingResponse(io.BytesIO(_png_error_bytes("Bad 'time'")), media_type="image/png")
        center_pos = int((df["time"] - t_utc).abs().argmin())

    png = render_candles_png(df, center_pos, bars, tz, symbol, reason)
    return StreamingResponse(io.BytesIO(png), media_type="image/png", headers={"Cache-Control":"no-store"})

# Verify endpoint (batch)
class VerifyReq(BaseModel):
    symbol: str
    items: List[Dict[str, str]]  # [{"time": "<iso>", "reason": "bearish_engulfing"}, ...]

@app.post("/backtest/verify")
def backtest_verify(req: VerifyReq):
    path = _find_csv(req.symbol)
    if not path:
        return JSONResponse({"ok": False, "error": f"No CSV found for {req.symbol}"}, status_code=404)
    try:
        df = _ensure_ohlc(pd.read_csv(path))
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    out = []
    for it in req.items:
        t_raw = (it.get("time") or "").strip()
        expected = (it.get("reason") or "").strip()
        if not t_raw:
            out.append({"time": t_raw, "expected": expected, "ok": False, "detected": None, "match": "none"})
            continue

        t_utc = pd.to_datetime(t_raw, utc=True, errors="coerce")
        if pd.isna(t_utc):
            out.append({"time": t_raw, "expected": expected, "ok": False, "detected": None, "match": "bad_time"})
            continue

        idxs = df.index[df["time"] == t_utc]
        if len(idxs) == 0:
            i = int((df["time"] - t_utc).abs().argmin())
            match = "nearest"
        else:
            i = int(idxs[0])
            match = "exact"

        cur = df.iloc[i]
        prev = df.iloc[i-1] if i > 0 else None

        det = None
        if prev is not None:
            if is_bullish_engulfing(prev["open"],prev["high"],prev["low"],prev["close"],
                                     cur["open"],cur["high"],cur["low"],cur["close"]):
                det = "bullish_engulfing"
            elif is_bearish_engulfing(prev["open"],prev["high"],prev["low"],prev["close"],
                                       cur["open"],cur["high"],cur["low"],cur["close"]):
                det = "bearish_engulfing"

        if det is None:
            if is_hammer(cur["open"],cur["high"],cur["low"],cur["close"]):
                det = "hammer"
            elif is_shooting_star(cur["open"],cur["high"],cur["low"],cur["close"]):
                det = "shooting_star"

        ok = (expected == det)
        out.append({
            "time": t_utc.isoformat(),
            "expected": expected,
            "detected": det,
            "ok": bool(ok),
            "match": match,
            "row_index": int(i),
        })

    return {"ok": True, "results": out}

# Utility endpoints
@app.get("/symbols")
def list_symbols():
    if not os.path.isdir(DATA_DIR):
        return {"symbols": []}
    syms: List[str] = []
    for f in sorted(os.listdir(DATA_DIR)):
        if f.lower().endswith(".csv"):
            s = f.replace("FX_", "").split(",")[0].strip()
            if s and s not in syms: syms.append(s)
    return {"symbols": syms}

@app.get("/csv/debug")
def csv_debug(symbol: str, n: int = 5):
    path = _find_csv(symbol)
    if not path:
        return {"ok": False, "error": f"No CSV found for {symbol}"}
    try:
        df = _ensure_ohlc(pd.read_csv(path))
    except Exception as e:
        return {"ok": False, "error": str(e)}
    to_s = lambda x: pd.to_datetime(x).tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "rows_total": int(df.shape[0]),
        "start_utc": to_s(df.iloc[0]["time"]),
        "end_utc": to_s(df.iloc[-1]["time"]),
        "first_5_rows": df.head(n).to_dict(orient="records"),
        "last_5_rows": df.tail(n).to_dict(orient="records"),
    }

# ─────────────────────────────────────────────────────────────────────────────
# 📈 NEWS / ECONOMIC CALENDAR (Investing.com via jobs/fetch_investing_calendar.py)
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: ensure you have jobs/fetch_investing_calendar.py (requests+bs4 version) in place.

# ── SAFE CALENDAR ENDPOINTS (replace your existing ones) ─────────────────────
from fastapi import Query
import traceback, pandas as pd, os
from datetime import datetime
from typing import Optional, List

# import your scraper (safe mode — jobs folder optional)
try:
    from jobs.fetch_investing_calendar import (
        get_investing_calendar,
        get_dividend_calendar,
        get_earnings_calendar,
        fetch_investing_calendar
    )
except Exception:
    print("⚠ jobs.fetch_investing_calendar missing — disabling calendar endpoints.")
    get_investing_calendar = None
    get_dividend_calendar = None
    get_earnings_calendar = None
    fetch_investing_calendar = lambda *a, **k: pd.DataFrame()



def _csv_list(s: Optional[str]) -> List[str]:
    if not s: return []
    return [x.strip() for x in s.split(",") if x.strip()]

def _load_csv_if_exists(date_str: str) -> Optional[pd.DataFrame]:
    """Read data/calendar/YYYY-MM-DD.csv if present; else return None."""
    path = os.path.join(NEWS_OUTPUT_DIR, f"{date_str}.csv")
    if os.path.isfile(path):
        try:
            df = pd.read_csv(path)
            # keep schema predictable
            cols = ["date","time_local","time_utc","currency","impact","event","actual","forecast","previous","source"]
            for c in cols:
                if c not in df.columns: df[c] = None
            return df[cols]
        except Exception:
            traceback.print_exc()
    return None

def _safe_fetch(date_str: str, tz: str) -> pd.DataFrame:
    """
    1) Try CSV cache first (if you ran the job manually).
    2) Else try live scrape.
    Always returns a DataFrame (possibly empty), never raises.
    """
    try:
        df = _load_csv_if_exists(date_str)
        if df is not None:
            return df

        df = fetch_investing_calendar(date_str, local_tz=tz)
        return df if df is not None else pd.DataFrame()
    except Exception:
        traceback.print_exc()
        # Return empty DF so UI stays happy
        return pd.DataFrame(columns=["date","time_local","time_utc","currency","impact","event","actual","forecast","previous","source"])

@app.get("/calendar/today")
def calendar_today(
    currencies: Optional[str] = Query(default=os.getenv("NEWS_CURRENCIES", NEWS_CURRENCIES)),
    min_impact: str = Query(default=os.getenv("NEWS_MIN_IMPACT", NEWS_MIN_IMPACT)),
    lookahead_hrs: int = Query(default=int(os.getenv("NEWS_LOOKAHEAD_HRS", str(NEWS_LOOKAHEAD_HRS)))),
    tz: str = Query(default=os.getenv("NEWS_TZ", NEWS_TZ)),
    save: bool = Query(default=False),
):
    date_str = datetime.now().strftime("%Y-%m-%d")
    df = _safe_fetch(date_str, tz)

    # optional save (also safe)
    if save:
        try: save_csv(df, date_str)
        except Exception: traceback.print_exc()

    try:
        cur_list = _csv_list(currencies)
        out = filter_events(df, currencies=cur_list, min_impact=min_impact,
                            lookahead_hours=lookahead_hrs, local_tz=tz)
        return {"date": date_str, "count": int(len(out)), "events": out.to_dict(orient="records")}
    except Exception as e:
        traceback.print_exc()
        # graceful JSON instead of 500
        return {"date": date_str, "count": 0, "events": [], "error": f"{type(e).__name__}: {e}"}

@app.get("/calendar/by-date")
def calendar_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    currencies: Optional[str] = Query(default=os.getenv("NEWS_CURRENCIES", NEWS_CURRENCIES)),
    min_impact: str = Query(default=os.getenv("NEWS_MIN_IMPACT", NEWS_MIN_IMPACT)),
    lookahead_hrs: int = Query(default=int(os.getenv("NEWS_LOOKAHEAD_HRS", str(NEWS_LOOKAHEAD_HRS)))),
    tz: str = Query(default=os.getenv("NEWS_TZ", NEWS_TZ)),
    save: bool = Query(default=False),
):
    df = _safe_fetch(date, tz)
    if save:
        try: save_csv(df, date)
        except Exception: traceback.print_exc()

    try:
        cur_list = _csv_list(currencies)
        out = filter_events(df, currencies=cur_list, min_impact=min_impact,
                            lookahead_hours=lookahead_hrs, local_tz=tz)
        return {"date": date, "count": int(len(out)), "events": out.to_dict(orient="records")}
    except Exception as e:
        traceback.print_exc()
        return {"date": date, "count": 0, "events": [], "error": f"{type(e).__name__}: {e}"}

try:
    from jobs.calendar_utils import make_telegram_summary
except Exception:
    print("⚠ jobs.calendar_utils missing — summary disabled.")
    make_telegram_summary = lambda df, tz: "Calendar summary unavailable."


@app.get("/calendar/summary")
def calendar_summary(
    currencies: str = "USD,EUR,JPY",
    min_impact: str = "medium",
    lookahead_hrs: int = 12,
    tz: str = NEWS_TZ,
):
    date_str = datetime.now().strftime("%Y-%m-%d")
    df = _safe_fetch(date_str, tz)
    out = filter_events(df, [c.strip() for c in currencies.split(",") if c.strip()],
                        min_impact=min_impact, lookahead_hours=lookahead_hrs, local_tz=tz)
    return {"date": date_str, "summary": make_telegram_summary(out, tz)}
