# jobs/fetch_investing_calendar.py
from pathlib import Path
import argparse
import pandas as pd
from calendar_utils import fetch_investing_calendar
import sys
sys.stdout.reconfigure(encoding="utf-8")

TAB_MAP = {
    "today": "today",
    "tomorrow": "tomorrow",
    "yesterday": "yesterday",
    "thisweek": "thisWeek",
    "nextweek": "nextWeek",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tab", default="today", help="today|tomorrow|yesterday|thisweek|nextweek")
    ap.add_argument("--tz", default="-4", help="website GMT offset hours, e.g. -4, -5, 0, 5.5")
    ap.add_argument("--out", default="data/investing_calendar_today.csv")
    args = ap.parse_args()

    tab = TAB_MAP.get(args.tab.lower(), "today")
    df = fetch_investing_calendar(current_tab=tab, tz_offset=str(args.tz))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows → {args.out}")

if __name__ == "__main__":
    main()
