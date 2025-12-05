import os
import re
import sys
import traceback
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional

import pandas as pd
import streamlit as st

# ---------- Global setup ----------
os.environ.setdefault("MPLBACKEND", "Agg")  # headless plotting
st.set_page_config(page_title="Strategy Backtester Bot", page_icon="📈", layout="wide")

# --- Minimal design CSS (optional, keeps UI tidy) ---
st.markdown("""
<style>
.main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1300px; }
.card { border: 1px solid rgba(250,250,250,0.1); border-radius: 16px; padding: 16px 18px; background: rgba(255,255,255,0.02); }
.badge { display:inline-block; padding: 4px 10px; border-radius: 999px; font-size: .85rem; font-weight: 600; }
.badge.ok { background: #1b5e20; color: #fff; }
.badge.warn { background: #7b5f00; color: #fff; }
.badge.no { background: #6b1111; color: #fff; }
</style>
""", unsafe_allow_html=True)

st.title("📈 Strategy Backtester Bot")
st.caption("Phase 1: CSV powered workbench. Tune → run → inspect. (Not financial advice.)")

# ---------- Defaults / config ----------
# store default display thresholds in session
DEFAULT_FILTERS = {"pf_min": 1.30, "win_min": 38, "netr_min": 5}
for k, v in DEFAULT_FILTERS.items():
    st.session_state.setdefault(k, v)

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_DEFAULT = os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data"))
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

def _first_existing(*paths: Path) -> Path:
    for p in paths:
        if p.exists():
            return p
    return paths[-1]

OUTPUT_FILES = {
    "bt": _first_existing(PROJECT_ROOT / "backtest_results.csv",
                          PROJECT_ROOT / "output/backtest_results.csv"),
    "audit_symbol": _first_existing(PROJECT_ROOT / "audit_by_symbol.csv",
                                    PROJECT_ROOT / "output/audit_by_symbol.csv"),
    "audit_hour": _first_existing(PROJECT_ROOT / "audit_by_hour.csv",
                                  PROJECT_ROOT / "output/audit_by_hour.csv"),
    "equity_img": _first_existing(PROJECT_ROOT / "equity_curve.png",
                                  PROJECT_ROOT / "output/equity_curve.png"),
    "trades_detailed": _first_existing(PROJECT_ROOT / "backtest_results_trades.csv",
                                       PROJECT_ROOT / "output/backtest_results_trades.csv"),
    "live_trades": PROJECT_ROOT / "live_trades.csv",  # for Phase 2
}

# ---------- Helpers ----------
def parse_free_text(q: str) -> Dict[str, str]:
    env = {}
    up = q.upper() if q else ""
    for s in SUPPORTED_SYMBOLS:
        if re.search(rf"\b{s}\b", up):
            env["SYMBOL_ALLOWLIST"] = s
            break
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
            df = pd.read_csv(p)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
    except Exception:
        pass
    return None

def run_pipeline() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    # Run scripts (best effort)
    try:
        subprocess.run([sys.executable, "backtest_runner.py"], cwd=PROJECT_ROOT, check=True)
    except subprocess.CalledProcessError:
        st.error("backtest_runner.py failed.")
        st.code(traceback.format_exc())
    for script, msg in [
        ("performance_report.py", "performance_report.py had an issue (continuing)."),
        ("equity_curve.py", "equity_curve.py had an issue (continuing)."),
        ("audit_insights.py", "audit_insights.py had an issue (continuing)."),
    ]:
        try:
            subprocess.run([sys.executable, script], cwd=PROJECT_ROOT, check=True)
        except subprocess.CalledProcessError:
            st.warning(msg)

    bt = safe_load_csv(OUTPUT_FILES["bt"])
    sym = safe_load_csv(OUTPUT_FILES["audit_symbol"])
    hr  = safe_load_csv(OUTPUT_FILES["audit_hour"])
    td  = safe_load_csv(OUTPUT_FILES["trades_detailed"])
    return bt, sym, hr, td

def make_decision(audit_symbol_df: Optional[pd.DataFrame], focus_symbol: Optional[str],
                  pf_min: float, win_min: int, netr_min: int) -> Tuple[str, str, str]:
    if audit_symbol_df is None or audit_symbol_df.empty:
        return ("CANNOT DECIDE", "No audit results to base a decision on.", "no")
    df = audit_symbol_df
    if focus_symbol:
        df = df[df["symbol"].str.upper() == focus_symbol.upper()]
    if df.empty:
        return ("CANNOT DECIDE", f"No audit row for {focus_symbol}.", "no")
    row = df.iloc[0]
    pf = float(row.get("pf", 0))
    win = float(row.get("win_rate_%", 0))
    netr = float(row.get("net_r", 0))
    if pf >= pf_min and win >= win_min and netr >= netr_min:
        return ("YES (with discipline)", f"PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f} meets thresholds.", "ok")
    elif pf >= 1.10 and win >= 35 and netr >= 0:
        return ("MAYBE / CAUTION", f"Borderline: PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f}.", "warn")
    else:
        return ("NO", f"Weak metrics: PF={pf:.2f}, Win%={win:.1f}, NetR={netr:.1f} below thresholds.", "no")

# ---------- Sidebar (friendly with old preset style) ----------
with st.sidebar:
    st.header("⚙️ Settings")

    # Quick Start form (must include submit button)
    with st.form("quick_start"):
        st.subheader("Quick start")

        PRESETS = {
            "Conservative": {"THRESHOLD": "70", "ATR_MULTIPLIER": "2.2", "RR": "1.2"},
            "Balanced":     {"THRESHOLD": "65", "ATR_MULTIPLIER": "1.8", "RR": "1.5"},
            "Aggressive":   {"THRESHOLD": "55", "ATR_MULTIPLIER": "1.5", "RR": "2.0"},
        }
        preset_sel = st.selectbox("Preset", ["(none)"] + list(PRESETS), index=0)

        data_dir = st.text_input("DATA_DIR", DATA_DIR_DEFAULT, placeholder="e.g. D:\\Trading Bot\\data")
        picked_syms = st.multiselect("Symbols", options=SUPPORTED_SYMBOLS,
                                     default=[s.strip() for s in DEFAULTS["SYMBOL_ALLOWLIST"].split(",") if s.strip() in SUPPORTED_SYMBOLS])
        hour_chip = st.selectbox("Hour window (quick pick)", ["(none)", "0-6","6-9","9-12","12-15","15-18","18-21","21-24"], index=6)
        hour_custom = st.text_input("Custom hours (optional)", DEFAULTS["HOUR_ALLOW"], placeholder="e.g. 0-6,15-18")

        st.caption("Decision thresholds (display only)")
        # ✅ FIXED TYPES:
        pf_min   = st.slider("Min PF for YES",   1.10, 2.50, float(st.session_state["pf_min"]), 0.05)
        win_min  = st.slider("Min Win% for YES", 20,   70,   int(st.session_state["win_min"]),   1)
        netr_min = st.slider("Min NetR for YES", -20,  100,  int(st.session_state["netr_min"]),  1)

        applied = st.form_submit_button("✅ Apply settings", use_container_width=True)

    with st.expander("Advanced parameters", expanded=False):
        threshold   = st.number_input("THRESHOLD", value=float(DEFAULTS["THRESHOLD"]), step=1.0)
        atr_mult    = st.number_input("ATR_MULTIPLIER", value=float(DEFAULTS["ATR_MULTIPLIER"]), step=0.1)
        rr          = st.number_input("RR", value=float(DEFAULTS["RR"]), step=0.1)
        cooldown    = st.number_input("COOLDOWN_BARS", value=int(DEFAULTS["COOLDOWN_BARS"]), step=1)
        min_atr_pct = st.text_input("MIN_ATR_PCT", DEFAULTS["MIN_ATR_PCT"])
        session     = st.selectbox("SESSION", ["ALL","ASIAN","LONDON","NY"], index=0)
        tz_off      = st.number_input("TZ_OFFSET_HOURS", value=float(DEFAULTS["TZ_OFFSET_HOURS"]), step=0.5)

        auto_syn    = st.checkbox("AUTO_SYNTHETIC_WHEN_EMPTY", value=DEFAULTS["AUTO_SYNTHETIC_WHEN_EMPTY"]=="1")
        dry_run     = st.checkbox("DRY_RUN", value=DEFAULTS["DRY_RUN"]=="1")
        truncate    = st.checkbox("TRUNCATE_RESULTS", value=DEFAULTS["TRUNCATE_RESULTS"]=="1")
        pattern_cols = st.text_area("PATTERN_COLS", DEFAULTS["PATTERN_COLS"])

    st.markdown("---")
    st.subheader("Upload data")
    up = st.file_uploader("Upload OHLC CSV", type=["csv"])
    if up:
        dest = Path(data_dir) / up.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(up.read())
        st.success(f"Saved → {dest}")

# ---------- Build env from sidebar choices ----------
symbol_allow = ",".join(picked_syms) if picked_syms else DEFAULTS["SYMBOL_ALLOWLIST"]
hour_allow = hour_custom.strip()
if hour_chip != "(none)":
    hour_allow = hour_chip if not hour_allow else f"{hour_chip},{hour_allow}"

env_vars = DEFAULTS.copy()
env_vars.update({
    "DATA_DIR": data_dir,
    "THRESHOLD": str(threshold if 'threshold' in locals() else DEFAULTS["THRESHOLD"]),
    "ATR_MULTIPLIER": str(atr_mult if 'atr_mult' in locals() else DEFAULTS["ATR_MULTIPLIER"]),
    "RR": str(rr if 'rr' in locals() else DEFAULTS["RR"]),
    "COOLDOWN_BARS": str(int(cooldown) if 'cooldown' in locals() else DEFAULTS["COOLDOWN_BARS"]),
    "MIN_ATR_PCT": min_atr_pct if 'min_atr_pct' in locals() else DEFAULTS["MIN_ATR_PCT"],
    "SESSION": session if 'session' in locals() else DEFAULTS["SESSION"],
    "TZ_OFFSET_HOURS": str(tz_off if 'tz_off' in locals() else DEFAULTS["TZ_OFFSET_HOURS"]),
    "AUTO_SYNTHETIC_WHEN_EMPTY": "1" if ('auto_syn' in locals() and auto_syn) else "0",
    "DRY_RUN": "1" if ('dry_run' in locals() and dry_run) else "0",
    "TRUNCATE_RESULTS": "1" if ('truncate' in locals() and truncate) else "0",
    "PATTERN_COLS": pattern_cols if 'pattern_cols' in locals() else DEFAULTS["PATTERN_COLS"],
    "SYMBOL_ALLOWLIST": symbol_allow,
    "HOUR_ALLOW": hour_allow,
})
# Apply preset (older style)
if 'preset_sel' in locals() and preset_sel != "(none)":
    for k, v in PRESETS[preset_sel].items():
        env_vars[k] = v

# Free-text ask + overrides
q = st.text_input("Ask your question", placeholder="e.g., Can I take EURJPY now?")
parsed_overrides = parse_free_text(q)
if parsed_overrides:
    env_vars.update(parsed_overrides)

colA, colB, colC, colD = st.columns([1,1,1,1])
with colA:
    pick_symbol = st.selectbox("Symbol (override)", ["(auto from question)"] + SUPPORTED_SYMBOLS, index=0)
with colB:
    pick_hour = st.text_input("Hour window (override)", "", placeholder="e.g. 0-6 or 15-18")
with colC:
    run_btn = st.button("▶️ Run Backtest", use_container_width=True)
with colD:
    live_mode = st.toggle("Live mode (files only)", value=False)

if pick_symbol != "(auto from question)":
    env_vars["SYMBOL_ALLOWLIST"] = pick_symbol
if pick_hour.strip():
    env_vars["HOUR_ALLOW"] = pick_hour.strip()

# Validate and set env
errors = []
if not Path(env_vars["DATA_DIR"]).exists():
    errors.append(f"DATA_DIR does not exist: {env_vars['DATA_DIR']}")
if env_vars["HOUR_ALLOW"].strip():
    bad = [seg for seg in [s.strip() for s in env_vars["HOUR_ALLOW"].split(",")]
           if not re.match(r"^(?:[01]?\d|2[0-4])-(?:[01]?\d|2[0-4])$", seg)]
    if bad:
        errors.append(f"Invalid hour range(s): {', '.join(bad)} (use 0-6, 15-18, etc.)")
set_env_from_dict(env_vars)

# Cache for non-live mode
cache_key = tuple(sorted(env_vars.items()))
@st.cache_data(show_spinner=False)
def cached_run(_key):
    return run_pipeline()

# ---------- Results ----------
tabs = st.tabs(["Overview", "Tables", "Equity", "Diagnostics"])

if errors:
    with tabs[3]:
        st.error("Please fix these before running:\n- " + "\n- ".join(errors))

if run_btn and not errors:
    if live_mode:
        bt_df = safe_load_csv(OUTPUT_FILES["bt"])
        sym_df = safe_load_csv(OUTPUT_FILES["audit_symbol"])
        hr_df  = safe_load_csv(OUTPUT_FILES["audit_hour"])
        trades_detailed_df = safe_load_csv(OUTPUT_FILES["trades_detailed"]) or safe_load_csv(OUTPUT_FILES["live_trades"])
    else:
        with st.spinner("Running backtest & reports…"):
            bt_df, sym_df, hr_df, trades_detailed_df = cached_run(cache_key)

    focus_symbol = env_vars.get("SYMBOL_ALLOWLIST", "").split(",")[0].strip().upper() if env_vars.get("SYMBOL_ALLOWLIST") else None
    label, reason, tone = make_decision(sym_df, focus_symbol, float(pf_min), int(win_min), int(netr_min))

    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        badge_cls = {"ok":"badge ok", "warn":"badge warn", "no":"badge no"}.get(tone, "badge")
        st.markdown(f'<span class="{badge_cls}">{label}</span> &nbsp; {reason}', unsafe_allow_html=True)
        if sym_df is not None and not sym_df.empty:
            try:
                view = sym_df.copy()
                if focus_symbol:
                    view = view[view["symbol"].str.upper()==focus_symbol]
                row = view.iloc[0]
                k1,k2,k3,k4 = st.columns(4)
                k1.metric("Profit Factor", f"{float(row.get('pf',0)):0.2f}")
                k2.metric("Win Rate %", f"{float(row.get('win_rate_%',0)):0.1f}")
                k3.metric("Net R", f"{float(row.get('net_r',0)):0.1f}")
                k4.metric("Trades", f"{int(row.get('trades',0))}")
            except Exception:
                pass
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("**Active configuration**")
        st.json(env_vars, expanded=False)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("By Symbol")
        if sym_df is not None and not sym_df.empty:
            st.dataframe(sym_df, use_container_width=True, height=360)
            st.download_button("Download By Symbol CSV",
                               sym_df.to_csv(index=False).encode("utf-8"),
                               "audit_by_symbol.csv", "text/csv", use_container_width=True)
        else:
            st.caption("No audit_by_symbol.csv found.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("By Hour (local)")
        if hr_df is not None and not hr_df.empty:
            st.dataframe(hr_df, use_container_width=True, height=360)
            st.download_button("Download By Hour CSV",
                               hr_df.to_csv(index=False).encode("utf-8"),
                               "audit_by_hour.csv", "text/csv", use_container_width=True)
        else:
            st.caption("No audit_by_hour.csv found.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("All Trades (summary)")
        if bt_df is not None and not bt_df.empty:
            st.dataframe(bt_df, use_container_width=True, height=280)
            st.download_button("Download All Trades CSV",
                               bt_df.to_csv(index=False).encode("utf-8"),
                               "backtest_results.csv", "text/csv", use_container_width=True)
        else:
            st.caption("No backtest_results.csv found.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Trades (detailed)")
        if trades_detailed_df is not None and not trades_detailed_df.empty:
            st.dataframe(trades_detailed_df, use_container_width=True, height=360)
            st.download_button("Download detailed trades CSV",
                               trades_detailed_df.to_csv(index=False).encode("utf-8"),
                               "backtest_results_trades.csv", "text/csv", use_container_width=True)
        else:
            st.caption("No backtest_results_trades.csv found.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Equity Curve")
        eq = OUTPUT_FILES["equity_img"]
        if eq.exists():
            st.image(str(eq), use_column_width=True)
        else:
            st.caption("No equity_curve.png yet (run a backtest or run equity_curve.py).")
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Diagnostics")
        st.write("DATA_DIR:", env_vars["DATA_DIR"])
        st.write("Preset:", preset_sel)
        st.write("Live mode:", live_mode)
        st.code("python backtest_runner.py\npython performance_report.py\npython equity_curve.py\npython audit_insights.py")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    with tabs[0]:
        st.info("Set your preferences on the left and click **Run Backtest**. You can paste a question like “Can I take EURJPY now?” to auto-pick symbol/hours.")
