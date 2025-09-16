import pandas as pd
import numpy as np
from bot.indicators import add_indicators
from bot.scoring import compute_score


def backtest(df, threshold=50, atr_mult=1.5, rr=2, max_bars=20):
    """
    Backtest strategy on given OHLCV dataframe with indicators.
    """
    trades = []

    # Ensure indicators and factors are present
    df = add_indicators(df.copy())

    for i in range(len(df) - max_bars):
        row = df.iloc[i]

        # Compute score/label/factors
        score, label, factors = compute_score(row)

        # Only trade if confidence meets threshold
        if score >= threshold:
            entry_price = row["close"]
            atr = row.get("ATR_14", None)

            if atr is None or pd.isna(atr) or atr == 0:
                continue

            if factors["direction"] == "BUY":
                sl = entry_price - atr * atr_mult
                tp = entry_price + atr * atr_mult * rr
            else:  # SELL
                sl = entry_price + atr * atr_mult
                tp = entry_price - atr * atr_mult * rr

            outcome, exit_price, bars_held = simulate_trade(
                df.iloc[i+1:i+max_bars],
                entry_price,
                sl,
                tp,
                factors["direction"]
            )

            trades.append({
                "entry_time": row.name,
                "direction": factors["direction"],
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "exit_price": exit_price,
                "outcome": outcome,
                "bars_held": bars_held,
                "score": score,
                "label": label
            })

    if trades:
        return pd.DataFrame(trades)
    else:
        return pd.DataFrame(columns=[
            "entry_time", "direction", "entry_price", "sl", "tp",
            "exit_price", "outcome", "bars_held", "score", "label"
        ])


def simulate_trade(future_df, entry, sl, tp, direction):
    """
    Simulate trade outcome by walking forward candle by candle.
    """
    for j, r in enumerate(future_df.itertuples(), 1):
        if direction == "BUY":
            if r.low <= sl:
                return "LOSS", sl, j
            if r.high >= tp:
                return "WIN", tp, j
        else:  
            if r.high >= sl:
                return "LOSS", sl, j
            if r.low <= tp:
                return "WIN", tp, j

    return "EXPIRED", future_df.iloc[-1].close, j


def summarize_results(results: pd.DataFrame):
    """
    Print performance summary from backtest results.
    """
    if results.empty:
        print("⚠️ No trades generated.")
        return

    total_trades = len(results)
    win_rate = (results["outcome"] == "WIN").mean() * 100
    loss_rate = (results["outcome"] == "LOSS").mean() * 100
    expired_rate = (results["outcome"] == "EXPIRED").mean() * 100

    print("\n📊 Backtest Summary")
    print("------------------------")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate    : {win_rate:.2f}%")
    print(f"Loss Rate   : {loss_rate:.2f}%")
    print(f"Expired     : {expired_rate:.2f}%")


