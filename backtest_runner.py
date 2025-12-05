import os
import sys
import glob
import pandas as pd
from dotenv import load_dotenv
from bot.backtest import backtest

load_dotenv()

def main():
    data_dir = os.getenv("DATA_DIR", "data")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Parameters
    threshold = float(os.getenv("THRESHOLD", "50"))
    atr_mult = float(os.getenv("ATR_MULTIPLIER", "2.0"))
    rr = float(os.getenv("RR", "2.0"))
    session_str = os.getenv("HOUR_ALLOW", "")
    session_filter = None
    if session_str and "-" in session_str:
        try:
            start, end = map(int, session_str.split("-"))
            session_filter = (start, end)
        except ValueError:
            pass
    
    tz_offset = float(os.getenv("TZ_OFFSET_HOURS", "0.0"))
    symbol_allow = os.getenv("SYMBOL_ALLOWLIST", "")
    allowed_symbols = [s.strip().upper() for s in symbol_allow.split(",")] if symbol_allow else []

    all_trades = []

    # Find CSVs
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {data_dir}")
        # Create dummy data if requested or just exit
        if os.getenv("AUTO_SYNTHETIC_WHEN_EMPTY", "0") == "1":
             print("Generating synthetic data...")
             # TODO: Implement synthetic data generation if needed
        return

    for csv_file in csv_files:
        symbol = os.path.splitext(os.path.basename(csv_file))[0].upper()
        if allowed_symbols and symbol not in allowed_symbols:
            continue
            
        print(f"Processing {symbol}...")
        try:
            df = pd.read_csv(csv_file)
            trades = backtest(
                df, 
                threshold=threshold, 
                atr_mult=atr_mult, 
                rr=rr, 
                session_filter=session_filter,
                tz_offset_hours=tz_offset
            )
            if not trades.empty:
                trades["symbol"] = symbol
                all_trades.append(trades)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    if all_trades:
        all_trades_df = pd.concat(all_trades, ignore_index=True)
        all_trades_df.to_csv("backtest_results_trades.csv", index=False)
        
        # Create summary
        summary = all_trades_df.groupby("symbol").apply(
            lambda x: pd.Series({
                "trades": len(x),
                "wins": (x["outcome"] == "WIN").sum(),
                "losses": (x["outcome"] == "LOSS").sum(),
                "win_rate_%": (x["outcome"] == "WIN").mean() * 100,
                "net_r": (x.apply(lambda r: (r["exit_price"] - r["entry_price"]) / (r["entry_price"] - r["sl"]) if r["direction"] == "BUY" else (r["entry_price"] - r["exit_price"]) / (r["sl"] - r["entry_price"]), axis=1)).sum()
            })
        ).reset_index()
        summary.to_csv("backtest_results.csv", index=False)
        print("Backtest complete. Results saved.")
    else:
        print("No trades found.")
        # Create empty files to satisfy other scripts
        pd.DataFrame(columns=["entry_time","exit_time","entry_price","exit_price","direction","sl","tp","outcome","symbol"]).to_csv("backtest_results_trades.csv", index=False)
        pd.DataFrame(columns=["symbol","trades","wins","losses","win_rate_%","net_r"]).to_csv("backtest_results.csv", index=False)

if __name__ == "__main__":
    main()
