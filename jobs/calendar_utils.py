# jobs/calendar_utils.py
# Robust Investing.com Economic Calendar fetcher
# - session warmup for cookies/CF
# - POST to Investing AJAX endpoint to get the day’s HTML snippet
# - parse rows (Time, Cur., Impact, Event, Actual, Forecast, Previous)
# - returns a pandas DataFrame with the exact columns your UI expects

from __future__ import annotations
import json, random, time, re
from typing import List, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

from bs4 import BeautifulSoup

# ... inside _parse_rows_from_html(html) ...
# (Removed erroneous top-level BeautifulSoup usage; parsing is handled inside _parse_rows_from_html)


BASE = "https://www.investing.com/economic-calendar/"
AJAX = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"

SCHEMA = ["time","currency","impact_stars","event","actual","forecast","previous"]

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
]

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    })
    retry = Retry(
        total=5, connect=5, read=5,
        backoff_factor=1.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET","POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=32)
    s.mount("https://", adapter); s.mount("http://", adapter)
    return s

def _clean(s: Optional[str]) -> str:
    if not s: return ""
    s = s.replace("\xa0"," ").strip()
    return "" if s in {"—","-"} else re.sub(r"\s+"," ", s)

def _get_text(el) -> str:
    return _clean(el.get_text()) if el else ""

def _impact_from_td(td) -> int:
    if not td: return 0
    # Primary hint: data-img_key="bullX"
    key = td.get("data-img_key","")
    m = re.search(r"bull(\d)", key)
    if m: return int(m.group(1))
    # Fallback: count icons that look like stars/bulls
    html = str(td)
    return html.count("bull") + html.count("star")

def _find_value_td(row, class_name: str, title_matches: tuple[str,...]):
    # 1) class-based
    td = row.find("td", class_=class_name)
    if td: return td
    # 2) attribute-based (data-title / aria-label)
    for td in row.find_all("td"):
        label = (td.get("data-title") or td.get("aria-label") or "").strip().lower()
        if label in title_matches:
            return td
    return None

def _deep_value(td) -> str:
    if not td: return ""
    txt = _get_text(td)
    if txt: return txt
    for a in ("data-real-value","data-value","data-col-value","data-text","title"):
        v = td.get(a)
        if v: return _clean(str(v))
    for ch in td.find_all(True, recursive=True):
        t = _get_text(ch)
        if t: return t
        for a in ("data-real-value","data-value","data-col-value","data-text","title"):
            v = ch.get(a)
            if v: return _clean(str(v))
    return ""

def _parse_rows_from_html(html: str) -> pd.DataFrame:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
    # Fallback if lxml not present or fails for any reason
        soup = BeautifulSoup(html, "html.parser")

    rows = soup.find_all("tr", class_="js-event-item")
    out: List[Dict] = []
    for r in rows:
        t_time  = _get_text(r.find("td", class_="time"))
        t_cur   = _get_text(r.select_one("td.flagCur") or r.select_one("td.left.flagCur") or r.select_one("td.cur"))
        t_imp   = _impact_from_td(r.find("td", class_="sentiment"))
        t_event = _get_text(r.find("td", class_="event"))

        td_actual   = _find_value_td(r, "actual",   ("actual",))
        td_forecast = _find_value_td(r, "forecast", ("forecast",))
        td_previous = _find_value_td(r, "previous", ("previous","prior","previous value"))

        t_actual   = _deep_value(td_actual)
        t_forecast = _deep_value(td_forecast)
        t_previous = _deep_value(td_previous)

        # Normalize HH:MM
        m = re.match(r"^\s*(\d{1,2}):(\d{1,2})\s*$", t_time or "")
        if m:
            t_time = f"{m.group(1).zfill(2)}:{m.group(2).zfill(2)}"

        out.append({
            "time": t_time,
            "currency": t_cur,
            "impact_stars": t_imp,
            "event": t_event,
            "actual": t_actual,
            "forecast": t_forecast,
            "previous": t_previous,
        })
    return pd.DataFrame(out, columns=SCHEMA) if out else pd.DataFrame(columns=SCHEMA)

def fetch_investing_calendar(current_tab: str = "today", tz_offset: str = "0") -> pd.DataFrame:
    """
    current_tab: 'today' | 'tomorrow' | 'yesterday' | 'thisWeek' | 'nextWeek'
    tz_offset:   string hours from GMT, e.g. '0', '-4', '5.5'
    """
    sess = _session()

    # Warm-up to set cookies / pass CF
    for i in range(3):
        try:
            sess.get(BASE, timeout=30)
            break
        except requests.RequestException:
            time.sleep(1.2 + i*0.8)

    payload = {
        "country[]": ["all"],
        "importance[]": ["1","2","3"],
        "timeZone": tz_offset,
        "timeFilter": "timeRemain",
        "currentTab": current_tab,
        "submitFilters": "1",
        "limit_from": "0",
    }
    headers = {
        "User-Agent": random.choice(UA_POOL),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE,
    }

    # Try AJAX a few times
    for i in range(4):
        try:
            r = sess.post(AJAX, headers=headers, data=payload, timeout=40)
            if r.status_code == 200:
                try:
                    j = r.json(); html = j.get("data") or ""
                except json.JSONDecodeError:
                    html = r.text
                df = _parse_rows_from_html(html)
                if not df.empty:
                    return df
        except requests.RequestException:
            pass
        time.sleep(1.0 + i*1.2)

    # Fallback: get the full page (may return fewer rows in some regions)
    try:
        g = sess.get(BASE, timeout=40)
        if g.status_code == 200:
            df = _parse_rows_from_html(g.text)
            return df
    except requests.RequestException:
        pass

    # Last resort: empty schema
    return pd.DataFrame(columns=SCHEMA)
