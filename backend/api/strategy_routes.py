import json
import shutil
import tempfile
from pathlib import Path
import pandas as pd
from typing import Any
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Strategy
from backend.data_providers.data_manager import data_manager
from backend.utils.helpers import clean_data

router = APIRouter()

# ── CRUD Strategy Endpoints ───────────────────────────────────────────────────
class StrategyCreate(BaseModel):
    name: str
    type: str
    rules_json: dict = {}
    python_code: str = ""
    risk_settings: dict = {}

@router.post("/strategies/create")
async def create_strategy(payload: StrategyCreate, db: Session = Depends(get_db)):
    try:
        # Wrap the disparate inputs into the single generic strategy_json column expected by models.py
        config_payload = {
            "mode": payload.type,
            "rules_json": payload.rules_json,
            "python_code": payload.python_code,
            "risk_settings": payload.risk_settings,
        }
        
        db_strategy = Strategy(
            strategy_name=payload.name,
            strategy_type=payload.type,
            config=config_payload
        )
        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        return {"success": True, "id": db_strategy.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error saving strategy: {str(e)}")

@router.get("/strategies")
async def get_strategies(db: Session = Depends(get_db)):
    strats = db.query(Strategy).all()
    out = []
    for s in strats:
        conf = s.config
        out.append({
            "id": s.id,
            "name": s.strategy_name,
            "type": s.strategy_type,
            "rules_json": conf.get("rules_json", {}),
            "python_code": conf.get("python_code", ""),
            "risk_settings": conf.get("risk_settings", {}),
            "created_at": str(s.created_at)
        })
    return out

# ── Strategy Explainer Endpoint ───────────────────────────────────────────────
class ExplainRule(BaseModel):
    indicator: str
    operator: str
    value: Any

class ExplainRequest(BaseModel):
    rules: list[ExplainRule]
    side: str = "buy"

@router.post("/explain_strategy")
async def explain_strategy(body: ExplainRequest):
    try:
        from backend.strategies.strategy_explainer import generate_explanation
        rules_as_dicts = [r.dict() for r in body.rules]
        result = generate_explanation(rules_as_dicts, side=body.side)
        return result
    except Exception as e:
        raise HTTPException(500, f"Explainer Error: {str(e)}")

# ── Market Regime Detection Endpoint ──────────────────────────────────────────
class RegimeRequest(BaseModel):
    symbol: str
    timeframe: str

@router.post("/detect_regime")
async def detect_regime(body: RegimeRequest):
    try:
        candles = data_manager.load_candles(body.symbol, body.timeframe)
        if not candles:
            raise ValueError(f"No market data available for {body.symbol} {body.timeframe}")
    except Exception as e:
        raise HTTPException(400, f"Data fetch error: {str(e)}")

    try:
        df = pd.DataFrame(candles)
        from backend.ml.regime_detection import detect_market_regime
        result = detect_market_regime(df)
        return clean_data(result)
    except Exception as e:
        raise HTTPException(500, f"Regime Detection Error: {str(e)}")

# ── Trade Scoring Endpoint ────────────────────────────────────────────────────
class ScoreTradesRequest(BaseModel):
    candles: list[dict]
    trades:  list[dict]

@router.post("/score_trades")
async def score_trades_endpoint(body: ScoreTradesRequest):
    try:
        if not body.trades:
            return {"scored_trades": []}
        df = pd.DataFrame(body.candles)
        from backend.ml.trade_scoring import score_trades
        scored = score_trades(df, body.trades)
        return clean_data({"scored_trades": scored})
    except Exception as e:
        raise HTTPException(500, f"Trade Scoring Error: {str(e)}")

# ── Regime Performance Breakdown Endpoint ─────────────────────────────────────
class RegimePerfRequest(BaseModel):
    candles: list[dict]
    trades:  list[dict]

@router.post("/regime_performance")
async def regime_performance_endpoint(body: RegimePerfRequest):
    try:
        if not body.trades or not body.candles:
            return {"breakdown": {}, "insight": "No data provided."}
        df = pd.DataFrame(body.candles)
        from backend.ml.regime_performance import compute_regime_performance
        result = compute_regime_performance(df, body.trades)
        return clean_data(result)
    except Exception as e:
        raise HTTPException(500, f"Regime Performance Error: {str(e)}")

class InsightsRequest(BaseModel):
    candles: list[dict]
    trades:  list[dict]

@router.post("/strategy_insights")
async def strategy_insights_endpoint(body: InsightsRequest):
    try:
        from backend.strategies.strategy_insights import generate_insights
        insights = generate_insights(body.candles, body.trades)
        return {"insights": insights}
    except Exception as e:
        raise HTTPException(500, f"Strategy Insights Error: {str(e)}")

class OptimizeRequest(BaseModel):
    symbol: str
    timeframe: str
    config: dict
    param_ranges: dict
    trials: int = 50

@router.post("/optimize_strategy")
async def optimize_strategy(payload: OptimizeRequest):
    try:
        candles = data_manager.load_candles(payload.symbol, payload.timeframe)
        if not candles:
            raise ValueError("No market data available.")
    except Exception as e:
        raise HTTPException(400, f"Data fetch error: {str(e)}")

    try:
        df = pd.DataFrame(candles)
        from backend.backtesting.optimizer import run_optimization
        opt_results = run_optimization(df, payload.config, payload.param_ranges, n_trials=payload.trials)
        return clean_data(opt_results)
    except Exception as e:
        raise HTTPException(500, f"Optimization Error: {str(e)}")
