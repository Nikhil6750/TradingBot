from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from fastapi import Query as QParam
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import BacktestSession, Trade as TradeModel, PerformanceMetrics as PerfModel
from backend.market_data.csv_dataset_loader import load_dataset_candles
from backend.setups.trade_setup_store import build_trade_setups, store_trade_setups
from backend.strategy_engine import run_strategy
from backend.utils.helpers import clean_data

router = APIRouter(tags=["backtesting"])

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "raw"
    config: dict

@router.post("/run-strategy")
@router.post("/run-backtest")
async def run_backtest(payload: BacktestRequest):
    try:
        datasets_dir = Path(__file__).resolve().parent.parent / "datasets"
        candles = load_dataset_candles(payload.symbol, datasets_dir, timeframe=payload.timeframe or "1m")
        if not candles:
            raise ValueError(f"No market data available for dataset {payload.symbol}")
    except Exception as e:
        raise HTTPException(400, f"Data fetch error: {str(e)}")

    try:
        df = pd.DataFrame(candles)
        result = run_strategy(df, payload.config)
        result = clean_data(result)
    except ValueError as e:
        raise HTTPException(400, f"Strategy Error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Strategy Error: {str(e)}")

    response_payload = {
        "candles":      candles,
        "buy_signals":  result.get("buy_signals",  []),
        "sell_signals": result.get("sell_signals", []),
        "trades":       result.get("trades",       []),
        "metrics":      result.get("metrics",      {}),
        "indicators":   result.get("indicators",   {}),
    }
    trade_setups = build_trade_setups(
        candles,
        response_payload["buy_signals"],
        response_payload["sell_signals"],
    )
    store_trade_setups(payload.symbol, payload.timeframe or "1m", trade_setups)
    response_payload["trade_setups"] = trade_setups

    try:
        db: Session = next(get_db())
        metrics_dict = result.get("metrics", {})
        trades_list  = result.get("trades",  [])

        session_obj = BacktestSession(
            symbol         = payload.symbol,
            initial_capital = 10_000.0,
        )
        db.add(session_obj)
        db.flush()

        pf = PerfModel(
            session_id    = session_obj.id,
            win_rate      = metrics_dict.get("win_rate"),
            profit_factor = metrics_dict.get("profit_factor"),
            sharpe_ratio  = metrics_dict.get("sharpe_ratio"),
            max_drawdown  = metrics_dict.get("max_drawdown"),
            total_return  = metrics_dict.get("total_return"),
            total_trades  = metrics_dict.get("total_trades"),
            best_trade    = metrics_dict.get("best_trade"),
            worst_trade   = metrics_dict.get("worst_trade"),
            expectancy    = metrics_dict.get("expectancy"),
            avg_trade     = metrics_dict.get("avg_trade"),
        )
        db.add(pf)

        for t in trades_list:
            entry = t.get("entry_time")
            exit_ = t.get("exit_time")
            dur   = (exit_ - entry) if exit_ and entry else None
            db.add(TradeModel(
                session_id  = session_obj.id,
                entry_time  = entry,
                exit_time   = exit_,
                entry_price = t.get("entry_price"),
                exit_price  = t.get("exit_price"),
                position    = t.get("type", "BUY"),
                pnl         = t.get("pnl", 0.0),
                duration    = dur,
            ))

        db.commit()
        response_payload["session_id"] = session_obj.id
    except Exception:
        pass 

    return response_payload

@router.get("/backtests")
def list_backtests(limit: int = QParam(50, ge=1, le=500), db: Session = Depends(get_db)):
    try:
        sessions = (
            db.query(BacktestSession)
            .order_by(BacktestSession.created_at.desc())
            .limit(limit)
            .all()
        )
        result = []
        for s in sessions:
            m = s.metrics
            result.append({
                "id":           s.id,
                "symbol":       s.symbol,
                "created_at":   s.created_at.isoformat() if s.created_at else None,
                "total_trades": m.total_trades  if m else None,
                "total_return": m.total_return  if m else None,
                "sharpe_ratio": m.sharpe_ratio  if m else None,
                "win_rate":     m.win_rate      if m else None,
                "max_drawdown": m.max_drawdown  if m else None,
            })
        return result
    except Exception:
        return []

@router.get("/backtests/{session_id}")
def get_backtest(session_id: int, db: Session = Depends(get_db)):
    s = db.query(BacktestSession).filter(BacktestSession.id == session_id).first()
    if not s:
        raise HTTPException(404, "Session not found")
    m = s.metrics
    trades_data = [
        {
            "entry_time":  t.entry_time,
            "exit_time":   t.exit_time,
            "entry_price": t.entry_price,
            "exit_price":  t.exit_price,
            "type":        t.position,
            "pnl":         t.pnl,
        }
        for t in s.trades
    ]
    return {
        "id":           s.id,
        "symbol":       s.symbol,
        "created_at":   s.created_at.isoformat() if s.created_at else None,
        "trades":       trades_data,
        "metrics": {
            "win_rate":      m.win_rate      if m else None,
            "profit_factor": m.profit_factor if m else None,
            "sharpe_ratio":  m.sharpe_ratio  if m else None,
            "max_drawdown":  m.max_drawdown  if m else None,
            "total_return":  m.total_return  if m else None,
            "total_trades":  m.total_trades  if m else None,
            "best_trade":    m.best_trade    if m else None,
            "worst_trade":   m.worst_trade   if m else None,
            "expectancy":    m.expectancy    if m else None,
            "avg_trade":     m.avg_trade     if m else None,
        } if m else {},
    }
