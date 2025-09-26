# bot/scoring.py

def compute_score(row):
    """
    Returns:
      score: float 0..100
      label: LOW / MEDIUM / HIGH
      factors: dict {trend_ok, momentum_ok, sr_ok, direction}
    Requires: close, EMA_20, EMA_50, RSI_14, ATR_14
    """
    ema20, ema50 = row["EMA_20"], row["EMA_50"]
    rsi, close, atr = row["RSI_14"], row["close"], row["ATR_14"]

    trend_ok    = bool(ema20 > ema50)
    momentum_ok = bool(35 <= rsi <= 65)
    sr_ok       = bool(abs(close - ema20) <= 0.25 * atr)

    direction = "BUY" if trend_ok else "SELL"

    # weights: trend=3, momentum=3, sr=2 (total 8)
    raw = (3*trend_ok + 3*momentum_ok + 2*sr_ok)
    score = round((raw / 8) * 100, 1)
    label = "HIGH" if score >= 75 else ("MEDIUM" if score >= 50 else "LOW")

    return score, label, {
        "trend_ok": trend_ok,
        "momentum_ok": momentum_ok,
        "sr_ok": sr_ok,
        "direction": direction
    }
