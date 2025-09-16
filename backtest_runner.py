from bot.backtest import backtest, summarize_results
import pandas as pd
import os

DATA_DIR = "data"
results = []

for file in os.listdir(DATA_DIR):
    if file.startswith("FX_") and file.endswith(".csv"):
        file_path = os.path.join(DATA_DIR, file)
        print(f"Processing file: {file}")

        df = pd.read_csv(file_path)

        # Correct column names
        df.rename(columns={
            "time": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
        }, inplace=True)

        required_cols = {"open", "high", "low", "close", "timestamp"}
        if not required_cols.issubset(df.columns):
            print(f"⚠️ Skipping {file} because required OHLCV columns are missing.")
            continue

        trades_df = backtest(df, threshold=10)
        trades_df["symbol"] = file
        results.append(trades_df)

if results:
    final_results = pd.concat(results)
    final_results.to_csv("backtest_results.csv", index=False)
    print("✅ Backtest complete. Results saved to backtest_results.csv")

    summarize_results(final_results)
else:
    print("⚠️ No valid OHLCV data files found for backtesting.")
