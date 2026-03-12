try:
    import ccxt
except ImportError:
    ccxt = None
import pandas as pd
import time

class BinanceDownloader:
    """Binance downloader for hourly/daily crypto data via CCXT."""
    def __init__(self):
        if ccxt is None:
            raise ImportError("ccxt module is not installed. Please install it to use BinanceDownloader.")
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })

    def download(self, symbol: str, timeframe: str = "1H") -> pd.DataFrame:
        tf_map = {"1H": "1h", "4H": "4h", "1D": "1d"}
        ccxt_tf = tf_map.get(timeframe.upper(), "1h")
        
        # Approximately 10 years ago
        ten_years_ago = pd.Timestamp.utcnow() - pd.Timedelta(days=3650)
        since = self.exchange.parse8601(str(ten_years_ago))
        
        all_ohlcv = []
        limit = 1000
        
        # Guard against infinite loops or excessive API calls (fetch up to latest)
        max_requests = 100  # 100k candles max (enough for 10 yrs 1H)
        req_count = 0
        
        while req_count < max_requests:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, ccxt_tf, since=since, limit=limit)
                if not ohlcv or len(ohlcv) == 0:
                    break
                
                # If the last fetched candle is the same as requested since, we might be stuck
                if len(all_ohlcv) > 0 and ohlcv[-1][0] == all_ohlcv[-1][0]:
                    break
                    
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                req_count += 1
            except Exception as e:
                print(f"BinanceDownloader error fetching {symbol}: {e}")
                break
                
        if not all_ohlcv:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime("%Y-%m-%d %H:%M")
        df.drop_duplicates(subset=['timestamp'], inplace=True)
        return df
