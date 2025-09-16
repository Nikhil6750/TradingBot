import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_alert(filename, score, label, factors, df):
    """
    Sends a formatted alert to Telegram with signal details including SL/TP.
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("[ALERT] Missing Telegram credentials, skipping alert.")
        return False

    last_row = df.iloc[-1]
    close = last_row["close"]
    ema20 = last_row.get("EMA_20", None)
    ema50 = last_row.get("EMA_50", None)
    rsi14 = last_row.get("RSI_14", None)
    atr14 = last_row.get("ATR_14", None)

    # Direction & SL/TP
    direction = "BUY" if ema20 > ema50 else "SELL"
    if direction == "BUY":
        sl = close - 1.5 * atr14 if atr14 else None
        tp = close + 3.0 * atr14 if atr14 else None
    else:
        sl = close + 1.5 * atr14 if atr14 else None
        tp = close - 3.0 * atr14 if atr14 else None

    # Pre-format values safely
    sl_str = f"{sl:.3f}" if sl else "N/A"
    tp_str = f"{tp:.3f}" if tp else "N/A"
    rr = abs((tp - close) / (close - sl)) if sl and tp else None
    rr_str = f"{rr:.2f}" if rr else "N/A"

    ema20_str = f"{ema20:.3f}" if ema20 else "N/A"
    ema50_str = f"{ema50:.3f}" if ema50 else "N/A"
    rsi14_str = f"{rsi14:.2f}" if rsi14 else "N/A"
    atr14_str = f"{atr14:.3f}" if atr14 else "N/A"

    # Compose message
    message = (
        f"📊 Trading Alert\n"
        f"Pair: {filename}\n"
        f"Timeframe: {factors.get('timeframe','')}\n"
        f"Candle Time: {factors.get('bar_time','')}\n\n"
        f"Score: {score:.1f} ({label})\n"
        f"Trend: {factors.get('trend_ok')}, "
        f"Momentum: {factors.get('momentum_ok')}, "
        f"S/R: {factors.get('sr_ok')}\n\n"
        f"Entry: {close:.3f}\n"
        f"SL: {sl_str}\n"
        f"TP: {tp_str}\n"
        f"R:R = {rr_str}\n\n"
        f"EMA20={ema20_str}, EMA50={ema50_str}, "
        f"RSI14={rsi14_str}, ATR14={atr14_str}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload)
        return True
    except Exception as e:
        print(f"[ALERT] Telegram send failed: {e}")
        return False
