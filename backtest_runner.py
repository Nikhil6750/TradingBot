# backtest_runner.py — FINAL (v3.2)
# - Self-contained (no imports from backtest.py)
# - Ignores inline comments in env (e.g., SYMBOL_ALLOWLIST="# leave blank")
# - Flexible PATTERN_COLS + AUTO_SYNTHETIC_WHEN_EMPTY fallback
# - Safe SYMBOL_ALLOWLIST handling
# - Produces: backtest_results.csv, backtest_results_trades.csv, backtest_trade_audit.csv

import os, glob, csv, traceback
from dataclasses import dataclass
from typing import List, Tuple
import pandas as pd
import numpy as np

# Optional .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

print(">>> BACKTEST_RUNNER BUILD: v3.2 <<<")

# ---------- helpers ----------
def getenv_float(name: str, default: float) -> float:
    v = os.getenv(name, "")
    try:
        return float(v)
    except Exception:
        return float(default)

def getenv_int(name: str, default: int) -> int:
    v = os.getenv(name, "")
    try:
        return int(float(v))
    except Exception:
        return int(default)

def getenv_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default

# ---------- config ----------
THRESHOLD       = getenv_float("THRESHOLD", getenv_float("BT_THRESHOLD", 65.0))
ATR_MULTIPLIER  = getenv_float("ATR_MULTIPLIER", getenv_float("ATR_MULT", 1.8))
RR              = getenv_float("RR", getenv_float("BT_RR", 1.5))
SESSION_RAW     = getenv_str("SESSION", getenv_str("BT_SESSION", "ALL"))
TZ_OFFSET_HOURS = getenv_float("TZ_OFFSET_HOURS", getenv_float("BT_TZ_OFFSET_HOURS", -5.5))
DATA_DIR        = getenv_str("DATA_DIR", "data")
SPREAD_PIPS     = getenv_float("SPREAD_PIPS", 0.00006)
SLIPPAGE_PIPS   = getenv_float("SLIPPAGE_PIPS", 0.00002)
FEE_R           = getenv_float("FEE_R", 0.0)
MAX_BARS        = getenv_int("MAX_BARS", 120)
DEBUG_SCAN      = getenv_str("DEBUG_SCAN", "0") == "1"

# Flexible score columns + safe fallback
PATTERN_COLS = [c.strip() for c in getenv_str(
    "PATTERN_COLS", "Pattern Alert,Pattern_Alert,pattern_alert,score,confidence"
).split(",") if c.strip()]
AUTO_SYNTHETIC_WHEN_EMPTY = getenv_str("AUTO_SYNTHETIC_WHEN_EMPTY", "1") == "1"

# --- SYMBOL_ALLOWLIST: clean & ignore inline comments ---
_raw_allow = os.getenv("SYMBOL_ALLOWLIST", "")
_raw_allow = _raw_allow.split("#", 1)[0]  # drop inline comment
SYMBOL_ALLOWLIST = [s.strip().upper() for s in _raw_allow.split(",") if s.strip()]

# HOUR_ALLOW: also drop inline comment and spaces (format: "12-15,15-18")
_raw_hours = os.getenv("HOUR_ALLOW", "")
_raw_hours = _raw_hours.split("#", 1)[0]
HOUR_ALLOW = _raw_hours.strip()

def parse_session(raw: str) -> Tuple[str, Tuple[int, int]]:
    raw = (raw or "").strip().upper()
    if raw == "ALL":
        return "ALL", (0, 24)
    try:
        a, b = raw.replace(" ", "").split("-")
        a, b = int(a), int(b)
        if 0 <= a <= 23 and 0 <= b <= 24 and a != b:
            return f"{a}-{b}", (a, b)
    except Exception:
        pass
    return "ALL", (0, 24)

SESSION_LABEL, SESSION = parse_session(SESSION_RAW)
print(f"[BT] Using threshold={THRESHOLD}, atr_mult={ATR_MULTIPLIER}, rr={RR}, "
      f"session={SESSION_LABEL} (raw='{SESSION_RAW}'), tz_offset={TZ_OFFSET_HOURS}h")
print(f"[DEBUG] SYMBOL_ALLOWLIST parsed={SYMBOL_ALLOWLIST!r}")

# ---------- outputs ----------
SUMMARY_CSV = "backtest_results.csv"
TRADE_CSV   = "backtest_results_trades.csv"
AUDIT_CSV   = "backtest_trade_audit.csv"

def ensure_output_files():
    if getenv_str("TRUNCATE_RESULTS", "0") == "1":
        for p in (SUMMARY_CSV, TRADE_CSV, AUDIT_CSV):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
    if not os.path.exists(TRADE_CSV):
        with open(TRADE_CSV, "w", newline="") as f:
            csv.writer(f).writerow(["result_r", "file"])
    if not os.path.exists(AUDIT_CSV):
        with open(AUDIT_CSV, "w", newline="") as f:
            csv.writer(f).writerow([
                "file","symbol","index","utc_time","local_time",
                "direction","entry","sl","tp","bars_held","outcome_r","reason"
            ])

# ---------- util ----------
def infer_symbol_from_filename(path: str) -> str:
    base = os.path.basename(path)
    head = base.split(",")[0].strip()        # e.g., "FX_EURUSD"
    return head.replace("FX_", "").upper()

def parse_hour_allow(raw: str):
    if not raw: return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            try:
                a,b = map(int, part.split("-"))
                out.append((a,b))
            except:
                pass
    return out

HOUR_BUCKETS = parse_hour_allow(HOUR_ALLOW)

def within_session(ts_hour: int, session: Tuple[int,int]) -> bool:
    a, b = session
    if a == 0 and b == 24: return True
    if a < b:  return a <= ts_hour < b
    return (ts_hour >= a) or (ts_hour < b)

def within_hour_allow(h: int) -> bool:
    if not HOUR_BUCKETS: return True
    return any(a <= h < b for a,b in HOUR_BUCKETS)

@dataclass
class FileStats:
    file: str
    trades: int
    wins: int
    losses: int
    expired: int
    net_r: float
    profit_factor: float

def instrument_costs(symbol: str):
    # simple per-symbol defaults; tune as needed
    JPY = {"USDJPY","EURJPY","GBPJPY","CHFJPY"}
    MAJ = {"EURUSD","GBPUSD","AUDUSD","NZDUSD","USDCAD","USDCHF","EURGBP","GBPAUD"}
    if symbol in JPY: return (0.01,    0.005)     # ~1 pip, 0.5 pip
    if symbol in MAJ: return (0.00008, 0.00002)   # ~0.8 pip, 0.2 pip
    return (SPREAD_PIPS, SLIPPAGE_PIPS)

def append_trade(result_r: float, file_name: str):
    with open(TRADE_CSV, "a", newline="") as f:
        csv.writer(f).writerow([result_r, file_name])

def append_audit(file_name, symbol, idx, utc_ts, local_ts, direction, entry, sl, tp, bars, r, reason):
    with open(AUDIT_CSV, "a", newline="") as f:
        csv.writer(f).writerow([
            file_name, symbol, idx,
            str(utc_ts) if pd.notna(utc_ts) else "",
            str(local_ts) if pd.notna(local_ts) else "",
            direction, f"{entry:.6f}", f"{sl:.6f}", f"{tp:.6f}",
            bars, f"{r:.6f}", reason
        ])

# ---------- per-file backtest (self-contained) ----------
def process_one_file(csv_path: str) -> FileStats:
    base_name = os.path.basename(csv_path)
    symbol = infer_symbol_from_filename(csv_path)
    print(f"[INFO] Start {base_name} (symbol={symbol})")

    df = pd.read_csv(csv_path)

    # timestamps -> local hour (optional)
    if "time" in df.columns:
        dt_utc   = pd.to_datetime(df["time"], unit="s", utc=True, errors="coerce")
        dt_local = dt_utc + pd.to_timedelta(TZ_OFFSET_HOURS, unit="h")
        df["_hour_local"] = dt_local.dt.hour
    else:
        dt_utc   = pd.Series([pd.NaT]*len(df))
        dt_local = pd.Series([pd.NaT]*len(df))
        df["_hour_local"] = 12

    # hour + session filters
    if HOUR_BUCKETS:
        df = df[df["_hour_local"].apply(lambda h: within_hour_allow(int(h)))].copy()
        dt_utc = dt_utc.loc[df.index]; dt_local = dt_local.loc[df.index]
    df = df[df["_hour_local"].apply(lambda h: within_session(int(h), SESSION))].copy()
    dt_utc = dt_utc.loc[df.index]; dt_local = dt_local.loc[df.index]

    # schema check
    if not {"open","high","low","close"}.issubset(df.columns):
        print(f"[WARN] Missing OHLC in {base_name} — skipping.")
        return FileStats(base_name, 0,0,0,0, 0.0, float("nan"))

    # indicators
    hi, lo, cl = df["high"], df["low"], df["close"]
    tr  = pd.concat([(hi-lo).abs(), (hi-cl.shift()).abs(), (lo-cl.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    sma20 = cl.rolling(20, min_periods=20).mean()

    # ---- candidate signals (flexible + fallback) ----
    found_col = None
    for cname in PATTERN_COLS:
        if cname in df.columns:
            found_col = cname
            break

    sig_idx = []
    if found_col is not None:
        sig_idx = df.index[df[found_col] >= THRESHOLD].tolist()
        print(f"  -> {len(sig_idx)} raw signals from '{found_col}' (>= {THRESHOLD})")
    else:
        print("  -> no score column found; using synthetic scan points")

    if not sig_idx:
        if AUTO_SYNTHETIC_WHEN_EMPTY:
            step = max(len(df)//200, 1)
            sig_idx = list(range(20, max(len(df)-MAX_BARS, 20), step))
            print(f"  -> fallback: {len(sig_idx)} synthetic scan points (AUTO_SYNTHETIC_WHEN_EMPTY=1)")
        else:
            print("  -> no signals and fallback disabled (AUTO_SYNTHETIC_WHEN_EMPTY=0)")

    if DEBUG_SCAN:
        print(f"  -> pre-filter candidates: {len(sig_idx)}")

    sym_spread, sym_slip = instrument_costs(symbol)

    # walk forward for each candidate
    trade_results: List[float] = []
    wins = losses = expired = 0

    min_atr_pct = getenv_float("MIN_ATR_PCT", 0.0002)
    cooldown_bars = getenv_int("COOLDOWN_BARS", 5)
    last_signal_i = -10_000

    for i in sig_idx:
        if i >= len(df) - 2 or pd.isna(atr.iat[i]) or pd.isna(sma20.iat[i]):
            continue
        if i - last_signal_i < cooldown_bars:
            continue

        vol = float(atr.iat[i])
        px  = float(cl.iat[i])
        if vol <= 0 or pd.isna(vol):
            continue

        # sanity filters
        if abs(px - float(sma20.iat[i])) < 0.35 * vol:
            continue   # avoid chop
        if vol < px * min_atr_pct:
            continue   # tiny volatility

        last_signal_i = i

        # direction by position vs SMA
        direction = "BUY" if px >= float(sma20.iat[i]) else "SELL"

        # next bar confirmation (mild)
        nxt = df.iloc[i+1]
        if direction == "BUY" and nxt["close"] < nxt["open"]:
            continue
        if direction == "SELL" and nxt["close"] > nxt["open"]:
            continue

        # simple trend slope confirmation
        if i < 5:
            continue
        slope = float(sma20.iat[i]) - float(sma20.iat[i-5])
        if direction == "BUY" and slope <= 0:
            continue
        if direction == "SELL" and slope >= 0:
            continue

        # entry + costs
        entry_raw = cl.iat[i]
        cost = sym_spread + sym_slip
        entry = float(entry_raw) + (cost if direction == "BUY" else -cost)
        if direction == "BUY":
            sl = entry - ATR_MULTIPLIER * vol
            tp = entry + RR * (entry - sl)
        else:
            sl = entry + ATR_MULTIPLIER * vol
            tp = entry - RR * (sl - entry)

        # forward walk
        fut = df.iloc[i+1 : i+1+MAX_BARS][["high","low","close"]]
        hit = None
        bars = 0
        reason = "EXPIRED"

        for _, rbar in fut.iterrows():
            bars += 1
            if direction == "BUY":
                if rbar["low"]  <= sl: hit = -1.0; reason="SL"; break
                if rbar["high"] >= tp: hit =  RR;  reason="TP"; break
            else:
                if rbar["high"] >= sl: hit = -1.0; reason="SL"; break
                if rbar["low"]  <= tp: hit =  RR;  reason="TP"; break

        r_mult = (hit if hit is not None else 0.0) - FEE_R
        trade_results.append(r_mult)
        if r_mult > 0: wins += 1
        elif r_mult < 0: losses += 1
        else: expired += 1

        # audit rows
        append_trade(r_mult, base_name)
        utc_ts   = dt_utc.loc[i] if i in dt_utc.index else pd.NaT
        local_ts = dt_local.loc[i] if i in dt_local.index else pd.NaT
        append_audit(base_name, symbol, int(i), utc_ts, local_ts,
                     direction, float(entry), float(sl), float(tp),
                     int(bars), float(r_mult), reason)

        if DEBUG_SCAN:
            print(f"  -> {symbol} i={i} {direction} vol={vol:.6f} r={r_mult:.3f} ({reason})")

    trades  = len(trade_results)
    gross_profit = wins * RR
    gross_loss   = losses * 1.0
    net_r        = gross_profit - gross_loss
    if losses == 0 and wins == 0: pf = float("nan")
    elif losses == 0:             pf = float("inf")
    elif wins == 0:               pf = 0.0
    else:                         pf = gross_profit / gross_loss

    print(f"[INFO] Done {base_name}: trades={trades}, W/L/E={wins}/{losses}/{expired}, "
          f"PF={(pf if pd.notna(pf) and np.isfinite(pf) else 'nan')}, NetR={net_r:.3f}")

    return FileStats(base_name, trades, wins, losses, expired, round(net_r,3),
                     round(pf,6) if pd.notna(pf) and np.isfinite(pf) else pf)

# ---------- main ----------
def main():
    ensure_output_files()

    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    print(f"[DEBUG] Found {len(files)} CSVs in {os.path.abspath(DATA_DIR)}")
    if not files:
        pd.DataFrame([], columns=["file","trades","win_rate","profit_factor","net_r"]).to_csv(SUMMARY_CSV, index=False)
        print(f"Backtest complete. Results saved to {SUMMARY_CSV}")
        return

    per_file: List[FileStats] = []
    total_trades = total_wins = total_losses = total_expired = 0

    for path in files:
        sym = infer_symbol_from_filename(path)
        if SYMBOL_ALLOWLIST and sym not in SYMBOL_ALLOWLIST:
            print(f"[DEBUG] skipping {os.path.basename(path)} (symbol={sym}) due to SYMBOL_ALLOWLIST={SYMBOL_ALLOWLIST}")
            continue
        try:
            s = process_one_file(path)
        except Exception as e:
            print(f"[ERROR] Crashed while processing: {os.path.basename(path)} -> {e}")
            traceback.print_exc()
            continue

        per_file.append(s)
        total_trades  += s.trades
        total_wins    += s.wins
        total_losses  += s.losses
        total_expired += s.expired

    # summary CSV for per-file stats
    rows = []
    for s in per_file:
        denom = max(s.wins + s.losses, 1)
        wr = (s.wins / denom) * 100.0
        rows.append({
            "file": s.file,
            "trades": s.trades,
            "win_rate": f"{wr:.2f}%",
            "profit_factor": s.profit_factor,
            "net_r": s.net_r,
        })
    pd.DataFrame(rows, columns=["file","trades","win_rate","profit_factor","net_r"]).to_csv(SUMMARY_CSV, index=False)

    # human summary
    gross_profit = total_wins * RR
    gross_loss   = total_losses * 1.0
    net_r        = gross_profit - gross_loss
    wl = (total_wins + total_losses)
    win_rate = (total_wins / wl * 100.0) if wl else 0.0
    avg_r    = (net_r / total_trades) if total_trades else 0.0
    if total_losses == 0 and total_wins == 0: pf = float("nan")
    elif total_losses == 0:                   pf = float("inf")
    elif total_wins == 0:                     pf = 0.0
    else:                                     pf = gross_profit / gross_loss

    print("\n=== Backtest Summary ===")
    print(f"Trades       : {total_trades}")
    print(f"Wins/Losses  : {total_wins}/{total_losses}  Expired: {total_expired}")
    print(f"Win Rate     : {win_rate:.2f}%")
    print(f"Avg R        : {avg_r:.3f}")
    print(f"ProfitFactor : {pf:.3f}" if pd.notna(pf) and np.isfinite(pf) else "ProfitFactor : nan")
    print(f"Net R        : {net_r:.3f}")
    print(f"Backtest complete. Results saved to {SUMMARY_CSV}")

if __name__ == "__main__":
    main()
