"""
data_manager.py
---------------
Loads uploaded CSV datasets and aggregates them into requested timeframes.
"""

from __future__ import annotations
import os
from pathlib import Path
from backend.market_data.csv_dataset_loader import TIMEFRAME_RULES, load_dataset_candles

# Supported timeframes and their pandas resample rules
TIMEFRAME_MAP = dict(TIMEFRAME_RULES)


class DataManager:
    def __init__(self, datasets_dir: str = "backend/datasets"):
        self.datasets_dir = Path(os.path.join(os.path.dirname(__file__), "..", "..", "datasets")).resolve()
        # Fallback if that path is wrong
        if not self.datasets_dir.exists():
            self.datasets_dir = Path("backend/datasets").resolve()
            
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def load_candles(self, arg1: str, arg2: str, arg3: str = "1h") -> list[dict]:
        """
        Backward compatibility for load_candles.
        Previously it was called as:
          load_candles(broker, symbol, timeframe) 
          or load_candles(symbol, timeframe)
          
        Now we expect:
          load_candles(dataset_id, timeframe)
          or load_candles(broker, dataset_id, timeframe)
        """
        # Determine which arg is the dataset_id (usually the first or second)
        dataset_id = arg1
        timeframe = arg2
        
        # If arg1 is a broker name or empty, dataset_id is likely arg2
        if arg1.lower() in ["oanda", "dukascopy", "fxcm", "binance", "coinbase", "yahoo"] or not arg1:
            dataset_id = arg2
            timeframe = arg3

        try:
            return load_dataset_candles(dataset_id, self.datasets_dir, timeframe=timeframe or "1m")
        except FileNotFoundError:
            alternate_dataset_id = arg2
            if alternate_dataset_id and alternate_dataset_id != dataset_id:
                return load_dataset_candles(alternate_dataset_id, self.datasets_dir, timeframe=arg3 or timeframe or "1m")
            else:
                raise


# ── Singleton ─────────────────────────────────────────────────────────────────
data_manager = DataManager()
