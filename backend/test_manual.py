import sys
sys.path.append('.')
import pandas as pd
from backend.optimizer import run_optimization

df = pd.DataFrame({
    "time": ["2022-01-01", "2022-01-02", "2022-01-03"],
    "open": [100, 102, 108],
    "high": [105, 110, 115],
    "low": [95, 100, 105],
    "close": [102, 108, 110],
    "volume": [1000, 1200, 1500]
})

base_config = {
    "mode": "template",
    "strategy": "ma_crossover",
    "parameters": {"stop_loss": 0.02, "take_profit": 0.04}
}

param_ranges = {
    "short_ma": [5, 10],
    "long_ma": [20, 50]
}

res = run_optimization(df, base_config, param_ranges, n_trials=5)

print("Best Parameters:", res["best_parameters"])
print("Best Score:", res["best_score"])
print("History Length:", len(res["optimization_history"]))
