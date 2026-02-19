from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_loader import load_candles
from gap_handling import generate_trades_and_setups_with_gap_resets


def run_market(market, pair):
    print(f"\n=== Testing {market.upper()} : {pair} ===")

    try:
        candles = load_candles(market=market, pair=pair)
    except Exception as e:
        print("ERROR loading candles:", str(e))
        return

    print(f"Candles loaded: {len(candles)}")

    try:
        trades, setups = generate_trades_and_setups_with_gap_resets(candles)
    except Exception as e:
        print("ERROR running strategy:", str(e))
        return

    print(f"Setups found: {len(setups)}")
    print(f"Trades found: {len(trades)}")

    for i, t in enumerate(trades[:5], 1):
        print(f"\nTrade {i}:")
        print(" Direction:", t["direction"])
        print(" Entry:", t["entry"])
        print(" Exit:", t["exit"])
        print(" Target:", t["target"])


if __name__ == "__main__":
    run_market("forex", "EURUSD")
    run_market("crypto", "BINANCE_BTCUSDT")
