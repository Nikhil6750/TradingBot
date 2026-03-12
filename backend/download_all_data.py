import time
from backend.data_providers.data_manager import data_manager

def main():
    print("========================================")
    print("  AlgoTradeX Automated Data Downloader")
    print("  Target: 10 Years Historical Candles")
    print("========================================")

    brokers = data_manager.get_brokers()
    for broker in brokers:
        print(f"\n[{broker.upper()} PROVIDER]")
        symbols = data_manager.get_symbols(broker)
        
        for sym in symbols:
            timeframes = data_manager.get_timeframes(sym)
            for tf in timeframes:
                print(f" > Fetching {sym} ({tf})... ", end="", flush=True)
                try:
                    # check if exists locally, if not, triggers downloader
                    path = data_manager.pull_market_data(sym, tf)
                    print(f"DONE -> Saved to {path}")
                except Exception as e:
                    print(f"FAILED -> {e}")
                
                # Small sleep to be polite to APIs
                time.sleep(2)

    print("\n[+] All requested historical data has been processed.")

if __name__ == "__main__":
    main()
