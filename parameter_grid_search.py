from bot.backtest import backtest, summarize_results
import pandas as pd

# Load one sample data file
df = pd.read_csv("data/FX_EURJPY, 5_abeeb.csv")

# Fix column names
df.rename(columns={
    "time": "timestamp",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
}, inplace=True)

# Define grid of parameters to test
thresholds = [10, 30, 50, 70]
atr_multipliers = [1.5, 2.0, 2.5]

# Store results
grid_results = []

for threshold in thresholds:
    for atr_mult in atr_multipliers:
        print(f"Testing threshold={threshold}, atr_mult={atr_mult}")

        trades_df = backtest(df, threshold=threshold, atr_mult=atr_mult)

        total_trades = len(trades_df)
        win_rate = (trades_df['outcome'] == 'WIN').mean() * 100 if total_trades else 0
        avg_rr = ((trades_df['exit_price'] - trades_df['entry_price']).abs() / (trades_df['entry_price'] - trades_df['sl']).abs()).mean() if total_trades else 0

        grid_results.append({
            "threshold": threshold,
            "atr_multiplier": atr_mult,
            "total_trades": total_trades,
            "win_rate (%)": round(win_rate, 2),
            "avg_rr": round(avg_rr, 2)
        })

# Save grid search results to CSV
grid_df = pd.DataFrame(grid_results)
grid_df.to_csv("parameter_grid_search_results.csv", index=False)
print("\n✅ Grid search complete. Results saved to parameter_grid_search_results.csv")
