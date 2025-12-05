import pandas as pd
import matplotlib.pyplot as plt
import os

def main():
    trades_file = "backtest_results_trades.csv"
    if not os.path.exists(trades_file):
        print("No trades file found.")
        return

    try:
        df = pd.read_csv(trades_file)
        if df.empty:
            print("No trades to plot.")
            return

        # Calculate R per trade
        def calculate_r(row):
            if row["direction"] == "BUY":
                risk = row["entry_price"] - row["sl"]
                gain = row["exit_price"] - row["entry_price"]
            else:
                risk = row["sl"] - row["entry_price"]
                gain = row["entry_price"] - row["exit_price"]
            
            if risk == 0: return 0
            return gain / risk

        df["r"] = df.apply(calculate_r, axis=1)
        df["cumulative_r"] = df["r"].cumsum()

        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df["cumulative_r"], label="Equity Curve (R)")
        plt.title("Equity Curve")
        plt.xlabel("Trade #")
        plt.ylabel("Cumulative R")
        plt.legend()
        plt.grid(True)
        plt.savefig("equity_curve.png")
        print("Equity curve saved to equity_curve.png")

    except Exception as e:
        print(f"Error generating equity curve: {e}")

if __name__ == "__main__":
    main()
