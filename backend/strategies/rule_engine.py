import pandas as pd
import numpy as np
import re

def compute_indicator(df: pd.DataFrame, indicator: str, params: dict):
    """Dynamically computes an indicator based on its name and injects it into the dataframe"""
    indicator = indicator.lower()
    
    if indicator == "rsi":
        period = int(params.get("period", 14))
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        
    elif indicator == "ma" or indicator == "sma":
        period = int(params.get("period", 50))
        df[f"sma_{period}"] = df["close"].rolling(window=period).mean()
        
    elif indicator == "ema":
        period = int(params.get("period", 200))
        df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()

def evaluate_condition(df: pd.DataFrame, condition: dict) -> pd.Series:
    """Evaluates a single condition like {'indicator': 'RSI', 'operator': '<', 'value': 30}"""
    ind = condition.get("indicator", "").lower()
    op = condition.get("operator", "")
    val = condition.get("value")
    
    # Map indicator aliases to dataframe columns (e.g. Price -> close)
    if ind == "price":
        ind = "close"
    
    # The value might be a static number or another indicator (e.g. "EMA200")
    if isinstance(val, str) and not val.replace('.', '', 1).isdigit():
        val = val.lower()
        if val == "price":
            val = "close"
        rhs = df[val]
    else:
        rhs = float(val)
        
    lhs = df[ind]
    
    if op == ">": return lhs > rhs
    if op == "<": return lhs < rhs
    if op == ">=": return lhs >= rhs
    if op == "<=": return lhs <= rhs
    if op == "==": return lhs == rhs
    return pd.Series(False, index=df.index)

def run_rule_engine(df: pd.DataFrame, config: dict) -> dict:
    """Runs a fully custom strategy based on user-defined indicators and rules"""
    
    # 1. Compute required indicators
    indicators = config.get("indicators", {})
    for ind, params in indicators.items():
        compute_indicator(df, ind, params)
        
    # Also support Mode 3 implicit indicator calculation if missed in 'indicators' dict
    # We heuristically parse strings like "EMA200" from rules
    def ensure_indicator_exists(name):
        name = str(name).lower()
        if name == "price" or name == "close": return
        if name in df.columns: return
        match = re.match(r"(ema|sma|ma)(\d+)", name)
        if match:
            ind_type, period = match.groups()
            compute_indicator(df, ind_type, {"period": int(period)})
            # Copy to raw name to match exactly
            df[name] = df[f"{ind_type}_{period}"]
        elif name == "rsi":
            compute_indicator(df, "rsi", {"period": 14})
            
    # 2. Parse and evaluate buy/sell rules
    buy_rules = config.get("buy_rules", [])
    sell_rules = config.get("sell_rules", [])
    
    for r in buy_rules:
        ensure_indicator_exists(r.get("indicator"))
        ensure_indicator_exists(r.get("value"))
        
    for r in sell_rules:
        ensure_indicator_exists(r.get("indicator"))
        ensure_indicator_exists(r.get("value"))

    # Initial condition arrays
    buy_cond = pd.Series(True, index=df.index)
    sell_cond = pd.Series(True, index=df.index)
    
    if not buy_rules: buy_cond = pd.Series(False, index=df.index)
    if not sell_rules: sell_cond = pd.Series(False, index=df.index)

    # AND logic for multiple rules
    for rule in buy_rules:
        buy_cond = buy_cond & evaluate_condition(df, rule)
        
    for rule in sell_rules:
        sell_cond = sell_cond & evaluate_condition(df, rule)
        
    # Generate signals
    buy_signals = []
    sell_signals = []
    trades = []
    
    stop_loss = float(config.get("stop_loss", 0.02))
    take_profit = float(config.get("take_profit", 0.04))
    
    in_trade = False
    entry_price = 0.0
    trade_type = ""

    for i in range(1, len(df)):
        current = df.iloc[i]
        
        if in_trade:
            pl_pct = (current["close"] - entry_price) / entry_price
            if trade_type == "BUY" and (pl_pct <= -stop_loss or pl_pct >= take_profit):
                in_trade = False
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": current["close"],
                    "type": "BUY",
                    "pnl": pl_pct,
                    "exit_time": current["time"]
                })
            elif trade_type == "SELL" and (-pl_pct <= -stop_loss or -pl_pct >= take_profit):
                in_trade = False
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": current["close"],
                    "type": "SELL",
                    "pnl": -pl_pct,
                    "exit_time": current["time"]
                })
                
        # Only enter new trades if we are flat
        if not in_trade:
            if buy_cond.iloc[i]:
                buy_signals.append({"time": current["time"], "price": current["close"]})
                in_trade = True
                entry_price = current["close"]
                trade_type = "BUY"
            elif sell_cond.iloc[i]:
                sell_signals.append({"time": current["time"], "price": current["close"]})
                in_trade = True
                entry_price = current["close"]
                trade_type = "SELL"
                
    # Calculate metrics
    wins = [t for t in trades if t["pnl"] > 0]
    win_rate = len(wins) / len(trades) if trades else 0.0
    total_return = sum(t["pnl"] for t in trades)
    
    return {
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "trades": trades,
        "metrics": {
            "win_rate": round(win_rate, 4),
            "total_return": round(total_return, 4),
            "max_drawdown": 0.0
        }
    }
