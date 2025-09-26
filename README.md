📈 Strategy Backtester Bot
🔹 What is this project?

The Strategy Backtester Bot is a Python-based framework to test and analyze trading strategies on historical market data.
It helps traders and researchers validate ideas, optimize parameters, and generate insights before risking real capital.

It is designed with:

Python scripts for backtesting, reporting, and automation

Streamlit UI for interactive exploration

Telegram integration for notifications and summaries

🔹 Why use it?

Avoid relying only on gut-feel or charts — backtest strategies with data.

Compare multiple strategies, symbols, and time sessions quickly.

Understand win-rate, profit factor, expectancy, and drawdowns before trading.

Automate reporting and receive updates directly on Telegram.

Extendable — can connect to TradingView alerts and real-time trading later.

🔹 Key Features

Backtest Runner (backtest_runner.py)
Runs deterministic bar-by-bar simulations on CSV market data. Outputs:

Per-trade results

Audit logs

Summary metrics (Win%, PF, Net R, etc.)

Parameter Sweep & Grid Search

parameter_grid_search.py / parameter_grid_search_all.py → test multiple thresholds, ATR multipliers, and RR ratios.

sweep_quick.py → run quick parameter sweeps and output best settings.

Performance Reports

performance_report.py → trade-level statistics.

equity_curve.py → equity curve, drawdown, Sharpe.

audit_insights.py → symbol-wise and hour-wise insights.

audit_oos.py → train/test split performance.

Streamlit UI (app.py)

Simple dashboard to configure parameters and run backtests.

Displays audit by symbol/hour, trade results, equity curve.

Free-text queries like “Can I take EURJPY now?” are parsed into backtests.

Automation

run_loop.py → orchestration script to run backtests + reports in sequence.

alert.py → lightweight Telegram integration for push alerts.

outcome_runner.py / outcome_tracker.py → resolve trade outcomes over time.

Helpers & Indicators

helpers.py → session parsing, trade summarization, CSV reading.

indicators.py / scoring.py → EMA, RSI, ATR, and scoring logic.

logger.py → structured result logging.

🔹 How to Use
1. Clone the repo
git clone https://github.com/your-username/strategy-backtester-bot.git
cd strategy-backtester-bot

2. Install dependencies
pip install -r requirements.txt

3. Prepare data

Place your OHLC CSVs inside the data/ folder.
Example CSV must have at least:

time, open, high, low, close

4. Run a backtest
python backtest_runner.py

5. Run reports
python performance_report.py
python equity_curve.py
python audit_insights.py

6. Use the Streamlit UI
streamlit run app.py


Adjust parameters via sidebar.

Ask natural language queries like:

“Can I take GBPUSD in 15-18?”

“Show EURJPY results now”

7. Enable Telegram alerts (optional)

Set environment variables:

set TELEGRAM_BOT_TOKEN=your_bot_token
set TELEGRAM_CHAT_ID=your_chat_id


Run:

python run_loop.py

🔹 Future Integrations

🔜 TradingView Webhook Integration → Run live strategy tests based on TradingView alerts.

🔜 Stock & Crypto Analysis (with news sentiment).

🔜 Indian Market Support → NSE/BSE swing/range calculations.

🔜 Dashboard Enhancements → interactive charts, trade drill-downs.

🔜 Cloud Deployment → deploy on AWS/GCP for 24x7 automation.

🔜 Live Trading Bridge → connect validated strategies to broker APIs.

🔹 Why this project matters

Backtesting is the backbone of systematic trading. This bot gives you:
✔️ Transparency — know how strategies perform.
✔️ Flexibility — test any parameters, symbols, or sessions.
✔️ Scalability — extend from backtesting to real-time automation.
✔️ Confidence — make trading decisions backed by data.

⚠️ Disclaimer: This project is for research & educational purposes only.
It is NOT financial advice and should not be used for live trading without further risk management.