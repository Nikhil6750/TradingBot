import pandas as pd
import os

def main():
    trades_file = "backtest_results_trades.csv"
    if not os.path.exists(trades_file):
        print("No trades file found.")
        return

    try:
        df = pd.read_csv(trades_file)
        if df.empty:
            print("No trades to report.")
            return

        print("\n=== Performance Report ===")
        print(f"Total Trades: {len(df)}")
        wins = df[df["outcome"] == "WIN"]
        losses = df[df["outcome"] == "LOSS"]
        win_rate = len(wins) / len(df) * 100
        print(f"Win Rate: {win_rate:.2f}%")
        
        # Simple R calculation if not present
        if "net_r" not in df.columns:
             # This is a simplification. Ideally we'd use the same logic as backtest_runner
             pass 

    except Exception as e:
        print(f"Error generating report: {e}")

if __name__ == "__main__":
    main()
