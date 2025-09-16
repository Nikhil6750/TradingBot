import pandas as pd
import os


def load_data(file_path):
    df = pd.read_csv(file_path)
    # Convert UNIX timestamp → datetime (UTC)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def update_outcomes(results_file="data/results.csv", data_dir="data"):
    if not os.path.exists(results_file):
        raise FileNotFoundError(f"Results file not found: {results_file}")

    results = pd.read_csv(results_file)

    # Ensure required columns exist
    required_cols = ["file", "bar_time", "direction", "entry_price", "sl", "tp"]
    for col in required_cols:
        if col not in results.columns:
            raise ValueError(f"[ALERT] Missing column in results.csv: {col}")

    # Convert bar_time string → datetime
    results["bar_time"] = pd.to_datetime(
        results["bar_time"], utc=True, errors="coerce"
    )

    updated = []
    for idx, row in results.iterrows():
        pair_file = os.path.join(data_dir, row["file"])
        if not os.path.exists(pair_file):
            print(f"[WARN] Data file not found: {pair_file}")
            continue

        df = load_data(pair_file)

        entry_time = row["bar_time"]
        # Find entry candle (closest at or before bar_time)
        candle = df[df["time"] <= entry_time].tail(1)
        if candle.empty:
            print(f"[WARN] No matching candle for {row['file']} at {entry_time}")
            continue

        entry_idx = candle.index[0]
        max_bars = int(row.get("max_bars", 20))
        exit_slice = df.iloc[entry_idx : entry_idx + max_bars]

        outcome = "EXPIRED"
        for _, c in exit_slice.iterrows():
            if row["direction"] == "BUY":
                if c["low"] <= row["sl"]:
                    outcome = "LOSS"
                    break
                if c["high"] >= row["tp"]:
                    outcome = "WIN"
                    break
            else:  # SELL
                if c["high"] >= row["sl"]:
                    outcome = "LOSS"
                    break
                if c["low"] <= row["tp"]:
                    outcome = "WIN"
                    break

        results.at[idx, "outcome"] = outcome
        updated.append(outcome)

    results.to_csv(results_file, index=False)
    print(f"✅ Outcomes updated in {results_file}")
    if updated:
        print(pd.Series(updated).value_counts())


# Alias for backwards compatibility
def evaluate_outcomes(results_file="data/results.csv", data_dir="data"):
    return update_outcomes(results_file, data_dir)
