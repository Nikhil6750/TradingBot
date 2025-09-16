from dotenv import load_dotenv; load_dotenv()
import time, subprocess, sys, os

PYTHON = sys.executable  # current venv's python
SCRIPT = os.path.join(os.path.dirname(__file__), "main.py")

while True:
    try:
        print("=== starting cycle ===")
        subprocess.run([PYTHON, SCRIPT], check=False)
    except Exception as e:
        print("runner error:", e)
    time.sleep(1 * 60)  
