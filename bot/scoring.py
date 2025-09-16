import pandas as pd

def _get(row, candidates):
    for k in candidates:
        if k in row and pd.notna(row[k]):
            return row[k]
    return None

def compute_score(row):
    """
    Returns (score_float, label_str, factors_dict)
    """
    ema20 = _get(row, ["EMA20", "ema20", "EMA_20", "ema_20"])
    ema50 = _get(row, ["EMA50", "ema50", "EMA_50", "ema_50"])
    rsi = _get(row, ["RSI14", "rsi14", "RSI_14", "rsi_14"])
    atr = _get(row, ["ATR14", "atr14", "ATR_14", "atr_14"])
    close = _get(row, ["close", "Close", "close_price"])

    direction = row.get("direction")
    if direction is None:
        if ema20 is not None and ema50 is not None:
            direction = "BUY" if ema20 > ema50 else "SELL"
        else:
            direction = "BUY"

    trend_ok = 1 if (ema20 is not None and ema50 is not None and (
        (direction == "BUY" and ema20 > ema50) or
        (direction == "SELL" and ema20 < ema50))) else 0

    momentum_ok = 1 if (rsi is not None and 30 <= rsi <= 70) else 0

    sr_ok = 0
    try:
        if close is not None and ema20 is not None:
            sr_ok = 1 if abs(close - ema20) / ema20 <= 0.01 else 0
    except Exception:
        sr_ok = 0

    weights = {"trend": 3, "momentum": 3, "sr": 2}
    total_w = sum(weights.values())
    score = (trend_ok * weights["trend"] +
             momentum_ok * weights["momentum"] +
             sr_ok * weights["sr"]) / total_w * 100

    if score >= 70:
        label = "HIGH"
    elif score >= 40:
        label = "MEDIUM"
    else:
        label = "LOW"

    factors = {
        "trend_ok": bool(trend_ok),
        "momentum_ok": bool(momentum_ok),
        "sr_ok": bool(sr_ok),
        "direction": direction
    }
    return score, label, factors
