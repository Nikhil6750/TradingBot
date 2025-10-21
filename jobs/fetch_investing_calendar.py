#!/usr/bin/env python3
# jobs/fetch_investing_calendar.py
# Simple Investing.com Economic Calendar scraper using requests + BeautifulSoup.

import os, re, time, argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

import requests
import pandas as pd
from bs4 import BeautifulSoup
from dateutil import tz

NEWS_OUTPUT_DIR    = os.getenv("NEWS_OUTPUT_DIR", "data/calendar")
NEWS_TZ            = os.getenv("NEWS_TZ", "Asia/Kolkata")
NEWS_CURRENCIES    = os.getenv("NEWS_CURRENCIES", "")
NEWS_MIN_IMPACT    = os.getenv("NEWS_MIN_IMPACT", "low")   # low|medium|high
NEWS_LOOKAHEAD_HRS = int(float(os.getenv("NEWS_LOOKAHEAD_HRS", "24")))

URL_DESKTOP = "https://www.investing.com/economic-calendar/"
URL_MOBILE  = "https://m.investing.com/economic-calendar/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.8",
}

_IMPACT_ORDER = {"low": 1, "medium": 2, "high": 3}

def _req(url: str, tries: int = 3, timeout: int = 30) -> str:
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and len(r.text) > 10000:
                return r.text
            last = f"HTTP {r.status_code} len={len(r.text)}"
        except Exception as e:
            last = str(e)
        time.sleep(1.0 * (k + 1))
    raise RuntimeError(f"GET failed for {url}: {last}")

def _normalize_impact(text: str) -> str:
    t = (text or "").strip().lower()
    # Investing often shows "Holiday" or star/bull icons rendered as text; fall back to heuristics.
    if "high" in t: return "high"
    if "medium" in t: return "medium"
    if "low" in t: return "low"
    if "holiday" in t: return "low"
    # Sometimes the column is empty → treat as low
    return "low"

def _to_utc(date_local: datetime, time_str: str, local_tz: str) -> Optional[datetime]:
    s = (time_str or "").strip().lower()
    if not s or s in {"all day", "all-day", "tentative"}:
        return None
    # ignore countdown like "16 min"
    if re.match(r"^\d+\s*(min|mins|minute|minutes)$", s):
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    local_zone = tz.gettz(local_tz)
    dt_local = date_local.replace(hour=hh, minute=mm, second=0, microsecond=0, tzinfo=local_zone)
    return dt_local.astimezone(tz.UTC)

# -------- parsers ----------

def _parse_desktop(html: str, date_str: str, local_tz: str) -> pd.DataFrame:
    """
    Desktop page has a big HTML table. We’ll read the first <table> with 7+ columns:
      Time | Cur. | Imp. | Event | Actual | Forecast | Previous
    """
    soup = BeautifulSoup(html, "html.parser")
    # find the main calendar table by scanning for a thead with those headings
    target = None
    for tbl in soup.select("table"):
        ths = [th.get_text(strip=True).lower() for th in tbl.select("thead th")]
        if not ths:  # some tables don’t have thead
            continue
        wanted = ["time", "cur.", "imp.", "event", "actual", "forecast", "previous"]
        hit = sum(int(any(w in th for th in ths)) for w in wanted)
        if hit >= 5:  # reasonably confident
            target = tbl
            break
    if not target:
        return pd.DataFrame()

    rows = target.select("tbody tr")
    if not rows:
        return pd.DataFrame()

    recs = []
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue
        time_txt   = tds[0].get_text(strip=True)
        cur_txt    = tds[1].get_text(strip=True).upper()
        impact_txt = tds[2].get_text(strip=True)
        event_txt  = tds[3].get_text(" ", strip=True)
        actual_txt = tds[4].get_text(strip=True)
        fcst_txt   = tds[5].get_text(strip=True)
        prev_txt   = tds[6].get_text(strip=True)
        if not event_txt:
            continue

        impact = _normalize_impact(impact_txt)
        utc_dt = _to_utc(date_obj, time_txt, local_tz)
        recs.append({
            "date": date_str,
            "time_local": time_txt or None,
            "time_utc": utc_dt.isoformat() if utc_dt else None,
            "currency": cur_txt or None,
            "impact": impact,
            "event": event_txt or None,
            "actual": actual_txt or None,
            "forecast": fcst_txt or None,
            "previous": prev_txt or None,
            "source": "investing",
        })
    return pd.DataFrame.from_records(recs)

def _parse_mobile(html: str, date_str: str, local_tz: str) -> pd.DataFrame:
    """
    Mobile page is simpler; same columns present in a responsive table.
    """
    soup = BeautifulSoup(html, "html.parser")
    # On mobile, rows are in <table> … try the first table with 6-7 columns
    target = None
    for tbl in soup.select("table"):
        ths = [th.get_text(strip=True).lower() for th in tbl.select("thead th")]
        if ths and ("event" in " ".join(ths)) and ("time" in " ".join(ths)):
            target = tbl
            break
    if not target:
        # fallback: pick the largest table
        tables = soup.select("table")
        if tables:
            target = max(tables, key=lambda t: len(t.select("tr")))
        else:
            return pd.DataFrame()

    rows = target.select("tbody tr")
    if not rows:
        return pd.DataFrame()

    recs = []
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 6:   # some mobile layouts combine columns
            continue
        # try to map by header order heuristics
        vals = [td.get_text(" ", strip=True) for td in tds]
        # Heuristic assignment
        time_txt, cur_txt, impact_txt, event_txt = vals[0], vals[1], vals[2], vals[3]
        actual_txt = vals[4] if len(vals) > 4 else ""
        fcst_txt   = vals[5] if len(vals) > 5 else ""
        prev_txt   = vals[6] if len(vals) > 6 else ""

        cur_txt = (cur_txt or "").upper()
        if not event_txt:
            continue

        impact = _normalize_impact(impact_txt)
        utc_dt = _to_utc(date_obj, time_txt, local_tz)
        recs.append({
            "date": date_str,
            "time_local": time_txt or None,
            "time_utc": utc_dt.isoformat() if utc_dt else None,
            "currency": cur_txt or None,
            "impact": impact,
            "event": event_txt or None,
            "actual": actual_txt or None,
            "forecast": fcst_txt or None,
            "previous": prev_txt or None,
            "source": "investing",
        })
    return pd.DataFrame.from_records(recs)

# -------- public API ----------

def fetch_investing_calendar(date_str: str, local_tz: str = NEWS_TZ) -> pd.DataFrame:
    """
    1) Try desktop HTML (SSR often available).
    2) If no rows found, fall back to the mobile page which is usually simpler/SSR.
    """
    html = _req(URL_DESKTOP)
    df = _parse_desktop(html, date_str, local_tz)
    if df is not None and not df.empty:
        return df.reset_index(drop=True)

    # fallback to mobile
    html_m = _req(URL_MOBILE)
    df2 = _parse_mobile(html_m, date_str, local_tz)
    return df2.reset_index(drop=True) if df2 is not None else pd.DataFrame()

def _within_lookahead(utc_iso: Optional[str], lookahead_hrs: int, local_tz: str, row_date: str) -> bool:
    now_local = datetime.now(tz.gettz(local_tz))
    until_local = now_local + timedelta(hours=int(lookahead_hrs))
    if not utc_iso:
        return row_date == now_local.date().strftime("%Y-%m-%d")
    try:
        tu = datetime.fromisoformat(utc_iso.replace("Z","+00:00")).astimezone(tz.gettz(local_tz))
        return now_local <= tu <= until_local
    except Exception:
        return False

def filter_events(df: pd.DataFrame,
                  currencies: Optional[List[str]] = None,
                  min_impact: str = "low",
                  lookahead_hours: int = 24,
                  local_tz: str = NEWS_TZ) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    if currencies:
        ccys = [c.strip().upper() for c in currencies if c.strip()]
        out = out[out["currency"].isin(ccys)]
    out["impact"] = out["impact"].map(lambda x: (x or "").lower())
    out = out[out["impact"].map(lambda x: _IMPACT_ORDER.get(x, 1) >= _IMPACT_ORDER.get(min_impact, 1))]
    out = out[out.apply(lambda r: _within_lookahead(r.get("time_utc"), lookahead_hours, local_tz, r.get("date")), axis=1)]
    out = out.sort_values(by=["time_utc","impact"], ascending=[True, False]).reset_index(drop=True)
    return out

def save_csv(df: pd.DataFrame, date_str: str, out_dir: str = NEWS_OUTPUT_DIR) -> Path:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    out = p / f"{date_str}.csv"
    df.to_csv(out, index=False)
    print(f"[CAL] saved: {out}")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="YYYY-MM-DD (local)")
    ap.add_argument("--currencies", default=NEWS_CURRENCIES, help="CSV e.g. USD,EUR,JPY,GBP")
    ap.add_argument("--min_impact", default=NEWS_MIN_IMPACT, choices=["low","medium","high"])
    ap.add_argument("--lookahead_hrs", type=int, default=NEWS_LOOKAHEAD_HRS)
    ap.add_argument("--tz", dest="local_tz", default=NEWS_TZ)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    df = fetch_investing_calendar(args.date, local_tz=args.local_tz)
    if df.empty:
        print("[CAL] no rows parsed; site might be serving a JS-only table for your IP. Try again later or use Playwright.")
    if args.save:
        save_csv(df, args.date, NEWS_OUTPUT_DIR)

    cur_list = [c.strip() for c in (args.currencies or "").split(",") if c.strip()]
    df2 = filter_events(df, currencies=cur_list, min_impact=args.min_impact,
                        lookahead_hours=args.lookahead_hrs, local_tz=args.local_tz)

    if args.print:
        if df2.empty:
            print("[CAL] No events found for current filters/window.")
        else:
            print(df2.to_string(index=False))

if __name__ == "__main__":
    main()
