try:
    import ccxt
except ImportError:
    ccxt = None
import pandas as pd
import time

class CoinbaseDownloader:
    """Coinbase downloader for crypto data via CCXT."""
    def __init__(self):
        if ccxt is None:
            raise ImportError("ccxt module is not installed. Please install it to use CoinbaseDownloader.")
        self.exchange = ccxt.coinbase({
            'enableRateLimit': True,
        })

    def download(self, symbol: str, timeframe: str = "1H") -> pd.DataFrame:
        # ccxt coinbase might require different symbols like BTC/USDT or BTC/USD
        # map common symbol to ccxt standard
        formatted_symbol = symbol.replace("USDT", "/USD").replace("USD", "/USD") 
        if formatted_symbol.endswith("//USD"):
            formatted_symbol = formatted_symbol.replace("//USD", "/USD")
            
        tf_map = {"1H": "1h", "4H": "4h", "1D": "1d"}
        ccxt_tf = tf_map.get(timeframe.upper(), "1h")
        
        # Approximately 5-10 years ago (Coinbase has less history for some pairs)
        ten_years_ago = pd.Timestamp.utcnow() - pd.Timedelta(days=3650)
        since = self.exchange.parse8601(str(ten_years_ago))
        
        all_ohlcv = []
        limit = 300 
        
        # Guard against infinite loops
        max_requests = 100
        req_count = 0
        
        while req_count < max_requests:
            try:
                ohlcv = self.exchange.fetch_ohlcv(formatted_symbol, ccxt_tf, since=since, limit=limit)
                if not ohlcv or len(ohlcv) == 0:
                    break
                    
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                req_count += 1
            except Exception as e:
                print(f"CoinbaseDownloader error fetching {symbol}: {e}")
                break
                
        if not all_ohlcv:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime("%Y-%m-%d %H:%M")
        df.drop_duplicates(subset=['timestamp'], inplace=True)
        return df
