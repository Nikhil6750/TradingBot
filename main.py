# main.py
import os
from helpers import get_env_str

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    print("[CONFIG ERROR] Missing environment variable: TELEGRAM_BOT_TOKEN")
else:
    print("Telegram bot ready (token present).")

print("Run the pipeline like:\n"
      "  python backtest_runner.py\n"
      "  python parameter_grid_search_all.py\n"
      "  python analyze_bt.py\n"
      "  python performance_report.py\n")
