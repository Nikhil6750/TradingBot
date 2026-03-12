"""
session_routes.py  (FXReplay MVP)
-----------------------------------
Session-centric API:
  POST   /sessions              → create session (name, broker, symbol, balance, dates)
  GET    /sessions              → list all sessions
  GET    /sessions/{id}         → get session detail
  GET    /sessions/{id}/candles → return sliced OHLCV candles for the session
  DELETE /sessions/{id}         → delete session

Candle data is pulled from the DataManager (which caches datasets locally).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from backend.database.database import get_db
from backend.database.models import TradingSession, SessionTrade
from backend.data_providers.data_manager import data_manager

router = APIRouter(prefix="", tags=["Sessions"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SessionCreateReq(BaseModel):
    session_name: str
    broker: str = "oanda"
    symbol: str
    balance: float = 10_000.0
    start_date: Optional[str] = None
    end_date:   Optional[str] = None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _session_dict(s: TradingSession) -> dict:
    return {
        "id":           s.id,
        "session_name": s.session_name,
        "broker":       s.broker,
        "symbol":       s.symbol,
        "balance":      s.balance,
        "start_date":   s.start_date.isoformat() if s.start_date else None,
        "end_date":     s.end_date.isoformat()   if s.end_date   else None,
        "created_at":   s.created_at.isoformat() if s.created_at else None,
    }


# ── Create session ─────────────────────────────────────────────────────────────

@router.post("/sessions")
def create_session(req: SessionCreateReq, db: DBSession = Depends(get_db)):
    sess = TradingSession(
        session_name=req.session_name,
        broker=req.broker.lower(),
        symbol=req.symbol.upper(),
        balance=req.balance,
        start_date=_parse_dt(req.start_date),
        end_date=_parse_dt(req.end_date),
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return _session_dict(sess)


# Keep legacy endpoint alive
@router.post("/sessions/create")
def create_session_legacy(req: SessionCreateReq, db: DBSession = Depends(get_db)):
    return create_session(req, db)


# ── List sessions ─────────────────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(db: DBSession = Depends(get_db)):
    rows = db.query(TradingSession).order_by(TradingSession.created_at.desc()).all()
    return [_session_dict(s) for s in rows]


# ── Get single session ────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: DBSession = Depends(get_db)):
    sess = db.query(TradingSession).filter(TradingSession.id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")
    return _session_dict(sess)


# ── Get candles for session ───────────────────────────────────────────────────

@router.get("/sessions/{session_id}/candles")
def get_session_candles(
    session_id: int,
    timeframe: str = Query("1h"),
    db: DBSession = Depends(get_db),
):
    """
    Load dataset for (broker, symbol), aggregate to timeframe,
    slice to [start_date, end_date], and return OHLCV records.
    """
    sess = db.query(TradingSession).filter(TradingSession.id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")

    try:
        candles = data_manager.load_candles(sess.broker, sess.symbol, timeframe)
    except Exception as e:
        raise HTTPException(500, f"Failed to load candle data: {e}")

    # Slice by date range if defined
    if sess.start_date or sess.end_date:
        start_ts = int(sess.start_date.timestamp()) if sess.start_date else 0
        end_ts   = int(sess.end_date.timestamp())   if sess.end_date   else 9_999_999_999
        candles  = [c for c in candles if start_ts <= c["time"] <= end_ts]

    return {
        "session":  _session_dict(sess),
        "timeframe": timeframe,
        "candles":   candles,
    }


# ── Delete session ────────────────────────────────────────────────────────────

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: DBSession = Depends(get_db)):
    sess = db.query(TradingSession).filter(TradingSession.id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")
    db.delete(sess)
    db.commit()
    return {"ok": True}


# ── Trade endpoints (kept for replay) ─────────────────────────────────────────

class TradeOpenReq(BaseModel):
    session_id: int
    symbol: str
    side: str
    entry_price: float
    quantity: float
    timestamp: float

@router.post("/trades/open")
def open_trade(req: TradeOpenReq, db: DBSession = Depends(get_db)):
    sess = db.query(TradingSession).filter(TradingSession.id == req.session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")
    trade = SessionTrade(
        session_id=req.session_id, symbol=req.symbol, side=req.side.upper(),
        entry_price=req.entry_price, quantity=req.quantity, timestamp=req.timestamp,
    )
    db.add(trade); db.commit(); db.refresh(trade)
    return {"id": trade.id, "session_id": trade.session_id, "side": trade.side}

class TradeCloseReq(BaseModel):
    trade_id: int
    exit_price: float
    pnl: float

@router.post("/trades/close")
def close_trade(req: TradeCloseReq, db: DBSession = Depends(get_db)):
    trade = db.query(SessionTrade).filter(SessionTrade.id == req.trade_id).first()
    if not trade:
        raise HTTPException(404, "Trade not found")
    trade.exit_price = req.exit_price
    trade.pnl = req.pnl
    sess = db.query(TradingSession).filter(TradingSession.id == trade.session_id).first()
    if sess:
        sess.balance += req.pnl
    db.commit(); db.refresh(trade)
    return {"id": trade.id, "pnl": trade.pnl}
