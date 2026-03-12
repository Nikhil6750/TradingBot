from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.database import get_db
from backend.database.models import BacktestSession, Trade as TradeModel, PerformanceMetrics as PerfModel
from backend.market_data.loaders import load_candles_from_csv_path
from backend.backtesting.metrics import compute_metrics
from backend.replay.replay_engine import evaluate_replay

router = APIRouter(prefix="/replay", tags=["replay"])

@router.get("/dataset/{name}")
def get_replay_dataset(name: str):
    try:
        candles = load_candles_from_csv_path(name)
        return {"candles": candles}
    except Exception as e:
        raise HTTPException(404, str(e))


class ReplayEvaluatePayload(BaseModel):
    symbol: str
    timeframe: str = "1h"
    config: dict[str, Any] = {}
    cursor: Optional[int] = None


@router.post("/evaluate")
def evaluate_replay_strategy(payload: ReplayEvaluatePayload):
    try:
        return evaluate_replay(
            dataset_id=payload.symbol,
            timeframe=payload.timeframe,
            config=payload.config,
            cursor=payload.cursor,
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

class ManualTradePayload(BaseModel):
    symbol: str
    initial_capital: float = 10000.0
    trades: list[dict]

@router.post("/save_session")
def save_replay_session(payload: ManualTradePayload, db: Session = Depends(get_db)):
    formatted_trades = []
    for t in payload.trades:
         formatted_trades.append({
             "entry_time": t.get("entry_time"),
             "exit_time": t.get("exit_time"),
             "entry_price": t.get("entry_price"),
             "exit_price": t.get("exit_price"),
             "type": t.get("type", "BUY"),
             "pnl": t.get("pnl", 0.0),
         })
         
    metrics_dict = compute_metrics(formatted_trades)
    
    session_obj = BacktestSession(
        symbol=payload.symbol,
        initial_capital=payload.initial_capital,
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
    
    for t in formatted_trades:
        dur = (t["exit_time"] - t["entry_time"]) if t["exit_time"] and t["entry_time"] else None
        db.add(TradeModel(
            session_id  = session_obj.id,
            entry_time  = t["entry_time"],
            exit_time   = t["exit_time"],
            entry_price = t["entry_price"],
            exit_price  = t["exit_price"],
            position    = t["type"],
            pnl         = t["pnl"],
            duration    = dur,
        ))
    db.commit()
    return {"session_id": session_obj.id}
