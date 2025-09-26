# loop_daemon.py
# Run your pipeline on a fixed cadence, no Windows Task Scheduler needed.
# - Respects ACTIVE_HOURS like "0-6,15-18" (local time) or "ALL"
# - Uses your existing run_loop.py
# - Push-only: no bot commands, just Telegram alerts
# - Graceful stop: create an empty file STOP_LOOP in the project folder

import os, sys, time, subprocess, datetime as dt
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PY_EXE = sys.executable                                # uses current venv python
RUN_SCRIPT = PROJECT_DIR / "run_loop.py"
STOP_FLAG = PROJECT_DIR / "STOP_LOOP"                  # create this file to stop
LOCK_FILE = PROJECT_DIR / ".loop_running.lock"         # prevents accidental overlap

# === Config via env (with safe defaults) ===
# How often to run (seconds)
LOOP_EVERY_SEC = int(os.getenv("LOOP_EVERY_SEC", "900"))            # 15 min
# Local active hours like "0-6,15-18" or "ALL"
ACTIVE_HOURS = os.getenv("ACTIVE_HOURS", "ALL").strip().upper()
# Hard safety cap to avoid runaway loops if a run hangs (minutes)
RUN_TIMEOUT_MIN = int(os.getenv("RUN_TIMEOUT_MIN", "15"))

# Telegram (optional but recommended)
TELEGRAM_OK = True
try:
    import alert  # your alert.py
except Exception:
    TELEGRAM_OK = False
    print("[WARN] alert.py not importable; Telegram heartbeats disabled.")

def send_tg(msg: str):
    if TELEGRAM_OK:
        try:
            # force HTML parsing for nicer formatting (alert.send_telegram handles DRY_RUN)
            alert.send_telegram(msg, parse_mode="HTML")
        except Exception as e:
            print(f"[WARN] Telegram send failed: {e}")

def parse_active_windows(spec: str):
    """Return list of (start,end) hour tuples in 0..24; 'ALL' -> [(0,24)]."""
    if spec in ("", "ALL", "ANY"):
        return [(0, 24)]
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            a, b = part.split("-", 1)
            start = int(a); end = int(b)
            start = max(0, min(24, start))
            end = max(0, min(24, end))
            if start == end:
                # treat "x-x" as the single hour bucket
                end = (start + 1) % 24
            out.append((start, end))
        except Exception:
            print(f"[WARN] Bad ACTIVE_HOURS segment: {part}; skipping")
    return out or [(0, 24)]

WINDOWS = parse_active_windows(ACTIVE_HOURS)

def in_active_window(now: dt.datetime) -> bool:
    h = now.hour
    for (a, b) in WINDOWS:
        if a < b and (a <= h < b):
            return True
        if a > b and (h >= a or h < b):  # wrap-around window like "21-3"
            return True
    return False

def main():
    started = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_tg(f"▶️ <b>Loop daemon started</b> @ <code>{started}</code>\n"
            f"Cadence: <code>{LOOP_EVERY_SEC}s</code> | Hours: <code>{ACTIVE_HOURS}</code>")

    while True:
        # Graceful stop
        if STOP_FLAG.exists():
            send_tg("⏹️ <b>Loop daemon stopped</b> (STOP_LOOP flag present).")
            try: STOP_FLAG.unlink()
            except: pass
            break

        now = dt.datetime.now()
        if not in_active_window(now):
            # Sleep and check again later
            time.sleep(min(60, LOOP_EVERY_SEC))
            continue

        # Prevent overlap (shouldn’t happen, but belt & suspenders)
        if LOCK_FILE.exists():
            print("[INFO] Previous run still marked running; waiting 30s…")
            time.sleep(30)
            continue

        try:
            LOCK_FILE.touch(exist_ok=True)
            stamp = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{stamp}] Running pipeline…")

            # Ensure DRY_RUN default is respected from environment; do not force here
            env = os.environ.copy()
            # Run the pipeline as a subprocess
            proc = subprocess.Popen(
                [PY_EXE, str(RUN_SCRIPT)],
                cwd=str(PROJECT_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # Stream output with a timeout guard
            deadline = time.time() + RUN_TIMEOUT_MIN * 60
            lines = []
            while True:
                if proc.poll() is not None:
                    break
                line = proc.stdout.readline()
                if line:
                    print(line, end="")
                    lines.append(line)
                if time.time() > deadline:
                    proc.kill()
                    raise TimeoutError(f"run_loop.py exceeded {RUN_TIMEOUT_MIN} min timeout")
                time.sleep(0.05)

            # Capture remaining output
            tail = proc.stdout.read() or ""
            if tail:
                print(tail, end="")
                lines.append(tail)

            code = proc.returncode or 0
            if code == 0:
                send_tg("✅ <b>Pipeline OK</b> (daemon)")
            else:
                send_tg(f"❌ <b>Pipeline failed</b> (exit {code})")
        except Exception as e:
            send_tg(f"🔥 <b>Daemon error</b>: <code>{type(e).__name__}: {e}</code>")
        finally:
            try:
                if LOCK_FILE.exists(): LOCK_FILE.unlink()
            except: pass

        # Wait until next tick
        time.sleep(LOOP_EVERY_SEC)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        send_tg("⏹️ <b>Loop daemon interrupted</b> (KeyboardInterrupt).")
