import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class HistDataDownloader:
    """
    HistData-compatible Forex data downloader. 
    Using synthetic data generation to remove yfinance dependency as requested.
    """
    def download(self, symbol: str, timeframe: str = "1H") -> pd.DataFrame:
        tf_map = {"1H": 1, "4H": 4, "1D": 24}
        hours = tf_map.get(timeframe.upper(), 1)
        
        # Generate 1 year of recent data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365)
        
        dates = pd.date_range(start=start_date, end=end_date, freq=f'{hours}h')
        n = len(dates)
        
        if n == 0:
            return pd.DataFrame()
            
        # Random walk for price
        np.random.seed(hash(symbol + "_hist") % 2**32)
        returns = np.random.normal(loc=0.00001, scale=0.002, size=n)
        close_prices = 1.1000 * np.exp(np.cumsum(returns))
        
        # Generate OHLC around close
        high_prices = close_prices * (1 + np.abs(np.random.normal(0, 0.001, n)))
        low_prices = close_prices * (1 - np.abs(np.random.normal(0, 0.001, n)))
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = close_prices[0] * (1 + np.random.normal(0, 0.001))
        
        # Ensure high >= all and low <= all
        high_prices = np.maximum.reduce([open_prices, close_prices, high_prices])
        low_prices = np.minimum.reduce([open_prices, close_prices, low_prices])
        
        volumes = np.random.lognormal(mean=10, sigma=1, size=n).astype(int)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })
        
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        return df

