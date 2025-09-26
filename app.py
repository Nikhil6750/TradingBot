import os
import re
import sys
import traceback
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional

import pandas as pd
import streamlit as st

# Use a headless matplotlib backend for any script that plots
os.environ.setdefault("MPLBACKEND", "Agg")

# ---------- Streamlit page setup ----------
st.set_page_config(page_title="Strategy Backtester Bot", page_icon="📈", layout="wide")
st.title("📈 Strategy Backtester Bot")
st.caption("Type a question like: *Can I take EURJPY now?* — or use the controls below. Not financial advice.")

# ---------- Filters (session defaults) ----------
DEFAULT_FILTERS = {"pf_min": 1.0, "win_min": 55.0, "netr_min": 0.0}
for k, v in DEFAULT_FILTERS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- Config ----------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_DEFAULT = os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data"))

OUTPUT_FILES = {
    "bt": PROJECT_ROOT / "backtest_results.csv",
    "audit_symbol": PROJECT_ROOT / "audit_by_symbol.csv",
    "audit_hour": PROJECT_ROOT / "audit_by_hour.csv",
    "equity_img": PROJECT_ROOT / "equity_curve.png",
    "trades_detailed": PROJECT_ROOT / "backtest_results_trades.csv",
}

SUPPORTED_SYMBOLS = ["EURJPY", "GBPAUD", "EURUSD", "GBPUSD", "USDJPY", "CHFJPY", "EURGBP"]

DEFAULTS = {
    "DATA_DIR": DATA_DIR_DEFAULT,
    "THRESHOLD": "50",
    "ATR_MULTIPLIER": "2.0",
    "RR": "2.0",
    "COOLDOWN_BARS": "8",
    "MIN_ATR_PCT": "0.0002",
    "SESSION": "ALL",
    "AUTO_SYNTHETIC_WHEN_EMPTY": "1",
    "PATTERN_COLS": "Pattern Alert,Pattern_Alert,pattern_alert,score,confidence,prob",
    "TZ_OFFSET_HOURS": "-5.5",
    "TRUNCATE_RESULTS": "1",
    "DRY_RUN": "1",
    "SYMBOL_ALLOWLIST": "GBPAUD,EURJPY,EURUSD",
    "HOUR_ALLOW": "15-18",
}

# ---------- Helpers ----------
def parse_free_text(q: str) -> Dict[str, str]:
    """Parse free-form Q like 'Can I take EURJPY now?' or 'EURUSD 0-6?'."""
    env = {}
    up = q.upper()

    # symbol
    sym = None
    for s in SUPPORTED_SYMBOLS:
        if re.search(rf"\b{s}\b", up):
            sym = s
            break
    if sym:
        env["SYMBOL_ALLOWLIST"] = sym

    # hour bucket (e.g., 0-6, 9-12, 15-18, 21-24)
    hour_match = re.findall(r"\b(?:[01]?\d|2[0-4])-(?:[01]?\d|2[0-4])\b", up)
    if hour_match:
        env["HOUR_ALLOW"] = ",".join(hour_match)

    return env


def set_env_from_dict(d: Dict[str, str]) -> None:
    for k, v in d.items():
        if v is not None:
            os.environ[k] = str(v)


def safe_load_csv(p: Path) -> Optional[pd.DataFrame]:
    try:
        if p.exists():
            return pd.read_csv(p)
    except Exception:
        pass
    return None


def run_pipeline() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Run your pipeline scripts (best-effort) and load their outputs.
    Always returns 4 dataframes (bt, sym, hr, detailed), any of which may be None.
    """
    # Backtest
    try:
        subprocess.run([sys.executable, "backtest_runner.py"], cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        st.error("backtest_runner.py failed.")
        st.code(traceback.format_exc())

    # Reports
    try:
        subprocess.run([sys.executable, "performance_report.py"], cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        st.warning("performance_report.py had an issue (continuing).")

    try:
        subprocess.run([sys.executable, "equity_curve.py"], cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        st.warning("equity_curve.py had an issue (continuing).")

    try:
        subprocess.run([sys.executable, "audit_insights.py"], cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        st.warning("audit_insights.py had an issue (continuing).")

    # Load outputs
    bt = safe_load_csv(OUTPUT_FILES["bt"])
    sym = safe_load_csv(OUTPUT_FILES["audit_symbol"])
    hr  = safe_load_csv(OUTPUT_FILES["audit_hour"])
    td  = safe_load_csv(OUTPUT_FILES["trades_detailed"])
    return bt, sym, hr, td


def make_decision(audit_symbol_df: Optional[pd.DataFrame], focus_symbol: Optional[str]) -> Tuple[str, str]:
    """
    Simple decision rule: YES if PF>=1.30 AND Win%>=38 AND NetR>=5 for the chosen symbol.
    """
    if audit_symbol_df is None or audit_symbol_df.empty:
        return ("CANNOT DECIDE", "No audit results to base a decision on.")

    df = audit_symbol_df.copy()
    if focus_symbol:
        df = df[df["symbol"].str.upper() == focus_symbol.upper()]

    if df.empty:
        return ("CANNOT DECIDE", f"No audit row for {focus_symbol}.")

    row = df.iloc[0]
    pf = float(row.get("pf", 0))
    win = float(row.get("win_rate_%", 0))
    netr = float(row.get("net_r", 0))

    if pf >= 1.30 and win >= 38 and netr >= 5:
        return ("YES (with discipline)", f"PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f} meets thresholds.")
    elif pf >= 1.10 and win >= 35 and netr >= 0:
        return ("MAYBE / CAUTION", f"Borderline: PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f}. Reduce risk or wait for A+ setup.")
    else:
        return ("NO", f"Metrics weak: PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f} below thresholds.")

# ---------- Sidebar ----------
with st.sidebar:
    st.subheader("Settings")

    # Basic knobs
    data_dir = st.text_input("DATA_DIR", DEFAULTS["DATA_DIR"])
    threshold = st.text_input("THRESHOLD", DEFAULTS["THRESHOLD"])
    atr_mult = st.text_input("ATR_MULTIPLIER", DEFAULTS["ATR_MULTIPLIER"])
    rr = st.text_input("RR", DEFAULTS["RR"])
    cooldown = st.text_input("COOLDOWN_BARS", DEFAULTS["COOLDOWN_BARS"])
    min_atr_pct = st.text_input("MIN_ATR_PCT", DEFAULTS["MIN_ATR_PCT"])
    session = st.text_input("SESSION", DEFAULTS["SESSION"])
    tz_off = st.text_input("TZ_OFFSET_HOURS", DEFAULTS["TZ_OFFSET_HOURS"])

    symbol_allow = st.text_input("SYMBOL_ALLOWLIST (comma-separated)", DEFAULTS["SYMBOL_ALLOWLIST"])
    hour_allow = st.text_input("HOUR_ALLOW (e.g. 0-6,15-18)", DEFAULTS["HOUR_ALLOW"])

    auto_syn = st.selectbox("AUTO_SYNTHETIC_WHEN_EMPTY", ["1", "0"], index=0)
    pattern_cols = st.text_input("PATTERN_COLS", DEFAULTS["PATTERN_COLS"])
    dry_run = st.selectbox("DRY_RUN", ["1", "0"], index=0)
    truncate = st.selectbox("TRUNCATE_RESULTS", ["1", "0"], index=0)

    st.markdown("---")
    st.caption("Tune thresholds used for the decision label (display only):")
    pf_min = st.slider("Min PF for YES", 1.10, 2.50, 1.30, 0.05)
    win_min = st.slider("Min Win% for YES", 20, 70, 38, 1)
    netr_min = st.slider("Min NetR for YES", -20, 100, 5, 1)

# ---------- Free-text ask ----------
q = st.text_input("Ask your question:", placeholder="e.g., Can I take EURJPY now?")
parsed_overrides = parse_free_text(q) if q else {}

# ---------- Param pickers (clicks) ----------
col1, col2, col3 = st.columns(3)
with col1:
    pick_symbol = st.selectbox("Symbol", ["(auto from question)"] + SUPPORTED_SYMBOLS, index=0)
with col2:
    pick_hour = st.text_input("Hour window (optional)", "", placeholder="e.g. 0-6 or 15-18")
with col3:
    run_btn = st.button("Run Backtest")

# ---------- Build env ----------
env_vars = DEFAULTS.copy()
env_vars["DATA_DIR"] = data_dir
env_vars["THRESHOLD"] = threshold
env_vars["ATR_MULTIPLIER"] = atr_mult
env_vars["RR"] = rr
env_vars["COOLDOWN_BARS"] = cooldown
env_vars["MIN_ATR_PCT"] = min_atr_pct
env_vars["SESSION"] = session
env_vars["TZ_OFFSET_HOURS"] = tz_off
env_vars["AUTO_SYNTHETIC_WHEN_EMPTY"] = auto_syn
env_vars["PATTERN_COLS"] = pattern_cols
env_vars["DRY_RUN"] = dry_run
env_vars["TRUNCATE_RESULTS"] = truncate

# Apply allowlists from sidebar first
if symbol_allow.strip():
    env_vars["SYMBOL_ALLOWLIST"] = symbol_allow
if hour_allow.strip():
    env_vars["HOUR_ALLOW"] = hour_allow

# Apply free-text overrides (question)
env_vars.update(parsed_overrides)

# Apply dropdown symbol/hour overrides
if pick_symbol != "(auto from question)":
    env_vars["SYMBOL_ALLOWLIST"] = pick_symbol
if pick_hour.strip():
    env_vars["HOUR_ALLOW"] = pick_hour.strip()

# Put env into process
set_env_from_dict(env_vars)

# Show active config
with st.expander("Active configuration", expanded=False):
    st.write(env_vars)

# ---------- Cache key & cached run ----------
cache_key = tuple(sorted(env_vars.items()))

@st.cache_data(show_spinner=False)
def cached_run(_key):
    return run_pipeline()

# ---------- Execute ----------
if run_btn:
    with st.spinner("Running backtest & reports..."):
        bt_df, sym_df, hr_df, trades_detailed_df = cached_run(cache_key)

    # Decide on first symbol in allowlist (if multiple)
    focus_symbol = None
    if env_vars.get("SYMBOL_ALLOWLIST"):
        focus_symbol = env_vars["SYMBOL_ALLOWLIST"].split(",")[0].strip().upper()

    # Decision (uses slider thresholds)
    def decide_with_sidebar(df, symbol):
        if df is None or df.empty:
            return ("CANNOT DECIDE", "No audit results available.")
        d = df if symbol is None else df[df["symbol"].str.upper() == symbol]
        if d.empty:
            return ("CANNOT DECIDE", f"No audit row for {symbol}.")
        row = d.iloc[0]
        pf = float(row.get("pf", 0))
        win = float(row.get("win_rate_%", 0))
        netr = float(row.get("net_r", 0))
        if pf >= pf_min and win >= win_min and netr >= netr_min:
            return ("YES (with discipline)", f"PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f} meets thresholds.")
        elif pf >= 1.10 and win >= 35 and netr >= 0:
            return ("MAYBE / CAUTION", f"Borderline: PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f}.")
        else:
            return ("NO", f"Weak metrics: PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f} below thresholds.")

    label, reason = decide_with_sidebar(sym_df, focus_symbol)

    # ---------- Display ----------
    st.success(f"**Decision:** {label}")
    st.write(reason)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("By Symbol")
        if sym_df is not None:
            st.dataframe(sym_df)
        else:
            st.write("No audit_by_symbol.csv found.")
    with c2:
        st.subheader("By Hour (local)")
        if hr_df is not None:
            st.dataframe(hr_df)
        else:
            st.write("No audit_by_hour.csv found.")

    st.subheader("All Trades")
    if bt_df is not None:
        st.dataframe(bt_df)
    else:
        st.write("No backtest_results.csv found.")

    st.subheader("Trades (detailed)")
    if trades_detailed_df is not None and not trades_detailed_df.empty:
        st.dataframe(trades_detailed_df)
        csv_bytes = trades_detailed_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download detailed trades CSV",
            data=csv_bytes,
            file_name="backtest_results_trades.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.caption("No backtest_results_trades.csv found.")

    st.subheader("Equity Curve")
    eq = OUTPUT_FILES["equity_img"]
    if eq.exists():
        st.image(str(eq))
    else:
        st.caption("No equity_curve.png yet (it appears when equity_curve.py generates it).")

    st.caption("Note: This tool is for research/education. Not financial advice.")
else:
    st.info("Set your preferences, type a question, then click **Run Backtest**.")
