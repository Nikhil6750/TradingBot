import glob
import json
import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from bot.backtest import candles_from_dataframe, compute_metrics, run_backtest, trades_to_frame
from bot.locked_strategy import LockedStreakPullbackStrategy

load_dotenv()


def main() -> None:
    data_dir = os.getenv("DATA_DIR", "data")
    output_dir = os.getenv("OUTPUT_DIR", "output")
    os.makedirs(output_dir, exist_ok=True)

    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))

    all_trade_frames: list[pd.DataFrame] = []
    per_symbol: dict[str, Any] = {}

    for csv_file in csv_files:
        base = os.path.splitext(os.path.basename(csv_file))[0].upper()
        symbol = base.replace("_5M", "") if base.endswith("_5M") else base
        df = pd.read_csv(csv_file)
        candles = candles_from_dataframe(df, tz_name="UTC")
        trades = run_backtest(candles, strategy=LockedStreakPullbackStrategy(allow_long=True, allow_short=True))
        all_trade_frames.append(trades_to_frame(trades, symbol=symbol))
        per_symbol[symbol] = compute_metrics(trades)

    trades_out = (
        pd.concat(all_trade_frames, ignore_index=True)
        if all_trade_frames
        else trades_to_frame([], symbol=None)
    )
    trades_out.to_csv(os.path.join(output_dir, "trades.csv"), index=False)

    metrics_out = {"symbols": per_symbol}
    with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
