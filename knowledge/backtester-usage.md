# Backtester Usage (Nikhil Reddy)

## Purpose
Validate strategies over historical data and summarize performance.

## Inputs (env vars / UI)
- SYMBOL_ALLOWLIST: e.g., EURJPY, XAUUSD, BTCUSD
- HOUR_ALLOW: e.g., 9-12,15-18
- SESSION: ALL or a specific session code
- RR: risk–reward target (e.g., 1.5)
- ATR_MULTIPLIER: stop sizing factor (e.g., 1.8)
- THRESHOLD: model/score cutoff (0–100)

## Outputs
- backtest_results.csv (overall metrics: trades, win_rate, profit_factor, avg_r, total_r)
- audit_by_symbol.csv
- audit_by_hour.csv

## Workflow
1) Choose symbol(s) and hours that match liquidity (London/NY).
2) Set RR and ATR_MULTIPLIER to control risk and stop distance.
3) Use THRESHOLD to filter low-quality signals.
4) Run the backtester, then examine audits by symbol and hour.
5) Iterate: adjust hours/threshold, re-run, compare PF and drawdown.

## Interpretation Tips
- Win rate × RR must exceed break-even.
- Profit factor > 1.3 is a minimum; >1.6 is solid.
- Concentration risk: if most edge is in 1–2 hours, treat schedule carefully.
