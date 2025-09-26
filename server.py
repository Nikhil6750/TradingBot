# server.py — TradingView webhook receiver that triggers your bot summary/CSV push
import os, sys, math, json
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))

# --- ENV & security ---
TV_SHARED_SECRET = os.getenv("TV_SHARED_SECRET", "")      # set this in TradingView alert message & .env
BOT_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID          = os.getenv("TELEGRAM_CHAT_ID", "")
DRY              = (os.getenv("TELEGRAM_DRY_RUN", os.getenv("DRY_RUN", "0")) == "1")

app = FastAPI(title="Samantha TradingView Bridge")

class TVPayload(BaseModel):
    secret: Optional[str] = ""
    event:  Optional[str] = "generic"   # your custom label, e.g. "bar_close" / "signal"
    symbol: Optional[str] = ""
    tf:     Optional[str] = ""          # timeframe text, e.g. "15", "60", "1D"
    price:  Optional[float] = None      # last price included by your alert()
    note:   Optional[str] = ""          # free text from Pine
    ts:     Optional[str] = ""          # ISO datetime you send from Pine if you like
    # You can add more fields as you wish (e.g., score, direction, SL/TP, etc.)

def _tg_text(text: str, parse_mode="HTML") -> bool:
    if DRY or not BOT_TOKEN or not CHAT_ID:
        print(f"[TG-DRY] sendMessage → {text[:1000]}...")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": "true",
            },
            timeout=15,
        )
        if not r.ok:
            print(f"[TG-ERR] sendMessage {r.status_code}: {r.text}")
        return bool(r.ok)
    except Exception as e:
        print(f"[TG-ERR] sendMessage exception: {e}")
        return False

def _tg_file(path: str, caption: str = "") -> bool:
    if DRY or not BOT_TOKEN or not CHAT_ID or not os.path.exists(path):
        print(f"[TG-DRY] sendDocument → {os.path.basename(path)}")
        return False
    try:
        with open(path, "rb") as fh:
            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": (os.path.basename(path), fh, "text/csv")},
                timeout=60,
            )
        if not r.ok:
            print(f"[TG-ERR] sendDocument {r.status_code}: {r.text}")
        return bool(r.ok)
    except Exception as e:
        print(f"[TG-ERR] sendDocument exception: {e}")
        return False

def _build_summary() -> str:
    """Replicate your loop’s summary from CSVs."""
    trades_csv  = os.path.join(ROOT, "backtest_results_trades.csv")
    summary_csv = os.path.join(ROOT, "backtest_results.csv")
    audit_sym   = os.path.join(ROOT, "audit_by_symbol.csv")

    trades = wins = losses = expired = 0
    win_rate = 0.0
    net_r = 0.0
    pf = float("nan")

    if os.path.exists(trades_csv):
        try:
            t = pd.read_csv(trades_csv)
            if "result_r" in t.columns and not t.empty:
                r = pd.to_numeric(t["result_r"], errors="coerce").fillna(0.0)
                trades  = int(len(r))
                wins    = int((r > 0).sum())
                losses  = int((r < 0).sum())
                expired = int((r == 0).sum())
                wl      = wins + losses
                win_rate = (wins / wl * 100.0) if wl else 0.0
                gross_profit = float(r[r > 0].sum())
                gross_loss   = float(-r[r < 0].sum())
                if gross_loss == 0 and gross_profit == 0:
                    pf = float("nan")
                elif gross_loss == 0:
                    pf = float("inf")
                elif gross_profit == 0:
                    pf = 0.0
                else:
                    pf = float(gross_profit / gross_loss)
                net_r = float(r.sum())
        except Exception as e:
            print(f"[TV] Could not compute summary: {e}")

    # Best symbol
    best_line = ""
    if os.path.exists(audit_sym):
        try:
            a = pd.read_csv(audit_sym)
            if not a.empty:
                sort_cols = [c for c in ["pf","avg_r","net_r"] if c in a.columns]
                if sort_cols:
                    a = a.sort_values(by=sort_cols, ascending=[False]*len(sort_cols))
                top = a.iloc[0]
                sym = str(top.get("symbol", "")).upper()
                pf_b = top.get("pf", float("nan"))
                wr_b = top.get("win_rate_%", float("nan"))
                if isinstance(pf_b, (int, float)):
                    best_line = f"\nBest: <b>{sym}</b> (PF {pf_b:.2f}, WR {wr_b:.1f}%)"
                else:
                    best_line = f"\nBest: <b>{sym}</b>"
        except Exception as e:
            print(f"[TV] Could not parse audit_by_symbol.csv: {e}")

    if isinstance(pf, float) and math.isfinite(pf):
        pf_txt = f"{pf:.3f}"
    elif isinstance(pf, float) and math.isinf(pf):
        pf_txt = "∞"
    else:
        pf_txt = "n/a"

    return (
        "<b>📣 Samantha (TV)</b>\n"
        f"Trades: <b>{trades}</b> | W/L/E: <b>{wins}/{losses}/{expired}</b>\n"
        f"Win%: <b>{win_rate:.2f}%</b> | PF: <b>{pf_txt}</b> | NetR: <b>{net_r:.2f}</b>"
        f"{best_line}"
    )

@app.post("/tv")
async def tv_webhook(payload: TVPayload, request: Request):
    # 1) Security check
    if TV_SHARED_SECRET:
        if payload.secret != TV_SHARED_SECRET:
            # Also allow secret via header 'X-TV-SECRET' as a fallback
            hdr = request.headers.get("X-TV-SECRET", "")
            if hdr != TV_SHARED_SECRET:
                raise HTTPException(status_code=401, detail="Invalid secret")

    # 2) Optionally use payload to customize message (symbol, tf, price, note)
    details = []
    if payload.symbol: details.append(f"<b>{payload.symbol}</b>")
    if payload.tf:     details.append(f"TF: <b>{payload.tf}</b>")
    if payload.price is not None: details.append(f"Price: <b>{payload.price}</b>")
    header = " • ".join(details)
    if header:
        _tg_text(f"🔔 TradingView alert: {header}")

    # 3) Send your standard summary + attach CSVs
    msg = _build_summary()
    _tg_text(msg)

    # Attach CSVs if present
    for pth, cap in [
        (os.path.join(ROOT, "audit_by_symbol.csv"), "audit_by_symbol.csv"),
        (os.path.join(ROOT, "audit_by_hour.csv"),   "audit_by_hour.csv"),
        (os.path.join(ROOT, "backtest_results.csv"),"backtest_results.csv"),
    ]:
        if os.path.exists(pth):
            _tg_file(pth, cap)

    return {"ok": True}
