from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
import os, httpx

router = APIRouter(prefix="/tools", tags=["tools"])

BASE = os.getenv("AGENT_INTERNAL_BASE", "http://127.0.0.1:8000")

class GetPricesArgs(BaseModel):
    symbol: str = Field(..., pattern=r"^[A-Z]{3,12}$")
    timeframe: Literal["1m","5m","15m","1h","4h","1d"] = "1h"
    limit: int = 200

class RunBacktestArgs(BaseModel):
    symbol: str
    timeframe: str = "15m"
    start: str
    end: str
    strategy: str = "streak_pullback_v1"
    params: Dict[str, Any] = {}

class PlaceOrderArgs(BaseModel):
    symbol: str
    side: Literal["buy","sell"]
    qty: float
    order_type: Literal["market","limit"] = "market"
    limit_price: Optional[float] = None
    mode: Literal["paper","live"] = "paper"

class FetchCalendarArgs(BaseModel):
    currency: Literal["USD","EUR","INR","JPY","GBP"] = "USD"
    day: Optional[str] = None

def _post(path: str, payload: Dict[str, Any]):
    url = f"{BASE}{path}"
    try:
        with httpx.Client(timeout=60) as c:
            r = c.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        raise HTTPException(502, f"Upstream call failed: {e}")

@router.post("/run_backtest")
def tool_run_backtest(a: RunBacktestArgs):
    # Forward to your existing /backtest/run endpoint
    body = {
        "symbol": a.symbol, "timeframe": a.timeframe,
        "start": a.start, "end": a.end,
        "strategy": a.strategy, "params": a.params
    }
    return _post("/backtest/run", body)

@router.post("/get_prices")
def tool_get_prices(a: GetPricesArgs):
    # Adjust path/body to your prices endpoint if different
    return _post("/prices/get", a.model_dump())

@router.post("/place_order")
def tool_place_order(a: PlaceOrderArgs):
    if a.mode != "paper":
        raise HTTPException(400, "Live mode disabled by policy")
    return _post("/orders/paper/place", a.model_dump())

@router.post("/fetch_calendar")
def tool_fetch_calendar(a: FetchCalendarArgs):
    # If you already expose /calendar/today|upcoming, call that
    path = "/calendar/upcoming" if a.day is None else "/calendar/day"
    return _post(path, {"currency": a.currency, "day": a.day})
