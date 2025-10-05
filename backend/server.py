from __future__ import annotations
import io, os, glob
from typing import Optional, List
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from urllib.parse import quote, unquote

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

app = FastAPI(title="Trading Bot API", version="2.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- helpers --------------------
def _parse_hour_allow(hour_allow: str) -> tuple[int, int]:
    try:
        a, b = map(int, str(hour_allow).split("-"))
        a = min(max(a, 0), 23)
        b = min(max(b, 1), 24)  # end exclusive
        if a == b:
            return (0, 24)
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
    """Normalize OHLC/time, coerce numeric, sort by time, and attach a stable time index (tidx)."""
    lower = {c.lower(): c for c in df.columns}
    need = ["time", "open", "high", "low", "close"]
    for k in need:
        if k not in lower:
            raise ValueError(f"Missing '{k}' in CSV")

    df = df.rename(columns={
        lower["time"]: "time",
        lower["open"]: "open",
        lower["high"]: "high",
        lower["low"]: "low",
        lower["close"]: "close",
    })

    for k in ["open", "high", "low", "close"]:
        df[k] = pd.to_numeric(df[k], errors="coerce")
    df["time"] = _coerce_time_any(df["time"])
    df = df.dropna(subset=["time", "open", "high", "low", "close"])\
           .sort_values("time")\
           .reset_index(drop=True)

    # Monotonic, time-sorted index used everywhere
    df["tidx"] = np.arange(len(df), dtype=int)
    return df


def _png_error(msg: str) -> StreamingResponse:
    fig, ax = plt.subplots(figsize=(6, 1.5))
    ax.axis("off")
    ax.text(0.02, 0.5, msg, fontsize=10, va="center", ha="left")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control": "no-store"})

# -------------------- patterns --------------------
def _body(o, c): return abs(float(c) - float(o))
def _upper(o, h, c): return float(h) - max(float(o), float(c))
def _lower(o, l, c): return min(float(o), float(c)) - float(l)

def is_bullish_engulfing(o1,h1,l1,c1, o2,h2,l2,c2):
    return (c1 < o1) and (c2 > o2) and (o2 <= c1) and (c2 >= o1)

def is_bearish_engulfing(o1,h1,l1,c1, o2,h2,l2,c2):
    return (c1 > o1) and (c2 < o2) and (o2 >= c1) and (c2 <= o1)

def is_hammer(o,h,l,c):
    b = _body(o,c)
    return (_lower(o,l,c) >= 2*b) and (_upper(o,h,c) <= b*0.5)

def is_shooting_star(o,h,l,c):
    b = _body(o,c)
    return (_upper(o,h,c) >= 2*b) and (_lower(o,l,c) <= b*0.5)

# -------------------- outcome --------------------
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
        step = s.replace(0, s[s > 0].min()).head(200).min()
        if pd.isna(step) or step == 0:
            return 0.001 if sym.endswith("JPY") else 0.0001
        for p in [0.00001, 0.0001, 0.001, 0.01]:
            if step >= p:
                return p
        return step
    except Exception:
        return 0.001 if sym.endswith("JPY") else 0.0001


def evaluate_trade_pos(df: pd.DataFrame, entry_pos: int, side: str, entry_price: float, params: OutcomeParams):
    """Evaluate outcome iterating by *row position* (tidx)."""
    sym = df.attrs.get("symbol", "UNKNOWN")
    point = _pip_point_for_symbol(sym, df)
    tp = params.tp_pips * point
    sl = params.sl_pips * point

    if side == "LONG":
        target, stop = entry_price + tp, entry_price - sl
    else:
        target, stop = entry_price - tp, entry_price + sl

    last_pos = min(len(df) - 1, entry_pos + params.max_hold_bars)
    outcome = "timeout"
    exit_price = float(df.iloc[last_pos]["close"])
    exit_time = pd.to_datetime(df.iloc[last_pos]["time"]).to_pydatetime()

    for i in range(entry_pos + 1, last_pos + 1):
        bar = df.iloc[i]
        lo, hi = float(bar["low"]), float(bar["high"])
        if side == "LONG":
            if lo <= stop:
                outcome, exit_price = "loss", stop
                exit_time = pd.to_datetime(bar["time"]).to_pydatetime()
                break
            if hi >= target:
                outcome, exit_price = "win", target
                exit_time = pd.to_datetime(bar["time"]).to_pydatetime()
                break
        else:
            if hi >= stop:
                outcome, exit_price = "loss", stop
                exit_time = pd.to_datetime(bar["time"]).to_pydatetime()
                break
            if lo <= target:
                outcome, exit_price = "win", target
                exit_time = pd.to_datetime(bar["time"]).to_pydatetime()
                break

    risk = max(sl, 1e-12)
    r_mult = round(((exit_price - entry_price) if side == "LONG" else (entry_price - exit_price)) / risk, 2)
    return {"outcome": outcome, "exit_time": exit_time, "exit_price": round(exit_price, 6), "r_multiple": r_mult}


# -------------------- models --------------------
class BacktestRunReq(BaseModel):
    symbol: str
    hour_allow: str = "0-24"      # end exclusive
    date: Optional[str] = None    # YYYY-MM-DD (UTC)
    tp_pips: float = 10.0
    sl_pips: float = 10.0
    max_hold_bars: int = 12
    max_alerts: int = 10
    cooldown_bars: int = 3
    fill: str = "next_open"
    hit_order: str = "conservative"
    tz: str = "UTC"
    bars_plot: int = 40

# -------------------- routes --------------------
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

    # --- filter by date/hour but KEEP tidx from full df ---
    df_filt = df_full
    if req.date:
        d = pd.to_datetime(req.date).date()
        df_filt = df_filt[df_filt["time"].dt.date == d]
        if df_filt.empty:
            return JSONResponse({"ok": False, "error": f"No data for {req.date}"}, status_code=404)

    h0, h1 = _parse_hour_allow(req.hour_allow)
    df_filt = df_filt[(df_filt["time"].dt.hour >= h0) & (df_filt["time"].dt.hour < h1)]
    if df_filt.empty:
        return JSONResponse({"ok": False, "error": f"No rows in hours {req.hour_allow} (UTC)"}, status_code=404)

    df_filt = df_filt.reset_index(drop=True)
    params = OutcomeParams(req.tp_pips, req.sl_pips, req.max_hold_bars, req.fill, req.hit_order)

    alerts = []
    last_signal_i = -10**9

    for i in range(1, len(df_filt)):
        p, c = df_filt.iloc[i - 1], df_filt.iloc[i]
        reason, side = None, None

        if is_bullish_engulfing(p["open"], p["high"], p["low"], p["close"], c["open"], c["high"], c["low"], c["close"]):
            reason, side = "bullish_engulfing", "LONG"
        elif is_bearish_engulfing(p["open"], p["high"], p["low"], p["close"], c["open"], c["high"], c["low"], c["close"]):
            reason, side = "bearish_engulfing", "SHORT"
        elif is_hammer(c["open"], c["high"], c["low"], c["close"]):
            reason, side = "hammer", "LONG"
        elif is_shooting_star(c["open"], c["high"], c["low"], c["close"]):
            reason, side = "shooting_star", "SHORT"
        else:
            continue

        # cooldown to avoid clusters
        if i - last_signal_i < max(0, int(req.cooldown_bars)):
            continue
        last_signal_i = i

        t_utc  = pd.to_datetime(c["time"], utc=True)
        tidx   = int(c["tidx"])                        # anchor in FULL df (time-sorted)
        entry_pos = min(tidx + 1, len(df_full) - 1)    # next bar (position in full df)

        entry_px = float(df_full.iloc[entry_pos]["open"]) if params.fill == "next_open" else float(c["close"])
        outc = evaluate_trade_pos(df_full, entry_pos, side, entry_px, params)

        qt = quote(t_utc.isoformat())
        plot_qs = f"/backtest/plot?symbol={sym}&tidx={tidx}&tz={req.tz}&bars={max(10, int(req.bars_plot))}&reason={reason}&time={qt}"

        alerts.append({
            "time": t_utc.isoformat(),
            "row_index": i,
            "tidx": tidx,
            "side": side,
            "reason": reason,
            "entry_price": entry_px,
            "exit_price": outc["exit_price"],
            "exit_time": outc["exit_time"].isoformat(),
            "outcome": outc["outcome"],
            "r_multiple": outc["r_multiple"],
            "take": (outc["outcome"] == "win"),
            "plot_url": plot_qs,
        })
        if len(alerts) >= req.max_alerts:
            break

    trades = len(alerts)
    wins = sum(a["outcome"] == "win" for a in alerts)
    losses = sum(a["outcome"] == "loss" for a in alerts)
    timeouts = sum(a["outcome"] == "timeout" for a in alerts)
    win_rate = round(100 * wins / max(trades, 1), 2)

    return {
        "ok": True,
        "symbol": sym,
        "summary": {"trades": trades, "wins": wins, "losses": losses, "timeouts": timeouts, "win_rate": win_rate},
        "run": {"date_utc": req.date, "hour_allow": req.hour_allow},
        "alerts": alerts,
    }


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
        return _png_error(f"No CSV for {symbol}")

    try:
        df = _ensure_ohlc(pd.read_csv(path))
    except Exception as e:
        return _png_error(str(e))
    if df.empty:
        return _png_error("No rows to plot")

    # Center by time-sorted index (tidx). Fallback to time if missing.
    if tidx is not None:
        center_pos = int(np.clip(int(tidx), 0, len(df) - 1))
    else:
        if not time:
            return _png_error("Missing tidx/time")
        t_utc = pd.to_datetime(unquote(time).strip(), utc=True, errors="coerce")
        if pd.isna(t_utc):
            return _png_error("Bad 'time'")
        center_pos = int((df["time"] - t_utc).abs().argmin())

    half = max(1, int(bars) // 2)
    lo = max(0, center_pos - half)
    hi = min(len(df), center_pos + half)
    if hi <= lo:
        return _png_error("Empty window")

    win = df.iloc[lo:hi].copy().reset_index(drop=True)

    try:
        win["time_local"] = pd.to_datetime(win["time"]).dt.tz_convert(tz)
    except Exception:
        win["time_local"] = pd.to_datetime(win["time"])

    anchor_ts = pd.to_datetime(df.iloc[center_pos]["time"]).tz_convert("UTC")

    buf = io.BytesIO()
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(win))
    for i, r in enumerate(win.itertuples(index=False)):
        o, h, l, c = float(r.open), float(r.high), float(r.low), float(r.close)
        color = "#22c55e" if c >= o else "#ef4444"
        ax.vlines(i, l, h, color=color, linewidth=1.2)
        body_y = min(o, c)
        body_h = max(1e-10, abs(c - o))
        ax.add_patch(plt.Rectangle((i - 0.3, body_y), 0.6, body_h, color=color, alpha=0.9, linewidth=0))

    ax.axvline(int(np.clip(center_pos - lo, 0, len(win) - 1)), color="#3b82f6", linewidth=1.0, alpha=0.6)
    ax.set_xlim(-1, len(win))
    step = max(1, len(x) // 6)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([t.strftime("%H:%M") for t in win["time_local"].iloc[::step]],
                       rotation=30, ha="right", fontsize=8)

    ymin, ymax = float(win["low"].min()), float(win["high"].max())
    pad = (ymax - ymin) * 0.05 if ymax > ymin else 0.0001
    ax.set_ylim(ymin - pad, ymax + pad)

    ttl = f"{symbol.upper()} {anchor_ts.strftime('%Y-%m-%d %H:%M UTC')}"
    if reason: ttl += f" • {reason}"
    ax.set_title(ttl, fontsize=10, weight="bold")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/symbols")
def list_symbols():
    if not os.path.isdir(DATA_DIR):
        return {"symbols": []}
    syms: List[str] = []
    for f in sorted(os.listdir(DATA_DIR)):
        if f.lower().endswith(".csv"):
            s = f.replace("FX_", "").split(",")[0].strip()
            if s and s not in syms:
                syms.append(s)
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
