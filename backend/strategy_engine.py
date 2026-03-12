import pandas as pd
from typing import Dict, Any

from backend.strategies.ma_crossover import run_ma_crossover
from backend.strategies.mean_reversion import run_mean_reversion
from backend.strategies.rsi_reversal import run_rsi_reversal
from backend.strategies.breakout import run_breakout
from backend.strategies.rule_engine import run_rule_engine
from backend.strategies.code_strategy import run_code_strategy
from backend.strategies.pine_script_strategy import run_pine_script_strategy

def run_strategy(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Central strategy router.
    Expects config format:
    {
       "mode": "template" | "parameter" | "rules" | "code" | "pine",
       "strategy": "ma_crossover" | "mean_reversion" | "rsi_reversal" | "breakout",
       "parameters": {...},  # for templates
       "indicators": {...},  # for parameter mode
       "buy_rules": [...],   # for rule mode
       "sell_rules": [...],  # for rule mode
       "stop_loss": 0.02,
       "take_profit": 0.04
    }
    """
    mode = config.get("mode", "template")

    # Minimal Strategy Lab path:
    # allow direct Moving Average Crossover evaluation without the broader template system.
    if config.get("strategy") == "ma_crossover" and "parameters" in config:
        return run_ma_crossover(df, config.get("parameters", {}))
    
    if mode == "template":
        strategy_name = config.get("strategy")
        params = config.get("parameters", {})
        
        # Merge global stops into params if not present
        if "stop_loss" in config and "stop_loss" not in params:
            params["stop_loss"] = config["stop_loss"]
        if "take_profit" in config and "take_profit" not in params:
            params["take_profit"] = config["take_profit"]

        if strategy_name == "ma_crossover":
            return run_ma_crossover(df, params)
        elif strategy_name == "mean_reversion":
            return run_mean_reversion(df, params)
        elif strategy_name == "rsi_reversal":
            return run_rsi_reversal(df, params)
        elif strategy_name == "breakout":
            return run_breakout(df, params)
        else:
            raise ValueError(f"Unknown template strategy: {strategy_name}")
            
    elif mode == "parameter":
        # Parameter mode sends string rules like "rsi < 30 AND close > ma".
        # We need to parse that string into JSON rules for the rule_engine to consume.
        # Alternatively, we convert the string logic into buy_rules and sell_rules here.
        # Let's write a simple string parser to JSON rule objects, or assume the frontend 
        # sends it already as JSON buy_rules depending on the implementation.
        # Based on instructions, Mode 2 sends string keys, Mode 3 sends array of objects.
        
        # Convert string rules to JSON rules structure
        def parse_rule_string(rule_str: str) -> list:
            if not rule_str: return []
            conditions = rule_str.split(" AND ")
            rules = []
            for cond in conditions:
                parts = cond.strip().split(" ")
                if len(parts) == 3:
                    rules.append({
                        "indicator": parts[0],
                        "operator": parts[1],
                        "value": parts[2]
                    })
            return rules
            
        string_rules = config.get("rules", {})
        config["buy_rules"] = parse_rule_string(string_rules.get("buy", ""))
        config["sell_rules"] = parse_rule_string(string_rules.get("sell", ""))
        
        return run_rule_engine(df, config)
        
    elif mode == "rules":
        return run_rule_engine(df, config)
        
    elif mode == "code":
        return run_code_strategy(df, config)
    elif mode == "pine":
        return run_pine_script_strategy(df, config)

    else:
        raise ValueError(f"Unknown strategy mode: {mode}")
