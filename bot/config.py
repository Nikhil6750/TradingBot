# bot/config.py
import os, sys

def need_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[CONFIG ERROR] Missing environment variable: {name}")
        sys.exit(1)
    return val

TELEGRAM_BOT_TOKEN = need_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = need_env("TELEGRAM_CHAT_ID")

CONFIDENCE_THRESHOLD = int(os.getenv("CONFIDENCE_THRESHOLD", "70"))
ATR_MULT = float(os.getenv("ATR_MULT", "1.5"))
RR = float(os.getenv("RR", "2.0"))

DATA_DIR = os.getenv("DATA_DIR", "data")
RESULTS_PATH = os.getenv("RESULTS_PATH", "results.csv")
MAX_BARS_TO_RESOLVE = int(os.getenv("MAX_BARS_TO_RESOLVE", "20"))
