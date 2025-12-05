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
            print("No trades to audit.")
            return
            
        # Ensure timestamp is datetime
        if "entry_time" in df.columns:
            df["entry_time"] = pd.to_datetime(df["entry_time"])
            df["hour"] = df["entry_time"].dt.hour

            # Audit by Symbol
            by_symbol = df.groupby("symbol").apply(
                lambda x: pd.Series({
                    "trades": len(x),
                    "win_rate_%": (x["outcome"] == "WIN").mean() * 100,
                    "pf": (x[x["outcome"]=="WIN"]["exit_price"].sum() / x[x["outcome"]=="LOSS"]["exit_price"].sum()) if (x["outcome"]=="LOSS").sum() > 0 else float("inf"), # Very rough PF approximation
                     # Better PF: Gross Win R / Gross Loss R
                })
            ).reset_index()
            by_symbol.to_csv("audit_by_symbol.csv", index=False)

            # Audit by Hour
            by_hour = df.groupby("hour").apply(
                lambda x: pd.Series({
                    "trades": len(x),
                    "win_rate_%": (x["outcome"] == "WIN").mean() * 100,
                })
            ).reset_index()
            by_hour.to_csv("audit_by_hour.csv", index=False)
            
            print("Audit files saved.")

    except Exception as e:
        print(f"Error generating audit insights: {e}")

if __name__ == "__main__":
    main()
