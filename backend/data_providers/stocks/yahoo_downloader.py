try:
    import yfinance as yf
except ImportError:
    yf = None
import pandas as pd

class YahooDownloader:
    """Yahoo Finance downloader for daily stock data."""
    def download(self, symbol: str, timeframe: str = "1D") -> pd.DataFrame:
        if yf is None:
            raise ImportError("yfinance module is not installed. Please install it to use YahooDownloader.")
        yf_tf = "1d"
        ticker = yf.Ticker(symbol)
        
        # Max history for 1d is 'max', we request '10y'
        df = ticker.history(period="10y", interval=yf_tf)
        if df.empty:
            return pd.DataFrame()
        
        df = df.reset_index()
        
        # Different yfinance version might return 'Date' or 'Datetime'
        if "Date" in df.columns:
            df.rename(columns={"Date": "timestamp"}, inplace=True)
        elif "Datetime" in df.columns:
            df.rename(columns={"Datetime": "timestamp"}, inplace=True)

        df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)
        
        # Handle timezone
        if df["timestamp"].dt.tz is not None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(None)
            
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        
        # Select and enforce schema
        cols = ["timestamp", "open", "high", "low", "close", "volume"]
        missing = [c for c in cols if c not in df.columns]
        for m in missing:
            df[m] = 0
            
        return df[cols]
