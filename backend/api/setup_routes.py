from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi import Query as QParam
from pydantic import BaseModel, Field

from backend.market_data.csv_dataset_loader import load_dataset_candles
from backend.setups.setup_registry import build_setup_config, get_setup, list_setups
from backend.setups.trade_setup_store import (
    build_trade_setups,
    get_latest_trade_setup_timeframe,
    get_trade_setups,
    store_trade_setups,
)
from backend.strategy_engine import run_strategy
from backend.utils.helpers import clean_data


router = APIRouter(tags=["setups"])


class RunSetupRequest(BaseModel):
    symbol: str
    timeframe: str = "1m"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    pine_script: str = ""


def _load_candles(symbol: str, timeframe: str) -> list[dict]:
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets"
    candles = load_dataset_candles(symbol, datasets_dir, timeframe=timeframe or "1m")
    if not candles:
        raise ValueError(f"No market data available for dataset {symbol}")
    return candles


@router.get("/setups")
def get_available_setups() -> dict:
    return {"setups": list_setups()}


@router.get("/trade-setups/{dataset_id}")
def get_detected_trade_setups(dataset_id: str, timeframe: str = QParam(None)):
    resolved_timeframe = timeframe or get_latest_trade_setup_timeframe(dataset_id)
    return {
        "dataset_id": dataset_id,
        "timeframe": resolved_timeframe,
        "setups": get_trade_setups(dataset_id, resolved_timeframe),
    }


@router.post("/run-setup/{setup_id}")
async def run_setup(setup_id: str, payload: RunSetupRequest):
    try:
        setup = get_setup(setup_id)
        candles = _load_candles(payload.symbol, payload.timeframe)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Setup data error: {str(exc)}")

    try:
        df = pd.DataFrame(candles)
        config = build_setup_config(
            setup_id,
            parameters=payload.parameters,
            pine_script=payload.pine_script,
        )
        result = clean_data(run_strategy(df, config))
    except ValueError as exc:
        raise HTTPException(400, f"Setup strategy error: {str(exc)}")
    except Exception as exc:
        raise HTTPException(500, f"Setup strategy error: {str(exc)}")

    trade_setups = build_trade_setups(
        candles,
        result.get("buy_signals", []),
        result.get("sell_signals", []),
    )
    store_trade_setups(payload.symbol, payload.timeframe or "1m", trade_setups)

    return {
        "setup_id": setup["id"],
        "setup_name": setup["name"],
        "candles": candles,
        "buy_signals": result.get("buy_signals", []),
        "sell_signals": result.get("sell_signals", []),
        "trades": result.get("trades", []),
        "metrics": result.get("metrics", {}),
        "indicators": result.get("indicators", {}),
        "trade_setups": trade_setups,
    }
