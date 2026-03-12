"""
market_data_routes.py  (upgraded)
-----------------------------------
Serves metadata and indicators.
Broker endpoints have been removed per the dataset migration plan.
"""
from fastapi import APIRouter, HTTPException, Query
from backend.data_providers.data_manager import data_manager
import pandas as pd
import numpy as np
import os

router = APIRouter(tags=["market_data"])

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")

@router.get("/assets")
def get_assets():
    """Returns uploaded datasets instead of broker assets."""
    assets = []
    seen = set()
    if os.path.exists(DATASETS_DIR):
        for f in os.listdir(DATASETS_DIR):
            if f.endswith(".csv"):
                dataset_id = f.rsplit(".", 1)[0]
                if dataset_id in seen:
                    continue
                seen.add(dataset_id)
                assets.append({
                    "symbol": dataset_id,
                    "market": "Uploaded Datasets",
                    "broker": "local", 
                    "name": dataset_id
                })
    return {"forex": {"datasets": assets}}

@router.get("/markets")
def get_markets():
    return {"markets": ["datasets"]}

@router.get("/brokers")
def get_brokers(market: str = Query(None)):
    return {"brokers": ["local"]}

@router.get("/symbols")
def get_symbols(market: str = Query(None), broker: str = Query(None)):
    assets = get_assets()
    return {"symbols": [a["symbol"] for a in assets.get("forex", {}).get("datasets", [])]}

@router.get("/symbols/{broker}")
def get_symbols_by_broker_path(broker: str):
    return get_symbols()

@router.get("/timeframes")
def get_timeframes():
    from backend.data_providers.data_manager import TIMEFRAME_MAP
    return {"timeframes": list(TIMEFRAME_MAP.keys())}


# Keep /market-data endpoint for backward compatibility with Strategy Lab
# but redirect it to use dataset ID
@router.get("/market-data")
def get_market_data(
    symbol: str,
    broker: str = Query(None),
    timeframe: str = Query(None),
    tf: str = Query(None),
    start: str = Query(None),
    end: str = Query(None),
):
    resolved_tf = timeframe or tf or "1h"
    if not symbol or not symbol.strip():
        raise HTTPException(status_code=400, detail="Missing param: symbol (should be dataset ID)")
        
    try:
        from backend.data_providers.data_manager import data_manager
        # data_manager now takes dataset ID in the symbol param
        candles = data_manager.load_candles(symbol, resolved_tf, broker)
        
        # Apply start/end windowing
        if start or end:
            from datetime import datetime
            start_ts = int(datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp()) if start else 0
            end_ts   = int(datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp())   if end else 9_999_999_999
            candles = [c for c in candles if start_ts <= c["time"] <= end_ts]
            
        return candles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators")
def get_indicators(
    symbol: str,
    broker: str = Query(None),
    timeframe: str = Query("1h"),
):
    try:
        from backend.data_providers.data_manager import data_manager
        candles = data_manager.load_candles(symbol, timeframe, broker)
        if not candles:
            return {"sma": [], "ema": [], "rsi": [], "macd": [], "bbands": []}

        df = pd.DataFrame(candles)
        times = df["time"].tolist()
        close = df["close"]

        from backend.indicators.indicators import (
            calculate_sma, calculate_ema, calculate_rsi,
            calculate_macd, calculate_bbands,
        )

        sma_20 = calculate_sma(close, 20)
        ema_50 = calculate_ema(close, 50)
        rsi_14 = calculate_rsi(close, 14)
        macd, signal, histogram = calculate_macd(close, 12, 26, 9)
        upper_bb, lower_bb, middle_bb = calculate_bbands(close, 20, 2)

        def fmt(series):
            return [{"time": t, "value": v} for t, v in zip(times, series) if not pd.isna(v)]

        def fmt_macd(m, s, h):
            return [
                {"time": times[i], "macd": m.iloc[i], "signal": s.iloc[i], "histogram": h.iloc[i]}
                for i in range(len(times))
                if not pd.isna(m.iloc[i]) and not pd.isna(s.iloc[i])
            ]

        def fmt_bb(u, l, mid):
            return [
                {"time": times[i], "upper": u.iloc[i], "lower": l.iloc[i], "middle": mid.iloc[i]}
                for i in range(len(times)) if not pd.isna(u.iloc[i])
            ]

        return {
            "sma":    fmt(sma_20),
            "ema":    fmt(ema_50),
            "rsi":    fmt(rsi_14),
            "macd":   fmt_macd(macd, signal, histogram),
            "bbands": fmt_bb(upper_bb, lower_bb, middle_bb),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
