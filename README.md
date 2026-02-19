# Trading Bot (Locked Forex Strategy)

This repo is a minimal backtesting scaffold with a single execution pipeline:

`CSV -> Candle Series -> Strategy -> Trades -> Metrics`

This repo implements a **locked** 5-minute execution engine. The UI uploads a CSV and the backend executes trades using the internal engine.

## CLI backtest

- Configure `DATA_DIR` / `OUTPUT_DIR` in `.env` (optional)
- Run: `python backtest_runner.py`
- Outputs:
  - `output/trades.csv`
  - `output/metrics.json`

## Backend + UI (optional)

- Backend (FastAPI):
  - Install: `pip install -r backend/requirements.txt`
  - Run: `python -m uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000`
  - API:
    - `GET /health`
    - `POST /run-backtest` (multipart/form-data: `file`)
- UI (Vite/React):
  - Install: `cd trading-ui; npm install`
  - Run: `npm run dev`
