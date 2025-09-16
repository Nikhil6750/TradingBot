import pandas as pd
import os

def performance_report(results_file="data/results.csv"):
    if not os.path.isfile(results_file):
        print("❌ No results.csv found. Run main.py first.")
        return

    df = pd.read_csv(results_file)

    if "outcome" not in df.columns:
        print("❌ No outcome column found. Run outcome_runner.py first.")
        return

    total_trades = len(df)
    wins = (df["outcome"] == "WIN").sum()
    losses = (df["outcome"] == "LOSS").sum()
    expired = (df["outcome"] == "EXPIRED").sum()

    win_rate = (wins / total_trades * 100) if total_trades else 0
    loss_rate = (losses / total_trades * 100) if total_trades else 0
    expired_rate = (expired / total_trades * 100) if total_trades else 0

    # Very simple PnL model: +1 for win, -1 for loss, 0 for expired
    net_profit = wins - losses
    gross_profit = wins
    gross_loss = losses if losses > 0 else 1  # avoid /0
    profit_factor = gross_profit / gross_loss

    print("\n📊 Performance Report")
    print("------------------------")
    print(f"Total Trades : {total_trades}")
    print(f"Wins         : {wins} ({win_rate:.2f}%)")
    print(f"Losses       : {losses} ({loss_rate:.2f}%)")
    print(f"Expired      : {expired} ({expired_rate:.2f}%)")
    print(f"Net Profit   : {net_profit}")
    print(f"Profit Factor: {profit_factor:.2f}")

if __name__ == "__main__":
    performance_report()
