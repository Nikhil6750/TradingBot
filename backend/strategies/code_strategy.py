import pandas as pd
import numpy as np
from typing import Dict, Any, List

def run_code_strategy(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a user-provided Python code logic string on the DataFrame.
    The logic string is evaluated per candle in an isolated namespace.
    """
    df = df.copy()
    code_str = config.get("code_string", "").strip()

    # If empty, just return empty signals
    if not code_str:
         return {
            "buy_signals": [], "sell_signals": [],
            "trades": [], "metrics": {}, "indicators": {}
        }

    # Pre-calculate common indicators so they are available in the namespace
    # This is a fixed set of convenient indicators for the code mode.
    df["sma_fast"] = df["close"].rolling(window=10).mean()
    df["sma_slow"] = df["close"].rolling(window=50).mean()

    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["bb_middle"] = df["close"].rolling(20).mean()
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]

    stop_loss_pct = config.get("stop_loss", 0.02)
    take_profit_pct = config.get("take_profit", 0.04)

    buy_signals = []
    sell_signals = []
    trades = []
    in_position = False
    entry_price = 0.0
    entry_time = None

    # Pre-compile the user code to avoid parsing syntax tree in the loop
    try:
        compiled_code = compile(code_str, "<string>", "exec")
    except SyntaxError as e:
        raise RuntimeError(f"Syntax Error in your strategy: {e}")

    # Iterate candle by candle
    for idx in range(len(df)):
        row = df.iloc[idx]
        ts = row["time"] if "time" in row else row.get("timestamp")
        c_price = row["close"]

        # If in a position, check standard SL/TP first
        if in_position:
            pnl_pct = (c_price - entry_price) / entry_price
            hit_sl = pnl_pct <= -stop_loss_pct
            hit_tp = pnl_pct >= take_profit_pct

            if hit_sl or hit_tp:
                pnl = (c_price - entry_price) / entry_price
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": ts,
                    "entry_price": float(entry_price),
                    "exit_price": float(c_price),
                    "type": "BUY",
                    "pnl": float(pnl),
                    "reason": "SL" if hit_sl else "TP"
                })
                sell_signals.append({"time": ts, "price": float(c_price), "type": "SELL"})
                in_position = False
                continue

        # Prepare namespace
        # We define buy() and sell() callbacks for the user code to trigger signals
        _action = []

        def _buy():
            _action.append("buy")

        def _sell():
            _action.append("sell")

        local_env = {
            "open":   row.get("open", 0),
            "high":   row.get("high", 0),
            "low":    row.get("low", 0),
            "close":  c_price,
            "volume": row.get("volume", 0),
            "sma_fast": row.get("sma_fast", 0),
            "sma_slow": row.get("sma_slow", 0),
            "rsi":      row.get("rsi", 0),
            "bb_upper": row.get("bb_upper", 0),
            "bb_lower": row.get("bb_lower", 0),
            "bb_middle": row.get("bb_middle", 0),
            "buy": _buy,
            "sell": _sell,
        }

        # Handle nan gracefully so comparisons don't crash
        for k, v in local_env.items():
            if isinstance(v, float) and np.isnan(v):
                 local_env[k] = 0.0

        try:
             exec(compiled_code, {"__builtins__": None}, local_env)
        except Exception as e:
             raise RuntimeError(f"Execution Exception during strategy evaluation at {ts}: {e}")

        if "buy" in _action and not in_position:
            buy_signals.append({"time": ts, "price": float(c_price), "type": "BUY"})
            in_position = True
            entry_price = float(c_price)
            entry_time = ts

        elif "sell" in _action and in_position:
            pnl = (c_price - entry_price) / entry_price
            trades.append({
                "entry_time": entry_time,
                "exit_time": ts,
                "entry_price": float(entry_price),
                "exit_price": float(c_price),
                "type": "BUY",
                "pnl": float(pnl),
                "reason": "CODE_SELL"
            })
            sell_signals.append({"time": ts, "price": float(c_price), "type": "SELL"})
            in_position = False

    from backend.backtesting.metrics import compute_metrics
    
    # Return structure
    indicators = {
        "short_ma": [
            {"time": float(row.time), "value": float(row.sma_fast)}
            for _, row in df.iterrows() if not pd.isna(row.sma_fast)
        ],
        "long_ma": [
            {"time": float(row.time), "value": float(row.sma_slow)}
            for _, row in df.iterrows() if not pd.isna(row.sma_slow)
        ],
    }

    return {
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "trades": trades,
        "metrics": compute_metrics(trades),
        "indicators": indicators
    }
