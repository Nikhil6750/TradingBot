"""
symbol_routes.py  (upgraded)
------------------------------
FXReplay-style broker-asset registry endpoints.
"""
from fastapi import APIRouter, Query, HTTPException
from backend.data_providers.data_manager import data_manager, BROKER_SYMBOLS, BROKERS_PER_MARKET

router = APIRouter(tags=["symbols"])


@router.get("/markets")
def list_markets():
    return {"markets": list(BROKER_SYMBOLS.keys())}


@router.get("/brokers-for-market")
def brokers_for_market(market: str = Query(...)):
    key = market.lower()
    if key not in BROKER_SYMBOLS:
        raise HTTPException(400, f"Unknown market: {market}")
    return {"market": key, "brokers": list(BROKER_SYMBOLS[key].keys())}


@router.get("/asset-list")
def asset_list():
    """
    Returns all (broker, symbol) pairs in an FXReplay-style grouped format:
    { forex: { oanda: [...], dukascopy: [...] }, crypto: { ... } }
    """
    return BROKER_SYMBOLS


@router.get("/assets-flat")
def assets_flat(market: str = Query(None)):
    """
    Flat list of { broker, symbol } records.
    Optionally filtered by market.
    """
    results = []
    markets = [market.lower()] if market else list(BROKER_SYMBOLS.keys())
    for mkt in markets:
        for broker, symbols in BROKER_SYMBOLS.get(mkt, {}).items():
            for sym in symbols:
                results.append({"market": mkt, "broker": broker, "symbol": sym})
    return {"assets": results}
