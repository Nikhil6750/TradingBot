# run_loop.py — loop runner that pushes Telegram summary + CSVs after each cycle
from dotenv import load_dotenv
load_dotenv()

# --- ensure local imports work no matter where you launch from ---
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PYTHON = sys.executable                                  # current venv's python
ROOT   = os.path.dirname(os.path.abspath(__file__))

# Optional: interval minutes via env (default: 1)
try:
    INTERVAL_MIN = int(os.getenv("RUN_LOOP_INTERVAL_MIN", "1"))
except Exception:
    INTERVAL_MIN = 1


# === Telegram summary + CSV attachments (safe, non-blocking) ===
def _push_summary_and_csvs():
    """
    Sends a compact summary (Win%, PF, NetR, trades) and attaches CSVs
    (audit_by_symbol.csv, audit_by_hour.csv, backtest_results.csv) to Telegram, if present.
    Respects TELEGRAM_DRY_RUN / DRY_RUN. Never raises.
    """
    import math
    try:
        import pandas as pd
        import requests
    except Exception:
        print("[TG] pandas/requests not available; skipping Telegram push.")
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat  = os.getenv("TELEGRAM_CHAT_ID", "")
    dry   = (os.getenv("TELEGRAM_DRY_RUN", os.getenv("DRY_RUN", "0")) == "1")

    def _send_text(text: str, parse_mode: str = "HTML"):
        if dry or not token or not chat:
            print(f"[TG-DRY] sendMessage → {text[:1200]}...")
            return False
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": "true"},
                timeout=15,
            )
            if not r.ok:
                print(f"[TG-ERR] sendMessage {r.status_code}: {r.text}")
            return bool(r.ok)
        except Exception as e:
            print(f"[TG-ERR] sendMessage exception: {e}")
            return False

    def _send_file(path: str, caption: str = ""):
        if not os.path.exists(path):
            return False
        if dry or not token or not chat:
            print(f"[TG-DRY] sendDocument → {os.path.basename(path)}")
            return False
        try:
            with open(path, "rb") as fh:
                r = requests.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={"chat_id": chat, "caption": caption},
                    files={"document": (os.path.basename(path), fh, "text/csv")},
                    timeout=60,
                )
            if not r.ok:
                print(f"[TG-ERR] sendDocument {r.status_code}: {r.text}")
            return bool(r.ok)
        except Exception as e:
            print(f"[TG-ERR] sendDocument exception: {e}")
            return False

    trades_csv  = os.path.join(ROOT, "backtest_results_trades.csv")
    summary_csv = os.path.join(ROOT, "backtest_results.csv")
    audit_sym   = os.path.join(ROOT, "audit_by_symbol.csv")
    audit_hr    = os.path.join(ROOT, "audit_by_hour.csv")

    trades = wins = losses = expired = 0
    win_rate = 0.0
    net_r = 0.0
    pf = float("nan")

    if os.path.exists(trades_csv):
        try:
            t = pd.read_csv(trades_csv)
            if "result_r" in t.columns and not t.empty:
                r = pd.to_numeric(t["result_r"], errors="coerce").fillna(0.0)
                trades  = int(len(r)); wins = int((r > 0).sum()); losses = int((r < 0).sum()); expired = int((r == 0).sum())
                wl = wins + losses
                win_rate = (wins / wl * 100.0) if wl else 0.0
                gross_profit = float(r[r > 0].sum()); gross_loss = float(-r[r < 0].sum())
                if gross_loss == 0 and gross_profit == 0: pf = float("nan")
                elif gross_loss == 0: pf = float("inf")
                elif gross_profit == 0: pf = 0.0
                else: pf = float(gross_profit / gross_loss)
                net_r = float(r.sum())
        except Exception as e:
            print(f"[TG] Could not compute summary from {trades_csv}: {e}")

    best_line = ""
    if os.path.exists(audit_sym):
        try:
            a = pd.read_csv(audit_sym)
            if not a.empty:
                sort_cols = [c for c in ["pf","avg_r","net_r"] if c in a.columns]
                if sort_cols: a = a.sort_values(by=sort_cols, ascending=[False]*len(sort_cols))
                top = a.iloc[0]; sym = str(top.get("symbol", "")).upper()
                pf_b = top.get("pf", float("nan")); wr_b = top.get("win_rate_%", float("nan"))
                best_line = f"\nBest: <b>{sym}</b>" + (f" (PF {pf_b:.2f}, WR {wr_b:.1f}%)" if isinstance(pf_b,(int,float)) else "")
        except Exception as e:
            print(f"[TG] Could not parse {audit_sym}: {e}")

    if isinstance(pf, float) and math.isfinite(pf): pf_txt = f"{pf:.3f}"
    elif isinstance(pf, float) and math.isinf(pf):   pf_txt = "∞"
    else:                                            pf_txt = "n/a"

    summary_text = (
        "<b>📣 Samantha run complete</b>\n"
        f"Trades: <b>{trades}</b> | W/L/E: <b>{wins}/{losses}/{expired}</b>\n"
        f"Win%: <b>{win_rate:.2f}%</b> | PF: <b>{pf_txt}</b> | NetR: <b>{net_r:.2f}</b>"
        f"{best_line}"
    )

    _send_text(summary_text)

    for pth, cap in [(audit_sym, "audit_by_symbol.csv"), (audit_hr, "audit_by_hour.csv"), (summary_csv, "backtest_results.csv")]:
        if os.path.exists(pth):
            _send_file(pth, caption=cap)


def main():
    while True:
        print("=== starting cycle ===")
        subprocess.run([PYTHON, os.path.join(ROOT, "backtest_runner.py")], check=False)
        subprocess.run([PYTHON, os.path.join(ROOT, "performance_report.py")], check=False)
        subprocess.run([PYTHON, os.path.join(ROOT, "equity_curve.py")], check=False)
        subprocess.run([PYTHON, os.path.join(ROOT, "audit_insights.py")], check=False)
        _push_summary_and_csvs()
        time.sleep(max(INTERVAL_MIN, 1) * 60)


if __name__ == "__main__":
    main()
