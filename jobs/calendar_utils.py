# jobs/calendar_utils.py

import pandas as pd
from datetime import datetime
from dateutil import tz

def make_telegram_summary(df: pd.DataFrame, local_tz: str) -> str:
    if df is None or df.empty:
        return "🗞️ No upcoming high/medium impact events in the selected window."
    lines = ["🗞️ **Upcoming Economic Events**"]
    for r in df.itertuples(index=False):
        if r.time_utc:
            tu = datetime.fromisoformat(str(r.time_utc).replace("Z","+00:00")).astimezone(tz.gettz(local_tz))
            tdisp = tu.strftime("%H:%M")
        else:
            tdisp = r.time_local or "-"
        imp = (r.impact or "").capitalize()
        row = f"{tdisp} {r.currency or ''} [{imp}] — {r.event}"
        if r.forecast: row += f" | Fcst: {r.forecast}"
        if r.actual:   row += f" | Actual: {r.actual}"
        lines.append(row)
    return "\n".join(lines)
