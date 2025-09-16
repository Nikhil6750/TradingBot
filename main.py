import os
import pandas as pd
from bot.scoring import compute_score
from bot.indicators import add_indicators

RESULTS_FILE = os.path.join("data", "results.csv")

# Ensure results.csv exists with proper columns
if not os.path.exists(RESULTS_FILE):
    pd.DataFrame(
        columns=["file", "bar_time", "direction", "entry_price", "sl", "tp", "max_bars", "outcome"]
    ).to_csv(RESULTS_FILE, index=False)


def log_signal(file, row, direction, entry_price, sl, tp, max_bars=20):
    results = pd.read_csv(RESULTS_FILE)

    # FIX: convert UNIX time → datetime properly
    if "time" in row:
        bar_time = pd.to_datetime(int(row["time"]), unit="s", utc=True)
    else:
        bar_time = pd.Timestamp.utcnow()

    new_row = {
        "file": file,
        "bar_time": bar_time,
        "direction": direction,
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "max_bars": max_bars,
        "outcome": "",
    }

    results = pd.concat([results, pd.DataFrame([new_row])], ignore_index=True)
    results.to_csv(RESULTS_FILE, index=False)


def run_signals():
    data_dir = "data"
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

    for file in files:
        df = pd.read_csv(os.path.join(data_dir, file))
        df = add_indicators(df)

        for _, row in df.tail(1).iterrows():  # just demo: check latest candle
            score, label, factors = compute_score(row)
            if label == "HIGH":
                direction = factors["direction"]
                entry = row["close"]
                sl = entry - 0.0010 if direction == "BUY" else entry + 0.0010
                tp = entry + 0.0020 if direction == "BUY" else entry - 0.0020
                log_signal(file, row, direction, entry, sl, tp)


if __name__ == "__main__":
    run_signals()
    print(f"Signals processed → results saved in {RESULTS_FILE}")
